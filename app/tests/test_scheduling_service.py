"""Modelo único de agendamento (`ScheduleGroup` + sequência de mensagens): criação, horário
preservado, edição, cancelamento, isolamento entre usuários e envio pela sessão certa."""

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, col, select

from whatsapp_scheduler import schedule_views, timing
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.errors import ValidationError
from whatsapp_scheduler.models import (
    Automation,
    AutomationMessage,
    AutomationSchedule,
    CachedMessage,
    Dispatch,
    DispatchStatus,
    Schedule,
    ScheduleDependency,
    ScheduleGroup,
    ScheduleSource,
    User,
    WhatsAppSession,
)
from whatsapp_scheduler.scheduler import SchedulerService, dispatch_due, materialize_due
from whatsapp_scheduler.service import (
    backfill_groups,
    cancel_group,
    cancel_schedule,
    create_schedule,
    create_sequence,
    get_group,
    group_schedules,
    reschedule_group,
    update_sequence,
)
from whatsapp_scheduler.waha import WahaError

TZ = "America/Sao_Paulo"
CHAT = "5514991110001@c.us"
FROZEN = datetime(2026, 9, 1, 12, 0, 0)  # UTC


@pytest.fixture
def frozen_clock(monkeypatch):
    holder = {"now": FROZEN}
    monkeypatch.setattr("whatsapp_scheduler.clock.utcnow", lambda: holder["now"])
    return holder


def _dispatches(db, schedule_id):
    return list(db.exec(select(Dispatch).where(Dispatch.schedule_id == schedule_id)).all())


def _sequence(db, user, *, messages=("Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."),
              start=datetime(2026, 9, 20, 18, 0), session=None, **kwargs):
    return create_sequence(
        db, user_id=user.id, session=session or user.waha_session, recipient=CHAT, messages=list(messages),
        start=start, timezone=TZ, source=kwargs.pop("source", ScheduleSource.manual), **kwargs,
    )


# --------------------------------------------------------------------------- #
# Testes 1-3: horário preservado, mensagens individuais
# --------------------------------------------------------------------------- #
def test_one_recipient_one_message_keeps_18h(db, test_user):
    """Teste 1."""
    group, (schedule,) = _sequence(db, test_user, messages=["Olá Leonardo!"])
    assert group.start_local == datetime(2026, 9, 20, 18, 0)
    assert group.timezone == TZ
    assert schedule.first_run_local == datetime(2026, 9, 20, 18, 0)
    (dispatch,) = _dispatches(db, schedule.id)
    # 18:00 em São Paulo = 21:00 UTC (a conversão é do ZoneInfo, sem "+3h" na mão)
    assert dispatch.scheduled_at_utc == datetime(2026, 9, 20, 21, 0)
    assert timing.to_local(dispatch.scheduled_at_utc, TZ) == datetime(2026, 9, 20, 18, 0)


def test_three_messages_are_three_individual_schedules_of_one_group(db, test_user):
    """Teste 2 + Parte 1.3: recipient, sessão, horário, fuso, ordem e conteúdo ficam explícitos."""
    group, schedules = _sequence(db, test_user)
    assert len(schedules) == 3
    assert {s.group_id for s in schedules} == {group.id}
    assert [s.position for s in schedules] == [0, 1, 2]
    assert [s.text for s in schedules] == ["Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."]
    assert (group.chat_id, group.session, group.timezone, group.source) == (CHAT, test_user.waha_session, TZ, ScheduleSource.manual)
    assert {s.chat_id for s in schedules} == {CHAT} and {s.session for s in schedules} == {test_user.waha_session}
    # O início é EXATAMENTE o digitado; as seguintes só somam o intervalo (3 s) que já existia nas automações.
    assert [s.first_run_local for s in schedules] == [
        datetime(2026, 9, 20, 18, 0, 0), datetime(2026, 9, 20, 18, 0, 3), datetime(2026, 9, 20, 18, 0, 6),
    ]
    assert group.message_gap_seconds == 3


def test_sequence_is_chained_so_order_survives_failures(db, test_user):
    _, schedules = _sequence(db, test_user)
    deps = {d.schedule_id: d.depends_on_schedule_id for d in db.exec(select(ScheduleDependency)).all()}
    assert schedules[0].id not in deps
    assert deps[schedules[1].id] == schedules[0].id and deps[schedules[2].id] == schedules[1].id
    # Só a 1ª tem dispatch agora; as outras materializam depois que a anterior for confirmada.
    assert len(_dispatches(db, schedules[0].id)) == 1
    assert _dispatches(db, schedules[1].id) == [] and _dispatches(db, schedules[2].id) == []


def test_adding_messages_later_never_changes_the_start(db, test_user):
    """Teste 3: a hora informada continua 18:00 depois de adicionar mensagens."""
    group, _ = _sequence(db, test_user, messages=["Mensagem 1"])
    for count in (2, 3):
        texts = [f"Mensagem {i + 1}" for i in range(count)]
        update_sequence(db, group.id, user_id=test_user.id, session=test_user.waha_session, messages=texts,
                        start=datetime(2026, 9, 20, 18, 0), allow_past=True)
        db.refresh(group)
        schedules = group_schedules(db, group.id)
        assert group.start_local == datetime(2026, 9, 20, 18, 0)
        assert schedules[0].first_run_local == datetime(2026, 9, 20, 18, 0)
        assert [s.position for s in schedules] == list(range(count))
    assert len(group_schedules(db, group.id)) == 3


def test_editing_the_start_moves_every_message(db, test_user):
    """Teste 4: 18:00 -> 19:00, todas acompanham (e a dispatch pendente também)."""
    group, schedules = _sequence(db, test_user)
    update_sequence(db, group.id, user_id=test_user.id, session=test_user.waha_session,
                    messages=[s.text for s in schedules], start=datetime(2026, 9, 20, 19, 0), allow_past=True)
    db.refresh(group)
    rows = group_schedules(db, group.id)
    assert [s.first_run_local for s in rows] == [
        datetime(2026, 9, 20, 19, 0, 0), datetime(2026, 9, 20, 19, 0, 3), datetime(2026, 9, 20, 19, 0, 6),
    ]
    (dispatch,) = _dispatches(db, rows[0].id)
    assert dispatch.scheduled_at_utc == datetime(2026, 9, 20, 22, 0) and dispatch.status == DispatchStatus.pending
    assert [s.id for s in rows][:3] == [s.id for s in schedules]  # editou no lugar, sem trocar as linhas


def test_edit_can_reorder_and_remove_messages(db, test_user):
    group, _ = _sequence(db, test_user)
    update_sequence(db, group.id, user_id=test_user.id, session=test_user.waha_session,
                    messages=["Nos vemos às 20h.", "Olá Leonardo!"], start=datetime(2026, 9, 20, 18, 0), allow_past=True)
    rows = group_schedules(db, group.id)
    assert [(s.position, s.text) for s in rows] == [(0, "Nos vemos às 20h."), (1, "Olá Leonardo!")]
    assert len(db.exec(select(ScheduleDependency)).all()) == 1


def test_edit_is_refused_once_sending_started(db, test_user, frozen_clock):
    group, schedules = _sequence(db, test_user, messages=["a", "b"], start=datetime(2026, 9, 1, 8, 59))
    with Session(get_engine()) as other:
        d = other.exec(select(Dispatch).where(Dispatch.schedule_id == schedules[0].id)).one()
        d.status = DispatchStatus.processing
        other.add(d)
        other.commit()
    with pytest.raises(ValidationError, match="já começou"):
        update_sequence(db, group.id, user_id=test_user.id, session=test_user.waha_session, messages=["x"],
                        start=datetime(2026, 9, 25, 10, 0), allow_past=True)
    view = schedule_views.get_group_view(db, group.id, test_user.id, TZ)
    assert view is not None and view.editable is False and view.status == "sending"


def test_recurrence_only_for_a_single_message(db, test_user):
    with pytest.raises(ValidationError, match="única mensagem"):
        _sequence(db, test_user, messages=["a", "b"], recurrence="daily 09:00")
    _, (schedule,) = _sequence(db, test_user, messages=["a"], recurrence="daily 09:00")
    assert schedule.recurrence == "0 9 * * *"


def test_validation(db, test_user):
    with pytest.raises(ValidationError, match="vazia"):
        _sequence(db, test_user, messages=["  ", ""])
    with pytest.raises(ValidationError):
        _sequence(db, test_user, messages=["x"] * 21)
    with pytest.raises(ValidationError, match="Timezone"):
        create_sequence(db, user_id=test_user.id, session="s", recipient=CHAT, messages=["a"],
                        start=datetime(2026, 9, 20, 18, 0), timezone="Mars/Olympus")
    with pytest.raises(ValidationError, match="passou"):
        create_sequence(db, user_id=test_user.id, session="s", recipient=CHAT, messages=["a"],
                        start=datetime(2001, 1, 1, 9, 0), timezone=TZ, allow_past=False)
    with pytest.raises(ValidationError):
        create_sequence(db, user_id=test_user.id, session="s", recipient="banana", messages=["a"],
                        start=datetime(2999, 1, 1, 9, 0), timezone=TZ)
    assert db.exec(select(ScheduleGroup)).all() == []  # nada foi gravado pela metade


def test_create_schedule_compat_is_a_group_of_one(db, test_user):
    schedule = create_schedule(db, user_id=test_user.id, session=test_user.waha_session, recipient="+55 14 99111-0001",
                               text="oi", send_at=datetime(2999, 1, 1, 9, 0), timezone=TZ)
    assert schedule.group_id and schedule.position == 0
    assert db.get(ScheduleGroup, schedule.group_id).source == ScheduleSource.manual


# --------------------------------------------------------------------------- #
# Envio: sessão certa, ordem, cancelamento
# --------------------------------------------------------------------------- #
def _second_whatsapp(db, user, name="WhatsApp B") -> WhatsAppSession:
    session = WhatsAppSession(user_id=user.id, name=name)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def test_message_goes_out_through_the_selected_whatsapp(db, test_user, fake_waha, frozen_clock):
    """Teste 10: agendado pelo WhatsApp B -> o job usa o WhatsApp B."""
    wa_a = WhatsAppSession(user_id=test_user.id, name="WhatsApp A")
    db.add(wa_a)
    wa_b = _second_whatsapp(db, test_user)
    _sequence(db, test_user, messages=["pelo B"], start=datetime(2026, 9, 1, 8, 50), session=wa_b.session_name)
    materialize_due()
    assert await dispatch_due(fake_waha) == 1
    assert fake_waha.sent == [{"session": wa_b.session_name, "chatId": CHAT, "text": "pelo B"}]


async def test_sequence_is_sent_in_order_and_appears_in_the_conversation_cache(db, test_user, fake_waha, frozen_clock):
    """Parte 19 (ponta a ponta do backend): agenda -> job -> sessão -> envio -> cache da conversa."""
    _sequence(db, test_user, start=datetime(2026, 9, 1, 8, 50))  # 11:50 UTC, já vencido no relógio congelado (12:00)
    await SchedulerService(fake_waha).run_once()
    assert [m["text"] for m in fake_waha.sent] == [
        "Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."
    ]
    assert {m["session"] for m in fake_waha.sent} == {test_user.waha_session}
    cached = db.exec(select(CachedMessage).where(CachedMessage.chat_id == CHAT)).all()
    assert sorted(m.body for m in cached) == sorted(m["text"] for m in fake_waha.sent)
    group = db.exec(select(ScheduleGroup)).one()
    view = schedule_views.get_group_view(db, group.id, test_user.id, TZ)
    assert view.status == "sent" and [m.status for m in view.messages] == ["sent"] * 3


async def test_later_messages_wait_when_an_earlier_one_fails(db, test_user, fake_waha, frozen_clock):
    _sequence(db, test_user, messages=["a", "b"], start=datetime(2026, 9, 1, 8, 50), max_attempts=1)
    fake_waha.send_error = WahaError("boom")
    await SchedulerService(fake_waha).run_once()
    assert fake_waha.sent == []
    group = db.exec(select(ScheduleGroup)).one()
    db.expire_all()
    view = schedule_views.get_group_view(db, group.id, test_user.id, TZ)
    assert view.messages[0].status == "failed"
    fake_waha.send_error = None
    await SchedulerService(fake_waha).run_once()
    assert fake_waha.sent == []  # a 2ª não sai fora de ordem


async def test_canceled_message_is_never_sent_and_the_others_still_are(db, test_user, fake_waha, frozen_clock):
    """Parte 2.9: cancelar pela conversa = mecanismo atual; a cancelada não vai, as outras seguem."""
    _, schedules = _sequence(db, test_user, start=datetime(2026, 9, 1, 8, 50))
    assert cancel_schedule(db, schedules[1].id, user_id=test_user.id) is True
    await SchedulerService(fake_waha).run_once()
    assert [m["text"] for m in fake_waha.sent] == ["Olá Leonardo!", "Nos vemos às 20h."]
    db.expire_all()
    view = schedule_views.get_group_view(db, schedules[0].group_id, test_user.id, TZ)
    assert [m.status for m in view.messages] == ["sent", "canceled", "sent"]
    assert view.status == "partial"


async def test_canceling_the_whole_group_sends_nothing(db, test_user, fake_waha, frozen_clock):
    group, _ = _sequence(db, test_user, start=datetime(2026, 9, 1, 8, 50))
    assert cancel_group(db, group.id, user_id=test_user.id) is True
    await SchedulerService(fake_waha).run_once()
    assert fake_waha.sent == []
    view = schedule_views.get_group_view(db, group.id, test_user.id, TZ)
    assert view.status == "canceled" and not view.can_cancel
    assert cancel_group(db, group.id, user_id=test_user.id) is False  # já cancelado


async def test_cancel_during_a_failing_send_does_not_resurrect_the_dispatch(db, test_user, fake_waha, frozen_clock):
    """Race real: o usuário cancela enquanto o envio está em andamento e o envio falha — não pode voltar como retry."""
    _, (schedule,) = _sequence(db, test_user, messages=["x"], start=datetime(2026, 9, 1, 8, 50))

    async def cancel_then_fail(session, chat_id, text):
        with Session(get_engine()) as other:
            cancel_schedule(other, schedule.id, user_id=test_user.id)
        raise WahaError("falhou depois de cancelar")

    fake_waha.send_text = cancel_then_fail
    materialize_due()
    await dispatch_due(fake_waha)
    db.expire_all()
    (dispatch,) = _dispatches(db, schedule.id)
    assert dispatch.status == DispatchStatus.canceled


# --------------------------------------------------------------------------- #
# Teste 12: isolamento
# --------------------------------------------------------------------------- #
def test_user_cannot_touch_another_users_schedule(db, test_user):
    other = User(name="Outra", email="outra@example.com", password_hash="x")
    db.add(other)
    db.commit()
    db.refresh(other)
    group, schedules = _sequence(db, test_user)
    assert get_group(db, group.id, other.id) is None
    assert cancel_group(db, group.id, user_id=other.id) is False
    assert cancel_schedule(db, schedules[0].id, user_id=other.id) is False
    with pytest.raises(ValidationError, match="não encontrado"):
        update_sequence(db, group.id, user_id=other.id, session="x", messages=["y"], start=datetime(2999, 1, 1, 9, 0))
    assert schedule_views.get_group_view(db, group.id, other.id, TZ) is None
    assert schedule_views.list_group_views(db, other.id, TZ) == []
    assert all(s.enabled for s in group_schedules(db, group.id))


# --------------------------------------------------------------------------- #
# Visões: status, horário real, conversa
# --------------------------------------------------------------------------- #
def test_group_status_derivation():
    gs = schedule_views.group_status
    assert gs(["scheduled", "scheduled"]) == "scheduled"
    assert gs(["sent", "scheduled"]) == "sending"
    assert gs(["sending", "scheduled"]) == "sending"
    assert gs(["sent", "sent"]) == "sent"
    assert gs(["canceled", "canceled"]) == "canceled"
    assert gs(["sent", "failed"]) == "partial"
    assert gs(["failed", "scheduled"]) == "scheduled"
    assert gs(["failed"]) == "failed"
    assert gs(["skipped"]) == "failed"
    assert gs([]) == "canceled"


def test_list_shows_real_local_time_and_sorts_open_first(db, test_user):
    _sequence(db, test_user, start=datetime(2026, 9, 25, 18, 0))
    later, _ = _sequence(db, test_user, start=datetime(2026, 9, 28, 9, 30))
    cancel_group(db, later.id, user_id=test_user.id)
    views = schedule_views.list_group_views(db, test_user.id, TZ)
    assert [v.status for v in views] == ["scheduled", "canceled"]
    first = views[0]
    assert first.when_local == datetime(2026, 9, 25, 18, 0)
    assert [m.when_local for m in first.messages] == [
        datetime(2026, 9, 25, 18, 0, 0), datetime(2026, 9, 25, 18, 0, 3), datetime(2026, 9, 25, 18, 0, 6)
    ]
    assert first.message_count == 3 and first.recipient == "+5514991110001"


def test_times_are_shown_in_the_users_timezone_not_the_schedules(db, test_user):
    """Todas as telas usam o fuso do usuário (Parte 10), qualquer que seja o fuso gravado no schedule."""
    group, _ = create_sequence(db, user_id=test_user.id, session="s", recipient=CHAT, messages=["a"],
                               start=datetime(2026, 9, 25, 18, 0), timezone="America/New_York")
    (view,) = schedule_views.list_group_views(db, test_user.id, TZ)
    assert view.when_utc == datetime(2026, 9, 25, 22, 0)  # 18:00 em NY (UTC-4)
    assert view.when_local == datetime(2026, 9, 25, 19, 0)  # o mesmo instante, em São Paulo


def test_conversation_items_only_this_chat_and_user(db, test_user):
    _sequence(db, test_user, start=datetime(2026, 9, 25, 18, 0))
    create_sequence(db, user_id=test_user.id, session=test_user.waha_session, recipient="5511999998888@c.us",
                    messages=["outra conversa"], start=datetime(2026, 9, 25, 18, 0), timezone=TZ)
    items, _ = schedule_views.conversation_items(db, test_user.id, test_user.waha_session, CHAT, TZ)
    assert [m.text for m in items] == ["Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."]
    assert all(m.status == "scheduled" for m in items)
    other_items, _ = schedule_views.conversation_items(db, "someone-else", test_user.waha_session, CHAT, TZ)
    assert other_items == []


# --------------------------------------------------------------------------- #
# Migração para o modelo único
# --------------------------------------------------------------------------- #
def test_backfill_groups_legacy_schedules_is_idempotent(db, test_user):
    now_local = datetime(2026, 9, 25, 18, 0)
    legacy = [
        Schedule(user_id=test_user.id, session="s", recipient_input="x", chat_id=CHAT, text=t, timezone=TZ,
                 first_run_local=now_local + timedelta(seconds=3 * i))
        for i, t in enumerate(["um", "dois"])
    ]
    db.add_all(legacy)
    db.commit()
    assert backfill_groups(db) == 2
    assert backfill_groups(db) == 0
    groups = db.exec(select(ScheduleGroup)).all()
    assert len(groups) == 2 and {g.source for g in groups} == {ScheduleSource.manual}
    assert all(s.group_id for s in db.exec(select(Schedule)).all())


def test_backfill_groups_automation_chain_by_recipient(db, test_user):
    from whatsapp_scheduler.models import Event, EventSource

    event = Event(user_id=test_user.id, source=EventSource.internal, title="E", start_utc=datetime(2026, 9, 25, 23, 0),
                  end_utc=datetime(2026, 9, 26, 0, 0), timezone=TZ)
    db.add(event)
    db.commit()
    automation = Automation(event_id=event.id, offset_amount=1, offset_unit="hours", offset_direction="before")
    db.add(automation)
    db.commit()
    for chat in (CHAT, "5511999998888@c.us"):
        for position in (0, 1):
            message = db.exec(select(AutomationMessage).where(col(AutomationMessage.automation_id) == automation.id)
                              .where(col(AutomationMessage.position) == position)).first()
            if message is None:
                message = AutomationMessage(automation_id=automation.id, position=position, text=f"m{position}")
                db.add(message)
                db.commit()
            schedule = Schedule(user_id=test_user.id, session="s", recipient_input=chat, chat_id=chat, text=message.text,
                                timezone=TZ, first_run_local=datetime(2026, 9, 25, 19, 0, 3 * position))
            db.add(schedule)
            db.commit()
            db.add(AutomationSchedule(automation_id=automation.id, message_id=message.id, schedule_id=schedule.id,
                                      recipient_chat_id=chat))
            db.commit()
    assert backfill_groups(db, test_user.id) == 4
    groups = db.exec(select(ScheduleGroup)).all()
    assert len(groups) == 2 and {g.source for g in groups} == {ScheduleSource.calendar}
    for group in groups:
        assert [s.position for s in group_schedules(db, group.id)] == [0, 1]
        assert group.start_local == datetime(2026, 9, 25, 19, 0, 0)


def test_reschedule_group_moves_pending_dispatch_and_every_message(db, test_user):
    group, schedules = _sequence(db, test_user)
    reschedule_group(db, group, datetime(2026, 9, 21, 22, 0))  # UTC
    db.refresh(group)
    rows = group_schedules(db, group.id)
    assert group.start_local == datetime(2026, 9, 21, 19, 0)
    assert [s.first_run_local for s in rows] == [
        datetime(2026, 9, 21, 19, 0, 0), datetime(2026, 9, 21, 19, 0, 3), datetime(2026, 9, 21, 19, 0, 6)
    ]
    (dispatch,) = _dispatches(db, schedules[0].id)
    assert dispatch.scheduled_at_utc == datetime(2026, 9, 21, 22, 0)


# --------------------------------------------------------------------------- #
# Auditoria: achados que viraram teste
# --------------------------------------------------------------------------- #
def test_extreme_dates_are_a_validation_error_not_a_crash(db, test_user):
    for year in (1, 1999, 3001, 9999):
        with pytest.raises(ValidationError, match="intervalo"):
            create_sequence(db, user_id=test_user.id, session="s", recipient=CHAT, messages=["a"],
                            start=datetime(year, 6, 1, 9, 0), timezone=TZ)
    with pytest.raises(ValidationError, match="intervalo"):
        timing.parse_local_input("9999-12-31", "23:59")
    with pytest.raises(ValidationError, match="intervalo"):
        timing.parse_local_input("0001-01-01", "00:00")
    assert db.exec(select(ScheduleGroup)).all() == []


def test_dedupe_collapses_an_identical_double_submit_but_not_a_different_one(db, test_user):
    kwargs = dict(user_id=test_user.id, session=test_user.waha_session, recipient=CHAT, messages=["a", "b"],
                  start=datetime(2999, 9, 20, 18, 0), timezone=TZ, dedupe=True)
    first, _ = create_sequence(db, **kwargs)
    again, schedules = create_sequence(db, **kwargs)
    assert again.id == first.id and len(schedules) == 2
    assert len(db.exec(select(ScheduleGroup)).all()) == 1 and len(db.exec(select(Schedule)).all()) == 2
    other, _ = create_sequence(db, **{**kwargs, "messages": ["a", "c"]})
    later, _ = create_sequence(db, **{**kwargs, "start": datetime(2999, 9, 20, 18, 1)})
    assert len({first.id, other.id, later.id}) == 3
    # cancelado não conta como duplicado: o usuário pode agendar de novo
    cancel_group(db, first.id, user_id=test_user.id)
    fresh, _ = create_sequence(db, **kwargs)
    assert fresh.id not in {first.id, other.id, later.id}


def test_waiting_chain_is_skipped_without_hitting_the_gate(db, test_user, monkeypatch, frozen_clock):
    """Perf: com a 1ª mensagem ainda aberta, as seguintes nem consultam `_dependency_gate` a cada tick."""
    from whatsapp_scheduler import scheduler

    _sequence(db, test_user, messages=["a", "b", "c"], start=datetime(2026, 9, 1, 8, 59))  # ainda no futuro
    calls = []
    real = scheduler._dependency_gate
    monkeypatch.setattr(scheduler, "_dependency_gate", lambda db_, sch: (calls.append(sch.text), real(db_, sch))[1])
    materialize_due()
    assert calls == []  # b e c esperam a cadeia aberta sem gastar consulta
    assert len(db.exec(select(Dispatch)).all()) == 1  # só a 1ª tem dispatch (como antes)


async def test_waiting_chain_still_advances_once_the_first_is_sent(db, test_user, fake_waha, frozen_clock):
    _sequence(db, test_user, messages=["a", "b", "c"], start=datetime(2026, 9, 1, 8, 50))
    materialize_due()
    await dispatch_due(fake_waha)          # a sai
    materialize_due()                      # b vira dispatch (o atalho não pode travar quem já está liberado)
    await dispatch_due(fake_waha)          # b sai
    materialize_due()
    await dispatch_due(fake_waha)          # c sai
    assert [m["text"] for m in fake_waha.sent] == ["a", "b", "c"]


def test_soft_deleted_whatsapp_cannot_be_used(db, test_user):
    import asyncio

    from tests.conftest import FakeWaha
    from whatsapp_scheduler import whatsapp_service
    from whatsapp_scheduler.clock import utcnow

    wa = WhatsAppSession(user_id=test_user.id, name="Antigo", disconnected_at=utcnow())
    db.add(wa)
    db.commit()
    with pytest.raises(ValidationError, match="foi desconectado"):
        asyncio.run(whatsapp_service.require_session_ready(FakeWaha(), wa))


async def test_run_now_moves_the_whole_sequence_not_just_the_first_message(db, test_user, fake_waha, frozen_clock):
    """Achado da revisão: "Enviar agora" antecipava só a 1ª e deixava as outras no horário original."""
    from whatsapp_scheduler.service import run_group_now

    group, schedules = _sequence(db, test_user, start=datetime(2026, 9, 20, 18, 0))
    assert run_group_now(db, group.id, user_id=test_user.id) is True
    db.expire_all()
    rows = group_schedules(db, group.id)
    # FROZEN = 12:00 UTC = 09:00 em São Paulo
    assert [s.first_run_local for s in rows] == [
        datetime(2026, 9, 1, 9, 0, 0), datetime(2026, 9, 1, 9, 0, 3), datetime(2026, 9, 1, 9, 0, 6)]
    for offset in (0, 3, 6):
        frozen_clock["now"] = FROZEN + timedelta(seconds=offset)
        materialize_due()
        await dispatch_due(fake_waha)
    assert [m["text"] for m in fake_waha.sent] == [s.text for s in schedules]
    assert run_group_now(db, group.id, user_id="another-user") is False
