from datetime import datetime

from sqlmodel import Session

from whatsapp_scheduler import whatsapp_service
from whatsapp_scheduler.auth import hash_password
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.models import Schedule, User
from whatsapp_scheduler.service import create_schedule


def _make_user(email: str, waha_session: str) -> User:
    with Session(get_engine()) as session:
        user = User(name="Tester", email=email, password_hash=hash_password("testpass123"), waha_session=waha_session)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def test_migrate_legacy_sessions_preserves_pairing_and_is_idempotent(db):
    user_a = _make_user("a@example.com", "legacy_a")
    user_b = _make_user("b@example.com", "legacy_b")

    whatsapp_service.migrate_legacy_sessions(db)

    sessions_a = whatsapp_service.list_sessions(db, user_a.id)
    sessions_b = whatsapp_service.list_sessions(db, user_b.id)
    assert [s.session_name for s in sessions_a] == ["legacy_a"]
    assert [s.session_name for s in sessions_b] == ["legacy_b"]

    # Rodar de novo não duplica nem cria uma segunda sessão para ninguém.
    whatsapp_service.migrate_legacy_sessions(db)
    assert len(whatsapp_service.list_sessions(db, user_a.id)) == 1
    assert len(whatsapp_service.list_sessions(db, user_b.id)) == 1


def test_create_list_rename_disconnect(db, test_user):
    session = whatsapp_service.create_session(db, test_user.id, "  Trabalho  ")
    assert session.name == "Trabalho"
    assert session.session_name  # gerado automaticamente

    listed = whatsapp_service.list_sessions(db, test_user.id)
    assert [s.id for s in listed] == [session.id]

    renamed = whatsapp_service.rename_session(db, session.id, test_user.id, "Comercial")
    assert renamed is not None
    assert renamed.name == "Comercial"

    assert whatsapp_service.disconnect_session(db, session.id, test_user.id) is True
    assert whatsapp_service.list_sessions(db, test_user.id) == []


def test_disconnect_cancels_open_schedules_for_that_session(db, test_user):
    session = whatsapp_service.create_session(db, test_user.id, "Pessoal")
    schedule = create_schedule(
        db,
        user_id=test_user.id,
        session=session.session_name,
        recipient="5511999998888",
        text="oi",
        send_at=datetime.utcnow(),
    )

    whatsapp_service.disconnect_session(db, session.id, test_user.id)

    refreshed = db.get(Schedule, schedule.id)
    assert refreshed.enabled is False


def test_ownership_is_enforced_across_users(db, test_user):
    other = _make_user("other@example.com", "legacy_other")
    session = whatsapp_service.create_session(db, test_user.id, "Pessoal")

    assert whatsapp_service.get_session(db, session.id, other.id) is None
    assert whatsapp_service.rename_session(db, session.id, other.id, "Hackeado") is None
    assert whatsapp_service.disconnect_session(db, session.id, other.id) is False
    assert whatsapp_service.session_by_name(db, other.id, session.session_name) is None


async def test_status_rows_shows_a_friendly_message_for_a_session_not_created_yet(db):
    from tests.conftest import FakeWaha

    from whatsapp_scheduler import whatsapp_service
    from whatsapp_scheduler.models import WhatsAppSession

    waha = FakeWaha()
    waha.session_exists = False
    rows = await whatsapp_service.status_rows(waha, [WhatsAppSession(user_id="u", name="x", session_name="u_abc")])
    assert rows[0]["status"] is None
    assert rows[0]["status_error"] == whatsapp_service.NOT_STARTED_MESSAGE
    assert waha.created == []  # passivo por padrão

    rows = await whatsapp_service.status_rows(
        waha, [WhatsAppSession(user_id="u", name="x", session_name="u_abc")], ensure=True
    )
    assert rows[0]["status"]["status"] == "STARTING"
    assert waha.created == ["u_abc"]
