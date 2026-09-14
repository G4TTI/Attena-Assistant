from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, col, select

from whatsapp_scheduler import app_settings as app_settings_module
from whatsapp_scheduler import calendar_service
from whatsapp_scheduler.calendar_providers.base import CalendarProviderError
from whatsapp_scheduler.config import settings as app_settings
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.models import (
    Automation,
    AutomationMessage,
    AutomationSchedule,
    Calendar,
    CalendarConnection,
    CalendarConnectionStatus,
    Dispatch,
    DispatchStatus,
    Event,
    EventAutomation,
    EventSource,
    EventSyncStatus,
    OffsetDirection,
    OffsetUnit,
    Schedule,
)
from whatsapp_scheduler.service import ValidationError, create_schedule

FROZEN = datetime(2026, 6, 1, 12, 0, 0)


@pytest.fixture
def frozen_clock(monkeypatch):
    holder = {"now": FROZEN}
    monkeypatch.setattr("whatsapp_scheduler.clock.utcnow", lambda: holder["now"])
    return holder


def make_internal_event(*, start=None) -> Event:
    with Session(get_engine()) as db:
        event = Event(
            source=EventSource.internal,
            title="Consulta com Leonardo",
            description="",
            start_utc=start or (FROZEN + timedelta(hours=2)),
            end_utc=(start or (FROZEN + timedelta(hours=2))) + timedelta(hours=1),
            timezone="America/Sao_Paulo",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event


def schedules_of_automation(automation_id: str) -> list[Schedule]:
    """Schedules de uma automação, ordenados pela `position` da mensagem."""
    with Session(get_engine()) as db:
        links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation_id)
        ).all()
        rows = []
        for link in links:
            message = db.get(AutomationMessage, link.message_id)
            schedule = db.get(Schedule, link.schedule_id)
            rows.append((message.position, schedule))
        rows.sort(key=lambda t: t[0])
        return [s for _, s in rows]


def dispatches_of_schedule(schedule_id: str) -> list[Dispatch]:
    with Session(get_engine()) as db:
        return list(
            db.exec(
                select(Dispatch)
                .where(col(Dispatch.schedule_id) == schedule_id)
                .order_by(col(Dispatch.scheduled_at_utc))
            ).all()
        )


def make_google_calendar(db: Session) -> tuple[CalendarConnection, Calendar]:
    from whatsapp_scheduler import crypto

    conn = CalendarConnection(
        provider="google",
        account_identifier="user@example.com",
        access_token_enc=crypto.encrypt("access"),
        refresh_token_enc=crypto.encrypt("refresh"),
        token_expires_at=FROZEN + timedelta(hours=1),
        status=CalendarConnectionStatus.active,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    cal = Calendar(connection_id=conn.id, external_id="primary", name="Trabalho", enabled=True)
    db.add(cal)
    db.commit()
    db.refresh(cal)
    return conn, cal


def test_missing_config_lists_exact_env_vars_when_unconfigured(monkeypatch):
    monkeypatch.setattr(app_settings, "google_client_id", "")
    monkeypatch.setattr(app_settings, "google_client_secret", "")
    monkeypatch.setattr(app_settings, "token_encryption_key", "")

    missing = calendar_service.missing_config()
    assert set(missing) == {"TOKEN_ENCRYPTION_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"}

    with pytest.raises(calendar_service.NotConfiguredError) as exc_info:
        calendar_service.start_connect()
    for name in missing:
        assert name in str(exc_info.value)


def test_start_connect_works_when_configured():
    url, state = calendar_service.start_connect()
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert state and len(state) > 10


# --------------------------------------------------------------------------- #
# Criar automação (multi-mensagem, multi-destinatário)
# --------------------------------------------------------------------------- #
def test_create_event_automation_creates_one_message_one_schedule_and_link():
    event = make_internal_event()
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db,
            event_id=event.id,
            recipients=["+55 11 99999-8888"],
            messages=["Olá Leonardo, passando para lembrar da nossa consulta."],
            offset_amount=2,
            offset_unit="hours",
            offset_direction="before",
        )
        automation_id = automation.id

    schedules = schedules_of_automation(automation_id)
    assert len(schedules) == 1
    schedule = schedules[0]
    assert schedule.first_run_local is not None

    with Session(get_engine()) as db:
        automations = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
        dispatches = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule.id)).all()
    assert len(automations) == 1
    assert len(dispatches) == 1
    assert dispatches[0].scheduled_at_utc == event.start_utc - timedelta(hours=2)


def test_create_event_automation_multiple_recipients_creates_one_schedule_each():
    event = make_internal_event()
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db,
            event_id=event.id,
            recipients=["+55 11 99999-8888", "+55 11 98888-7777"],
            messages=["Lembrete"],
            offset_amount=30,
            offset_unit="minutes",
            offset_direction="before",
        )
        automation_id = automation.id
    schedules = schedules_of_automation(automation_id)
    assert len(schedules) == 2
    assert {s.chat_id for s in schedules} == {"5511999998888@c.us", "5511988887777@c.us"}


def test_create_event_automation_rejects_unknown_event():
    with Session(get_engine()) as db:
        with pytest.raises(ValidationError):
            calendar_service.create_event_automation(
                db,
                event_id="does-not-exist",
                recipients=["+55 11 99999-8888"],
                messages=["x"],
                offset_amount=1,
                offset_unit="hours",
                offset_direction="before",
            )


def test_create_event_automation_rejects_empty_messages():
    event = make_internal_event()
    with Session(get_engine()) as db:
        with pytest.raises(ValidationError):
            calendar_service.create_event_automation(
                db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["   ", ""],
                offset_amount=1, offset_unit="hours", offset_direction="before",
            )


# --------------------------------------------------------------------------- #
# Várias mensagens: ordem, encadeamento (depends_on_schedule_id) e recálculo
# --------------------------------------------------------------------------- #
def test_multi_message_automation_chains_schedules_by_recipient_with_dependency():
    from whatsapp_scheduler.models import ScheduleDependency

    event = make_internal_event()
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888", "+55 11 98888-7777"],
            messages=["um", "dois", "três"], offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id

    with Session(get_engine()) as db:
        links = db.exec(select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation_id)).all()
        assert len(links) == 6  # 2 destinatários x 3 mensagens

        by_recipient: dict[str, list[tuple[int, str]]] = {}
        for link in links:
            message = db.get(AutomationMessage, link.message_id)
            by_recipient.setdefault(link.recipient_chat_id, []).append((message.position, link.schedule_id))

        for chat_id, entries in by_recipient.items():
            entries.sort(key=lambda t: t[0])
            schedule_ids_in_order = [sid for _, sid in entries]
            # mensagem 0 não depende de nada
            dep0 = db.exec(
                select(ScheduleDependency).where(col(ScheduleDependency.schedule_id) == schedule_ids_in_order[0])
            ).first()
            assert dep0 is None
            # mensagem 1 depende da mensagem 0 DO MESMO destinatário, mensagem 2 da 1
            for i in range(1, len(schedule_ids_in_order)):
                dep = db.exec(
                    select(ScheduleDependency).where(col(ScheduleDependency.schedule_id) == schedule_ids_in_order[i])
                ).first()
                assert dep is not None
                assert dep.depends_on_schedule_id == schedule_ids_in_order[i - 1]


async def test_reschedule_preserves_per_message_gap(frozen_clock):
    # timezone_name="UTC" força o schedule a usar UTC como sua própria
    # timezone — assim Schedule.first_run_local (hora LOCAL na timezone do
    # schedule) pode ser comparado direto com valores UTC sem ambiguidade.
    event = make_internal_event(start=FROZEN + timedelta(hours=2))
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["um", "dois"],
            offset_amount=1, offset_unit="hours", offset_direction="before", timezone_name="UTC",
        )
        automation_id = automation.id
    schedules = schedules_of_automation(automation_id)
    assert schedules[1].first_run_local - schedules[0].first_run_local == timedelta(seconds=3)
    # a segunda mensagem ainda não foi despachada — só materializa depois que
    # a primeira for confirmada como enviada (ver scheduler._dependency_gate)
    assert dispatches_of_schedule(schedules[1].id) == []

    new_start = FROZEN + timedelta(hours=6)
    with Session(get_engine()) as db:
        await calendar_service.update_internal_event(
            db, event.id, title="Consulta com Leonardo", start_local=new_start,
            end_local=new_start + timedelta(hours=1), timezone_name="UTC",
        )

    schedules_after = schedules_of_automation(automation_id)
    assert schedules_after[1].first_run_local - schedules_after[0].first_run_local == timedelta(seconds=3)
    assert schedules_after[0].first_run_local == new_start - timedelta(hours=1)


def test_remove_event_automation_cancels_schedules_but_keeps_event():
    event = make_internal_event()
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id
    schedule_id = schedules_of_automation(automation_id)[0].id

    with Session(get_engine()) as db:
        assert calendar_service.remove_event_automation(db, automation_id) is True

    with Session(get_engine()) as db:
        sched = db.get(Schedule, schedule_id)
        assert sched.enabled is False
        ev = db.get(Event, event.id)
        assert ev is not None  # evento preservado


def test_disconnect_cancels_pending_but_preserves_sent_history():
    with Session(get_engine()) as db:
        conn, cal = make_google_calendar(db)
        connection_id = conn.id
        event = Event(
            source=EventSource.google,
            calendar_id=cal.id,
            external_id="ext-1",
            title="Consulta",
            start_utc=FROZEN + timedelta(hours=2),
            end_utc=FROZEN + timedelta(hours=3),
            timezone="America/Sao_Paulo",
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        pending_automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["a"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        sent_automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 98888-7777"], messages=["b"],
            offset_amount=2, offset_unit="hours", offset_direction="before",
        )
        pending_automation_id = pending_automation.id
        sent_automation_id = sent_automation.id

    pending_id = schedules_of_automation(pending_automation_id)[0].id
    sent_id = schedules_of_automation(sent_automation_id)[0].id

    with Session(get_engine()) as db:
        (sent_dispatch,) = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == sent_id)).all()
        sent_dispatch.status = DispatchStatus.sent
        db.add(sent_dispatch)
        db.commit()

    with Session(get_engine()) as db:
        assert calendar_service.disconnect(db, connection_id) is True

    with Session(get_engine()) as db:
        (pending_dispatch,) = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == pending_id)).all()
        assert pending_dispatch.status == DispatchStatus.canceled

        (sent_dispatch_after,) = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == sent_id)).all()
        assert sent_dispatch_after.status == DispatchStatus.sent  # histórico intocado

        conn_after = db.get(CalendarConnection, connection_id)
        assert str(conn_after.status) == "disconnected"


# --------------------------------------------------------------------------- #
# month_grid
# --------------------------------------------------------------------------- #
def test_month_grid_always_has_42_cells(frozen_clock):
    with Session(get_engine()) as db:
        weeks = calendar_service.month_grid(db, 2026, 9)
    assert len(weeks) == 6
    for week in weeks:
        assert len(week) == 7
    all_dates = [day["date"] for week in weeks for day in week]
    assert len(all_dates) == 42
    assert all_dates == sorted(all_dates)
    assert any(day["in_month"] for week in weeks for day in week)


def test_month_grid_places_event_on_correct_local_day(frozen_clock):
    # 2026-09-15 14:00 America/Sao_Paulo (UTC-3) = 2026-09-15 17:00 UTC
    with Session(get_engine()) as db:
        event = Event(
            source=EventSource.internal,
            title="Consulta",
            start_utc=datetime(2026, 9, 15, 17, 0),
            end_utc=datetime(2026, 9, 15, 18, 0),
            timezone="America/Sao_Paulo",
        )
        db.add(event)
        db.commit()

        weeks = calendar_service.month_grid(db, 2026, 9)

    day15 = next(day for week in weeks for day in week if day["date"].isoformat() == "2026-09-15")
    assert [e.title for e in day15["events"]] == ["Consulta"]
    other_days = [day for week in weeks for day in week if day["date"].isoformat() != "2026-09-15"]
    assert all(e.title != "Consulta" for day in other_days for e in day["events"])


def test_month_grid_buckets_by_event_own_timezone_not_default(frozen_clock):
    # 2026-08-31 15:30 UTC = 2026-09-01 00:30 in Asia/Tokyo (UTC+9), but only
    # 2026-08-31 12:30 in America/Sao_Paulo (default_timezone, UTC-3). If the
    # grid bucketed by default_timezone instead of the event's own timezone,
    # this would land on Aug 31 instead of Sep 1.
    with Session(get_engine()) as db:
        event = Event(
            source=EventSource.google,
            title="Tokyo meeting",
            start_utc=datetime(2026, 8, 31, 15, 30),
            end_utc=datetime(2026, 8, 31, 16, 30),
            timezone="Asia/Tokyo",
        )
        db.add(event)
        db.commit()

        weeks = calendar_service.month_grid(db, 2026, 9)

    day1 = next(day for week in weeks for day in week if day["date"].isoformat() == "2026-09-01")
    assert [e.title for e in day1["events"]] == ["Tokyo meeting"]
    aug31 = next(day for week in weeks for day in week if day["date"].isoformat() == "2026-08-31")
    assert aug31["events"] == []


# --------------------------------------------------------------------------- #
# CRUD de evento interno
# --------------------------------------------------------------------------- #
async def test_create_internal_event_validates_fields():
    with Session(get_engine()) as db:
        with pytest.raises(ValidationError):
            await calendar_service.create_internal_event(
                db, title="", start_local=FROZEN, end_local=FROZEN + timedelta(hours=1),
                timezone_name="America/Sao_Paulo",
            )
        with pytest.raises(ValidationError):
            await calendar_service.create_internal_event(
                db, title="x", start_local=FROZEN, end_local=FROZEN,  # fim não é depois do início
                timezone_name="America/Sao_Paulo",
            )


async def test_update_internal_event_reschedules_pending_dispatch_in_place(frozen_clock):
    event = make_internal_event(start=FROZEN + timedelta(hours=2))
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id
    schedule_id = schedules_of_automation(automation_id)[0].id

    with Session(get_engine()) as db:
        (dispatch,) = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule_id)).all()
        original_dispatch_id = dispatch.id
        assert dispatch.scheduled_at_utc == FROZEN + timedelta(hours=1)  # 2h - 1h antes

    new_start = FROZEN + timedelta(hours=5)
    with Session(get_engine()) as db:
        # timezone_name="UTC" aqui só pra manter a aritmética do teste em UTC
        # puro — update_internal_event recebe hora LOCAL (naive) e converte
        # via local_to_utc, igual create_internal_event.
        await calendar_service.update_internal_event(
            db, event.id, title="Consulta com Leonardo", start_local=new_start,
            end_local=new_start + timedelta(hours=1), timezone_name="UTC",
        )

    with Session(get_engine()) as db:
        dispatches = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule_id)).all()
    assert len(dispatches) == 1  # sem duplicar
    assert dispatches[0].id == original_dispatch_id
    assert dispatches[0].scheduled_at_utc == new_start - timedelta(hours=1)


async def test_update_internal_event_does_not_touch_already_sent_dispatch(frozen_clock):
    event = make_internal_event(start=FROZEN + timedelta(hours=2))
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id
    schedule_id = schedules_of_automation(automation_id)[0].id
    with Session(get_engine()) as db:
        (dispatch,) = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule_id)).all()
        dispatch.status = DispatchStatus.sent
        db.add(dispatch)
        db.commit()
        original_scheduled_at = dispatch.scheduled_at_utc

    with Session(get_engine()) as db:
        await calendar_service.update_internal_event(
            db, event.id, title="Consulta com Leonardo", start_local=FROZEN + timedelta(hours=9),
            end_local=FROZEN + timedelta(hours=10), timezone_name="America/Sao_Paulo",
        )

    with Session(get_engine()) as db:
        (dispatch,) = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule_id)).all()
        assert dispatch.status == DispatchStatus.sent
        assert dispatch.scheduled_at_utc == original_scheduled_at  # histórico intocado


async def test_update_internal_event_rejects_google_sourced_event():
    with Session(get_engine()) as db:
        event = Event(
            source=EventSource.google, calendar_id=None, title="x",
            start_utc=FROZEN, end_utc=FROZEN + timedelta(hours=1), timezone="America/Sao_Paulo",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        with pytest.raises(ValidationError):
            await calendar_service.update_internal_event(
                db, event.id, title="y", start_local=FROZEN, end_local=FROZEN + timedelta(hours=1),
                timezone_name="America/Sao_Paulo",
            )


async def test_delete_internal_event_cancels_automations_and_preserves_schedule_history():
    event = make_internal_event()
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id
    schedule_id = schedules_of_automation(automation_id)[0].id

    with Session(get_engine()) as db:
        assert await calendar_service.delete_internal_event(db, event.id) is True

    with Session(get_engine()) as db:
        assert db.get(Event, event.id) is None
        assert db.get(Automation, automation_id) is None
        remaining_links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation_id)
        ).all()
        assert remaining_links == []
        sched = db.get(Schedule, schedule_id)
        assert sched is not None and sched.enabled is False  # histórico preservado, não apagado
        (dispatch,) = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule_id)).all()
        assert dispatch.status == DispatchStatus.canceled


async def test_delete_internal_event_rejects_google_sourced_event():
    with Session(get_engine()) as db:
        event = Event(
            source=EventSource.google, title="x",
            start_utc=FROZEN, end_utc=FROZEN + timedelta(hours=1), timezone="America/Sao_Paulo",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        with pytest.raises(ValidationError):
            await calendar_service.delete_internal_event(db, event.id)


# --------------------------------------------------------------------------- #
# Editar automação (remover + recriar, sem deixar linha fantasma)
# --------------------------------------------------------------------------- #
def test_update_event_automation_does_not_leave_ghost_row_and_keeps_old_schedule_untouched():
    event = make_internal_event()
    with Session(get_engine()) as db:
        old_automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["mensagem antiga"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        automation_id = old_automation.id
    old_schedule_id = schedules_of_automation(automation_id)[0].id

    with Session(get_engine()) as db:
        new_automation = calendar_service.update_event_automation(
            db, automation_id, recipients=["+55 11 99999-8888"], messages=["mensagem nova"],
            offset_amount=2, offset_unit="hours", offset_direction="before",
        )
        new_automation_id = new_automation.id

    assert new_automation_id != automation_id
    new_schedule_id = schedules_of_automation(new_automation_id)[0].id
    assert new_schedule_id != old_schedule_id

    with Session(get_engine()) as db:
        assert db.get(Automation, automation_id) is None  # apagada, não deixada como "fantasma"
        remaining = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
        assert len(remaining) == 1
        assert remaining[0].id == new_automation_id

        old_sched = db.get(Schedule, old_schedule_id)
        assert old_sched.enabled is False
        assert old_sched.text == "mensagem antiga"  # nunca mutado

        new_sched = db.get(Schedule, new_schedule_id)
        assert new_sched.enabled is True
        assert new_sched.text == "mensagem nova"


# --------------------------------------------------------------------------- #
# Prevenção de duplicidade
# --------------------------------------------------------------------------- #
def test_create_event_automation_is_idempotent_for_identical_immediate_resubmit(frozen_clock):
    event = make_internal_event()
    with Session(get_engine()) as db:
        first = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["oi"],
            offset_amount=2, offset_unit="hours", offset_direction="before",
        )
        second = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["oi"],
            offset_amount=2, offset_unit="hours", offset_direction="before",
        )
        assert first.id == second.id  # devolveu a mesma Automation, não criou outra

    with Session(get_engine()) as db:
        automations = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
        assert len(automations) == 1
        schedules = db.exec(select(Schedule).where(col(Schedule.chat_id) == "5511999998888@c.us")).all()
        assert len(schedules) == 1


def test_duplicate_guard_multi_message_resubmit_does_not_violate_unique_constraint(frozen_clock):
    """Duplo-submit de uma automação com várias mensagens/destinatários não
    pode tentar religar um `Schedule` já usado a uma nova `AutomationSchedule`
    (isso violaria o UNIQUE de `schedule_id`) — a trava precisa agir no nível
    da `Automation` inteira, não por mensagem individual."""
    event = make_internal_event()
    with Session(get_engine()) as db:
        first = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888", "+55 11 98888-7777"],
            messages=["um", "dois", "três"], offset_amount=2, offset_unit="hours", offset_direction="before",
        )
        second = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888", "+55 11 98888-7777"],
            messages=["um", "dois", "três"], offset_amount=2, offset_unit="hours", offset_direction="before",
        )
        assert first.id == second.id

    with Session(get_engine()) as db:
        automations = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
        assert len(automations) == 1
        links = db.exec(select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == first.id)).all()
        assert len(links) == 6  # 2 destinatários x 3 mensagens, sem duplicar


def test_edit_flow_not_blocked_by_duplicate_guard_even_with_near_identical_values(frozen_clock):
    """Editar cancela a antiga e cria uma quase idêntica logo em seguida — a
    trava de duplicidade não pode bloquear esse fluxo (ela é escopada em
    enabled=True, e a automação antiga já foi desativada nesse ponto)."""
    event = make_internal_event()
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["oi"],
            offset_amount=2, offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id

    with Session(get_engine()) as db:
        # "edita" mas mantém os mesmos valores — deve criar uma automação nova mesmo assim
        new_automation = calendar_service.update_event_automation(
            db, automation_id, recipients=["+55 11 99999-8888"], messages=["oi"],
            offset_amount=2, offset_unit="hours", offset_direction="before",
        )
        new_automation_id = new_automation.id

    assert new_automation_id != automation_id
    new_schedule = schedules_of_automation(new_automation_id)[0]
    assert new_schedule.enabled is True


# --------------------------------------------------------------------------- #
# Migração do formato legado (EventAutomation -> Automation/.../.../)
# --------------------------------------------------------------------------- #
def test_migrate_legacy_automations_is_idempotent_and_preserves_schedule():
    event = make_internal_event()
    with Session(get_engine()) as db:
        schedule = create_schedule(
            db, recipient="+55 11 99999-8888", text="legado",
            send_at=event.start_utc - timedelta(hours=1), timezone="America/Sao_Paulo",
        )
        db.add(
            EventAutomation(
                event_id=event.id, schedule_id=schedule.id,
                offset_amount=1, offset_unit=OffsetUnit.hours, offset_direction=OffsetDirection.before,
            )
        )
        db.commit()
        schedule_id = schedule.id

    with Session(get_engine()) as db:
        calendar_service.migrate_legacy_automations(db)
    with Session(get_engine()) as db:
        calendar_service.migrate_legacy_automations(db)  # idempotente — não duplica

    with Session(get_engine()) as db:
        links = db.exec(select(AutomationSchedule).where(col(AutomationSchedule.schedule_id) == schedule_id)).all()
        assert len(links) == 1
        automations = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
        assert len(automations) == 1
        messages = db.exec(
            select(AutomationMessage).where(col(AutomationMessage.automation_id) == automations[0].id)
        ).all()
        assert [m.text for m in messages] == ["legado"]

        # o Schedule original nunca é tocado pela migração
        original_schedule = db.get(Schedule, schedule_id)
        assert original_schedule.text == "legado"


# --------------------------------------------------------------------------- #
# Push pro Google Agenda (criar/editar/excluir vinculado)
# --------------------------------------------------------------------------- #
async def test_create_internal_event_pushes_to_google_and_links(monkeypatch, fake_google, frozen_clock):
    monkeypatch.setattr(calendar_service, "get_provider", lambda key: fake_google)
    with Session(get_engine()) as db:
        _, cal = make_google_calendar(db)
        event = await calendar_service.create_internal_event(
            db, title="Consulta", start_local=FROZEN + timedelta(hours=2),
            end_local=FROZEN + timedelta(hours=3), timezone_name="America/Sao_Paulo",
            target_calendar_id=cal.id,
        )
        assert event.calendar_id == cal.id
        assert event.external_id is not None
        event_id = event.id

    assert len(fake_google.created_events) == 1
    with Session(get_engine()) as db:
        status = db.get(EventSyncStatus, event_id)
        assert status.status == "synced"


async def test_create_internal_event_survives_google_push_failure(monkeypatch, fake_google, frozen_clock):
    monkeypatch.setattr(calendar_service, "get_provider", lambda key: fake_google)
    fake_google.create_event_error = CalendarProviderError("403 forbidden — escopo insuficiente")
    with Session(get_engine()) as db:
        _, cal = make_google_calendar(db)
        event = await calendar_service.create_internal_event(
            db, title="Consulta", start_local=FROZEN + timedelta(hours=2),
            end_local=FROZEN + timedelta(hours=3), timezone_name="America/Sao_Paulo",
            target_calendar_id=cal.id,
        )
        event_id = event.id
        assert event.external_id is None  # não vinculado — mas o evento local existe mesmo assim

    with Session(get_engine()) as db:
        assert db.get(Event, event_id) is not None
        status = db.get(EventSyncStatus, event_id)
        assert status.status == "error"


async def test_update_internal_event_rejects_local_change_when_google_push_fails(monkeypatch, fake_google, frozen_clock):
    """Bug crítico encontrado na revisão de arquitetura: se o push falhasse
    DEPOIS de já ter gravado a mudança localmente, o próximo pull-sync
    reverteria o horário local sozinho (silenciosamente) e reagendaria a
    automação de volta pro horário errado. A correção é nunca commitar a
    mudança local se o push falhar."""
    monkeypatch.setattr(calendar_service, "get_provider", lambda key: fake_google)
    with Session(get_engine()) as db:
        _, cal = make_google_calendar(db)
        event = await calendar_service.create_internal_event(
            db, title="Consulta", start_local=FROZEN + timedelta(hours=2),
            end_local=FROZEN + timedelta(hours=3), timezone_name="America/Sao_Paulo",
            target_calendar_id=cal.id,
        )
        event_id = event.id
        original_start = event.start_utc

    fake_google.update_event_error = CalendarProviderError("403 forbidden")
    with Session(get_engine()) as db:
        with pytest.raises(ValidationError):
            await calendar_service.update_internal_event(
                db, event_id, title="Consulta", start_local=FROZEN + timedelta(hours=9),
                end_local=FROZEN + timedelta(hours=10), timezone_name="America/Sao_Paulo",
            )

    with Session(get_engine()) as db:
        ev = db.get(Event, event_id)
        assert ev.start_utc == original_start  # nada mudou localmente


async def test_delete_internal_event_keeps_local_row_when_google_delete_fails(monkeypatch, fake_google, frozen_clock):
    monkeypatch.setattr(calendar_service, "get_provider", lambda key: fake_google)
    with Session(get_engine()) as db:
        _, cal = make_google_calendar(db)
        event = await calendar_service.create_internal_event(
            db, title="Consulta", start_local=FROZEN + timedelta(hours=2),
            end_local=FROZEN + timedelta(hours=3), timezone_name="America/Sao_Paulo",
            target_calendar_id=cal.id,
        )
        event_id = event.id

    fake_google.delete_event_error = CalendarProviderError("500 boom")
    with Session(get_engine()) as db:
        with pytest.raises(ValidationError):
            await calendar_service.delete_internal_event(db, event_id, also_delete_google=True)

    with Session(get_engine()) as db:
        assert db.get(Event, event_id) is not None  # não excluído localmente


async def test_delete_internal_event_app_only_leaves_google_event_alone(monkeypatch, fake_google, frozen_clock):
    monkeypatch.setattr(calendar_service, "get_provider", lambda key: fake_google)
    with Session(get_engine()) as db:
        _, cal = make_google_calendar(db)
        event = await calendar_service.create_internal_event(
            db, title="Consulta", start_local=FROZEN + timedelta(hours=2),
            end_local=FROZEN + timedelta(hours=3), timezone_name="America/Sao_Paulo",
            target_calendar_id=cal.id,
        )
        event_id = event.id

    with Session(get_engine()) as db:
        assert await calendar_service.delete_internal_event(db, event_id, also_delete_google=False) is True

    assert fake_google.deleted_events == []  # não chamou o Google
    with Session(get_engine()) as db:
        assert db.get(Event, event_id) is None


# --------------------------------------------------------------------------- #
# Fuso horário global (app_settings)
# --------------------------------------------------------------------------- #
def test_set_timezone_updates_settings_and_persists_across_reload():
    original = app_settings.default_timezone
    try:
        with Session(get_engine()) as db:
            app_settings_module.set_timezone(db, "Europe/Lisbon")
        assert app_settings.default_timezone == "Europe/Lisbon"

        # simula reinício do processo: recarrega a partir do banco
        app_settings.default_timezone = "America/Sao_Paulo"
        with Session(get_engine()) as db:
            app_settings_module.load_from_db(db)
        assert app_settings.default_timezone == "Europe/Lisbon"
    finally:
        app_settings.default_timezone = original


def test_set_timezone_rejects_invalid_and_leaves_setting_untouched():
    original = app_settings.default_timezone
    try:
        with Session(get_engine()) as db:
            with pytest.raises(ValidationError):
                app_settings_module.set_timezone(db, "Not/ARealZone")
        assert app_settings.default_timezone == original
    finally:
        app_settings.default_timezone = original


def test_set_timezone_does_not_touch_already_created_schedule_timezone(frozen_clock):
    """Mudar o fuso padrão global nunca reescreve retroativamente o fuso já
    gravado em Schedule/Event existentes — só afeta o default de coisas
    criadas DEPOIS da mudança."""
    event = make_internal_event()
    with Session(get_engine()) as db:
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id
    schedule_id = schedules_of_automation(automation_id)[0].id

    original = app_settings.default_timezone
    try:
        with Session(get_engine()) as db:
            app_settings_module.set_timezone(db, "Europe/Lisbon")

        with Session(get_engine()) as db:
            sched = db.get(Schedule, schedule_id)
            assert sched.timezone == "America/Sao_Paulo"  # continua o fuso do evento, não o novo default
    finally:
        app_settings.default_timezone = original
