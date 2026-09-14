from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.models import Dispatch, DispatchStatus, Schedule, ScheduleDependency
from whatsapp_scheduler.recurrence import utc_to_local
from whatsapp_scheduler.scheduler import dispatch_due, materialize_due
from whatsapp_scheduler.waha import WahaError

TZ = "America/Sao_Paulo"
FROZEN = datetime(2026, 6, 1, 12, 0, 0)


@pytest.fixture
def frozen_clock(monkeypatch):
    holder = {"now": FROZEN}
    monkeypatch.setattr("whatsapp_scheduler.clock.utcnow", lambda: holder["now"])
    return holder


def make_schedule(*, minutes_from_now: float, recurrence=None, max_attempts=3) -> str:
    first_run_local = utc_to_local(FROZEN + timedelta(minutes=minutes_from_now), TZ)
    with Session(get_engine()) as db:
        s = Schedule(
            session="default",
            recipient_input="+55 11 99999-8888",
            chat_id="5511999998888@c.us",
            text="olá",
            timezone=TZ,
            first_run_local=first_run_local,
            recurrence=recurrence,
            max_attempts=max_attempts,
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s.id


def dispatches_of(schedule_id: str) -> list[Dispatch]:
    with Session(get_engine()) as db:
        return list(
            db.exec(
                select(Dispatch)
                .where(Dispatch.schedule_id == schedule_id)
                .order_by(Dispatch.scheduled_at_utc)
            ).all()
        )


async def test_due_dispatch_is_sent(fake_waha, frozen_clock):
    sid = make_schedule(minutes_from_now=-1)
    materialize_due()
    sent = await dispatch_due(fake_waha)

    assert sent == 1
    assert fake_waha.sent == [{"session": "default", "chatId": "5511999998888@c.us", "text": "olá"}]
    (d,) = dispatches_of(sid)
    assert d.status == DispatchStatus.sent
    assert d.sent_at_utc == FROZEN
    assert d.waha_message_id


async def test_future_dispatch_not_sent(fake_waha, frozen_clock):
    sid = make_schedule(minutes_from_now=30)
    materialize_due()
    sent = await dispatch_due(fake_waha)

    assert sent == 0
    assert fake_waha.sent == []
    (d,) = dispatches_of(sid)
    assert d.status == DispatchStatus.pending


async def test_session_not_working_defers_without_consuming_attempt(fake_waha, frozen_clock):
    fake_waha.status = "SCAN_QR_CODE"
    sid = make_schedule(minutes_from_now=-1)
    materialize_due()
    sent = await dispatch_due(fake_waha)

    assert sent == 0
    (d,) = dispatches_of(sid)
    assert d.status == DispatchStatus.pending
    assert d.attempts == 0
    assert "não está pronta" in d.last_error
    assert d.scheduled_at_utc == FROZEN + timedelta(seconds=60)


async def test_send_error_retries_with_backoff(fake_waha, frozen_clock):
    fake_waha.send_error = WahaError("500 boom")
    sid = make_schedule(minutes_from_now=-1, max_attempts=3)
    materialize_due()
    await dispatch_due(fake_waha)

    (d,) = dispatches_of(sid)
    assert d.status == DispatchStatus.pending
    assert d.attempts == 1
    assert d.scheduled_at_utc == FROZEN + timedelta(seconds=60)
    assert "boom" in d.last_error


async def test_send_error_exhausts_to_failed(fake_waha, frozen_clock):
    fake_waha.send_error = WahaError("permanent")
    sid = make_schedule(minutes_from_now=-1, max_attempts=1)
    materialize_due()
    await dispatch_due(fake_waha)

    (d,) = dispatches_of(sid)
    assert d.status == DispatchStatus.failed
    assert d.attempts == 1


async def test_overdue_is_skipped(fake_waha, frozen_clock):
    sid = make_schedule(minutes_from_now=-180)  # 3h atrás, limite é 120min
    materialize_due()
    sent = await dispatch_due(fake_waha)

    assert sent == 0
    assert fake_waha.sent == []
    (d,) = dispatches_of(sid)
    assert d.status == DispatchStatus.skipped


async def test_recurring_materializes_next_after_send(fake_waha, frozen_clock):
    sid = make_schedule(minutes_from_now=-1, recurrence="*/5 * * * *")
    materialize_due()
    await dispatch_due(fake_waha)
    materialize_due()

    ds = dispatches_of(sid)
    assert [d.status for d in ds] == [DispatchStatus.sent, DispatchStatus.pending]
    assert ds[1].scheduled_at_utc == datetime(2026, 6, 1, 12, 5)


def test_recover_stuck_processing(frozen_clock):
    sid = make_schedule(minutes_from_now=-1)
    with Session(get_engine()) as db:
        db.add(
            Dispatch(
                schedule_id=sid,
                scheduled_at_utc=FROZEN - timedelta(minutes=1),
                status=DispatchStatus.processing,
                updated_at=FROZEN - timedelta(minutes=20),
            )
        )
        db.commit()

    materialize_due()

    (d,) = dispatches_of(sid)
    assert d.status == DispatchStatus.pending
    assert "presa" in d.last_error


# --------------------------------------------------------------------------- #
# Encadeamento de schedules (ScheduleDependency) — usado por automações de
# várias mensagens em sequência (calendar_service). Genérico: o scheduler não
# sabe o que é uma "automação", só que um schedule pode depender de outro.
# --------------------------------------------------------------------------- #
def link_dependency(schedule_id: str, depends_on: str) -> None:
    with Session(get_engine()) as db:
        db.add(ScheduleDependency(schedule_id=schedule_id, depends_on_schedule_id=depends_on))
        db.commit()


async def test_dependency_gate_holds_successor_until_predecessor_sent(fake_waha, frozen_clock):
    a_id = make_schedule(minutes_from_now=-5)
    b_id = make_schedule(minutes_from_now=-5)
    link_dependency(b_id, a_id)

    materialize_due()
    sent = await dispatch_due(fake_waha)
    assert sent == 1
    assert dispatches_of(b_id) == []  # ainda esperando a predecessora confirmar envio

    materialize_due()
    sent = await dispatch_due(fake_waha)
    assert sent == 1
    (b_dispatch,) = dispatches_of(b_id)
    assert b_dispatch.status == DispatchStatus.sent


async def test_dependency_gate_aborts_successor_when_predecessor_fails_permanently(fake_waha, frozen_clock):
    fake_waha.send_error = WahaError("permanent")
    a_id = make_schedule(minutes_from_now=-5, max_attempts=1)
    b_id = make_schedule(minutes_from_now=-5)
    link_dependency(b_id, a_id)

    materialize_due()
    await dispatch_due(fake_waha)  # A falha e esgota (max_attempts=1) -> failed
    (a_dispatch,) = dispatches_of(a_id)
    assert a_dispatch.status == DispatchStatus.failed

    # 2 ticks: 1 pra A se auto-desativar (disparo único já terminou), outro
    # pra B enxergar a predecessora desativada-sem-sucesso e abortar a
    # cadeia — determinístico independente da ordem de iteração da query.
    materialize_due()
    materialize_due()

    with Session(get_engine()) as db:
        a = db.get(Schedule, a_id)
        b = db.get(Schedule, b_id)
        assert a.enabled is False
        assert b.enabled is False
    assert dispatches_of(b_id) == []  # nunca chegou a ser despachada, fora de ordem


async def test_dependency_gate_cascade_aborts_two_levels_deep(fake_waha, frozen_clock):
    fake_waha.send_error = WahaError("permanent")
    a_id = make_schedule(minutes_from_now=-5, max_attempts=1)
    b_id = make_schedule(minutes_from_now=-5)
    c_id = make_schedule(minutes_from_now=-5)
    link_dependency(b_id, a_id)
    link_dependency(c_id, b_id)

    materialize_due()
    await dispatch_due(fake_waha)  # só A é despachada (B e C esperam)

    for _ in range(3):  # ticks suficientes pra cascata resolver A -> B -> C
        materialize_due()

    with Session(get_engine()) as db:
        assert db.get(Schedule, a_id).enabled is False
        assert db.get(Schedule, b_id).enabled is False
        assert db.get(Schedule, c_id).enabled is False
    assert dispatches_of(b_id) == []
    assert dispatches_of(c_id) == []
