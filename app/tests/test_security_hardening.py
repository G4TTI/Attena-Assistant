"""Endurecimentos da v1.4: CSRF por Origin, cookies, sessões, auditoria de login
sem dado sensível, cabeçalhos e isolamento entre usuários nos recursos novos."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.conftest import FakeWaha, register_and_login, whatsapp_session_id
from whatsapp_scheduler.config import settings
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import AuditEventType, LoginAuditEvent, User, UserSession


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        yield c


def test_cross_site_form_post_is_blocked_but_same_origin_passes(client):
    register_and_login(client)
    evil = client.post("/configuracoes/conta/perfil", data={"name": "Hacked"}, headers={"Origin": "https://evil.example"},
                       follow_redirects=False)
    assert evil.status_code == 403
    evil_ref = client.post("/configuracoes/conta/perfil", data={"name": "Hacked"},
                           headers={"Referer": "https://evil.example/page"}, follow_redirects=False)
    assert evil_ref.status_code == 403
    ok = client.post("/configuracoes/conta/perfil", data={"name": "Legit"}, headers={"Origin": "http://testserver"},
                     follow_redirects=False)
    assert ok.status_code == 303
    with Session(get_engine()) as db:
        assert db.exec(select(User)).one().name == "Legit"


def test_session_cookie_flags(client, monkeypatch):
    resp = client.post("/cadastro", data={"name": "A", "email": "a@example.com", "password": "testpass123",
                                          "password_confirm": "testpass123"}, follow_redirects=False)
    cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    monkeypatch.setattr(settings, "session_cookie_secure", True)
    client.cookies.clear()
    resp = client.post("/login", data={"email": "a@example.com", "password": "testpass123"}, follow_redirects=False)
    assert "secure" in resp.headers["set-cookie"].lower()


def test_login_records_activity_and_failed_login_does_not_store_typed_email(client):
    register_and_login(client, email="b@example.com")
    client.cookies.clear()
    client.post("/login", data={"email": "ninguem-existe@example.com", "password": "x" * 10})
    client.post("/login", data={"email": "b@example.com", "password": "errada-123"})
    client.post("/login", data={"email": "b@example.com", "password": "testpass123"})
    with Session(get_engine()) as db:
        events = db.exec(select(LoginAuditEvent)).all()
        failed = [e for e in events if e.event_type == AuditEventType.login_failed]
        assert len(failed) == 2 and all(e.detail is None for e in failed)
        assert all("ninguem-existe" not in (e.detail or "") for e in events)
        user = db.exec(select(User).where(User.email == "b@example.com")).one()
        assert user.login_count == 2 and user.last_login_at is not None and user.last_activity_at is not None


def test_password_change_revokes_other_sessions(client):
    register_and_login(client, email="c@example.com")
    with Session(get_engine()) as db:
        user = db.exec(select(User)).one()
        from whatsapp_scheduler import auth

        db.add(UserSession(user_id=user.id, token_hash=auth.hash_token("outro-dispositivo"), expires_at=datetime(2999, 1, 1)))
        db.commit()
    r = client.post("/configuracoes/conta/senha", data={
        "current_password": "testpass123", "new_password": "novasenha123", "new_password_confirm": "novasenha123"})
    assert "Outros dispositivos foram desconectados" in r.text
    with Session(get_engine()) as db:
        sessions = db.exec(select(UserSession)).all()
        assert sum(1 for s in sessions if s.revoked_at is None) == 1


def test_private_pages_are_not_cached(client):
    register_and_login(client)
    assert client.get("/planos").headers["cache-control"] == "no-store"
    assert client.get("/configuracoes").headers["cache-control"] == "no-store"


def test_user_b_cannot_touch_user_a_schedules_or_session_data(client):
    register_and_login(client, name="A", email="a2@example.com")
    sid_a = whatsapp_session_id(client)
    created = client.post("/api/schedules", json={"recipient": "+55 14 99111-0001", "text": "só de A",
                                                   "send_at": "2999-01-01T09:00"}).json()
    client.cookies.clear()
    register_and_login(client, name="B", email="b2@example.com")
    assert client.get(f"/api/schedules/{created['id']}").status_code == 404
    assert client.delete(f"/api/schedules/{created['id']}").status_code == 404
    assert client.post(f"/api/schedules/{created['id']}/run-now").status_code == 404
    assert "só de A" not in client.get("/api/schedules").text
    assert client.get(f"/api/whatsapp-sessions/{sid_a}").status_code == 404
    assert client.get(f"/ui/chats/{sid_a}/scheduled", params={"chat": "5514991110001@c.us"}).status_code == 404


def test_session_status_api_does_not_leak_waha_config(client):
    register_and_login(client)
    sid = whatsapp_session_id(client)
    data = client.get(f"/api/whatsapp-sessions/{sid}").json()
    assert set(data) == {"id", "name", "status", "me"}


def test_app_refuses_to_start_without_data_keys(monkeypatch):
    from whatsapp_scheduler import privacy

    monkeypatch.setattr(settings, "data_encryption_keys", "")
    privacy.reset_key_cache()
    try:
        with pytest.raises(privacy.KeyConfigurationError):
            with TestClient(app):
                pass
    finally:
        monkeypatch.undo()
        privacy.reset_key_cache()
