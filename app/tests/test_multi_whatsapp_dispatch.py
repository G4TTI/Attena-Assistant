"""v1.3 — prova de que o scheduler nunca mistura sessões WAHA quando um
usuário tem múltiplos WhatsApps, e que duas automações do mesmo evento podem
sair por números diferentes (itens 15-17, 36, 44 do pedido)."""

from datetime import timedelta

from sqlmodel import Session, col, select

from tests.conftest import FakeWaha
from whatsapp_scheduler import calendar_service, whatsapp_service
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.models import Event, EventSource, Schedule
from whatsapp_scheduler.recurrence import utc_to_local
from whatsapp_scheduler.scheduler import dispatch_due, materialize_due
from whatsapp_scheduler.service import create_schedule

TZ = "America/Sao_Paulo"


async def test_dispatch_routes_each_schedule_through_its_own_whatsapp_session(test_user):
    now = utcnow()
    with Session(get_engine()) as db:
        wa_a = whatsapp_service.create_session(db, test_user.id, "Pessoal")
        wa_b = whatsapp_service.create_session(db, test_user.id, "Trabalho")

        create_schedule(
            db, user_id=test_user.id, session=wa_a.session_name, recipient="5511999998888",
            text="mensagem pessoal", send_at=utc_to_local(now - timedelta(minutes=1), TZ), timezone=TZ,
        )
        create_schedule(
            db, user_id=test_user.id, session=wa_b.session_name, recipient="5511988887777",
            text="mensagem de trabalho", send_at=utc_to_local(now - timedelta(minutes=1), TZ), timezone=TZ,
        )
        session_a_name, session_b_name = wa_a.session_name, wa_b.session_name

    waha = FakeWaha()
    materialize_due()
    sent = await dispatch_due(waha)

    assert sent == 2
    sent_by_session = {row["session"]: row for row in waha.sent}
    assert sent_by_session[session_a_name]["chatId"] == "5511999998888@c.us"
    assert sent_by_session[session_a_name]["text"] == "mensagem pessoal"
    assert sent_by_session[session_b_name]["chatId"] == "5511988887777@c.us"
    assert sent_by_session[session_b_name]["text"] == "mensagem de trabalho"


async def test_two_automations_on_same_event_send_through_different_whatsapps(test_user):
    now = utcnow()
    with Session(get_engine()) as db:
        wa_a = whatsapp_service.create_session(db, test_user.id, "Pessoal")
        wa_b = whatsapp_service.create_session(db, test_user.id, "Comercial")

        event = Event(
            user_id=test_user.id, source=EventSource.internal, title="Consulta",
            start_utc=now + timedelta(hours=2), end_utc=now + timedelta(hours=3), timezone=TZ,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        calendar_service.create_event_automation(
            db, event_id=event.id, user_id=test_user.id, waha_session=wa_a.session_name,
            recipients=["+55 11 99999-8888"], messages=["lembrete pessoal"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        calendar_service.create_event_automation(
            db, event_id=event.id, user_id=test_user.id, waha_session=wa_b.session_name,
            recipients=["+55 11 97777-6666"], messages=["lembrete comercial"],
            offset_amount=2, offset_unit="hours", offset_direction="before",
        )

        session_a_name, session_b_name = wa_a.session_name, wa_b.session_name

    with Session(get_engine()) as db:
        schedules = db.exec(select(Schedule).where(col(Schedule.user_id) == test_user.id)).all()
    by_recipient = {s.recipient_input: s.session for s in schedules}
    assert by_recipient["+55 11 99999-8888"] == session_a_name
    assert by_recipient["+55 11 97777-6666"] == session_b_name
