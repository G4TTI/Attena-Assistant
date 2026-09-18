"""v1.3, itens 2 e 45-46 — prova de que a migração para multiusuário nunca
perde dado: dados criados ANTES de existir autenticação (user_id NULL) e a
sessão WAHA já pareada (`User.waha_session`) sobrevivem intactos ao virar
"do primeiro usuário cadastrado", sem duplicar nem exigir novo QR code."""

from datetime import timedelta

from sqlmodel import Session, col, select

from whatsapp_scheduler import auth_service, crypto, whatsapp_service
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.config import settings
from whatsapp_scheduler.models import (
    CachedMessage,
    CalendarConnection,
    CalendarConnectionStatus,
    Event,
    EventSource,
    Schedule,
    WhatsAppSession,
)


def _seed_orphan_data(db: Session) -> dict:
    """Dados criados quando o app só tinha um usuário (user_id NULL) —
    exatamente o estado de antes da v1.3 chegar."""
    now = utcnow()
    schedule = Schedule(
        session=settings.waha_session,  # sessão do .env, já pareada
        recipient_input="+55 11 99999-8888", chat_id="5511999998888@c.us", text="lembrete antigo",
        timezone="America/Sao_Paulo", first_run_local=now,
    )
    db.add(schedule)
    cached_message = CachedMessage(
        message_id="MSGID1", chat_id="5511999998888@c.us", ts=int(now.timestamp()), from_me=True, body="oi",
    )
    db.add(cached_message)
    connection = CalendarConnection(
        provider="google", account_identifier="antigo@example.com",
        access_token_enc=crypto.encrypt("tok"), refresh_token_enc=crypto.encrypt("refresh"),
        token_expires_at=now + timedelta(hours=1), status=CalendarConnectionStatus.active,
    )
    db.add(connection)
    event = Event(
        source=EventSource.internal, title="Evento antigo",
        start_utc=now + timedelta(hours=2), end_utc=now + timedelta(hours=3), timezone="America/Sao_Paulo",
    )
    db.add(event)
    db.commit()
    return {
        "schedule_id": schedule.id, "message_id": cached_message.message_id,
        "connection_id": connection.id, "event_id": event.id,
    }


def test_first_user_to_register_inherits_all_orphan_data_and_the_paired_session(db):
    ids = _seed_orphan_data(db)

    user = auth_service.register_user(
        db, name="Dono original", email="dono@example.com", password="testpass123", password_confirm="testpass123",
    )

    # Nenhum dado órfão foi perdido — todos agora pertencem ao primeiro usuário.
    schedule = db.get(Schedule, ids["schedule_id"])
    assert schedule.user_id == user.id
    assert schedule.session == settings.waha_session  # preserva a sessão já pareada, não gera uma nova

    message = db.get(CachedMessage, ids["message_id"])
    assert message.user_id == user.id

    connection = db.get(CalendarConnection, ids["connection_id"])
    assert connection.user_id == user.id

    event = db.get(Event, ids["event_id"])
    assert event.user_id == user.id

    # A sessão WAHA já pareada (settings.waha_session) foi herdada pelo
    # usuário — não um nome novo gerado aleatoriamente.
    assert user.waha_session == settings.waha_session

    # E a primeira WhatsAppSession do usuário usa EXATAMENTE esse mesmo nome
    # — ninguém precisa escanear QR code de novo.
    sessions = whatsapp_service.list_sessions(db, user.id)
    assert len(sessions) == 1
    assert sessions[0].session_name == settings.waha_session


def test_second_user_does_not_steal_the_first_users_orphan_data(db):
    ids = _seed_orphan_data(db)
    first = auth_service.register_user(
        db, name="Primeiro", email="primeiro@example.com", password="testpass123", password_confirm="testpass123",
    )
    second = auth_service.register_user(
        db, name="Segundo", email="segundo@example.com", password="testpass123", password_confirm="testpass123",
    )

    schedule = db.get(Schedule, ids["schedule_id"])
    assert schedule.user_id == first.id
    assert schedule.user_id != second.id

    # O segundo usuário ganha sua própria WhatsAppSession nova (nome
    # aleatório, nunca reaproveitando settings.waha_session de novo).
    second_sessions = whatsapp_service.list_sessions(db, second.id)
    assert len(second_sessions) == 1
    assert second_sessions[0].session_name != settings.waha_session
    assert second.waha_session != settings.waha_session


def test_migrate_legacy_sessions_is_idempotent_and_never_duplicates(db):
    ids = _seed_orphan_data(db)
    user = auth_service.register_user(
        db, name="Dono", email="dono2@example.com", password="testpass123", password_confirm="testpass123",
    )
    assert len(whatsapp_service.list_sessions(db, user.id)) == 1

    # Rodar a migração de boot de novo (ex.: reinício do processo) não cria
    # uma segunda sessão nem apaga a existente.
    whatsapp_service.migrate_legacy_sessions(db)
    sessions = db.exec(select(WhatsAppSession).where(col(WhatsAppSession.user_id) == user.id)).all()
    assert len(sessions) == 1
    assert sessions[0].session_name == settings.waha_session
