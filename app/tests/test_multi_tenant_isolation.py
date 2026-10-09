"""v1.3, item 43 — teste de isolamento consolidado: dois usuários (A e B),
cada um com seus próprios WhatsApps/eventos/agendamentos/conexões de
calendário, confirmando que um nunca enxerga nem consegue tocar o recurso do
outro só trocando o id na URL (IDOR). Um único TestClient (evita reiniciar o
lifespan do app duas vezes); a "troca de usuário" é feita passando o cookie
de sessão certo em cada chamada, sem depender do cookie jar ambiente do
client."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import FakeWaha, register_and_login
from whatsapp_scheduler import crypto, whatsapp_service
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.config import settings
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import Calendar, CalendarConnection, CalendarConnectionStatus, Event, EventSource


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        yield c


def _login_cookie(client, *, name: str, email: str) -> tuple[str, object]:
    user = register_and_login(client, name=name, email=email)
    token = client.cookies.get(settings.session_cookie_name)
    return token, user


def _as(token: str) -> dict:
    return {"cookies": {settings.session_cookie_name: token}}


def _make_connection_and_event(user_id: str) -> tuple[str, str]:
    now = utcnow()
    with Session(get_engine()) as db:
        conn = CalendarConnection(
            user_id=user_id, provider="google", account_identifier="user@example.com",
            access_token_enc=crypto.encrypt("secret-access"), refresh_token_enc=crypto.encrypt("secret-refresh"),
            token_expires_at=now + timedelta(hours=1), status=CalendarConnectionStatus.active,
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)
        cal = Calendar(connection_id=conn.id, external_id="primary", name="Agenda", enabled=True)
        db.add(cal)
        db.commit()
        event = Event(
            user_id=user_id, source=EventSource.internal, title="Evento privado",
            start_utc=now + timedelta(hours=2), end_utc=now + timedelta(hours=3), timezone="America/Sao_Paulo",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return conn.id, event.id


def test_two_users_never_see_each_others_data(client):
    token_a, user_a = _login_cookie(client, name="Usuário A", email="isolamento-a@example.com")
    token_b, user_b = _login_cookie(client, name="Usuário B", email="isolamento-b@example.com")

    # --- WhatsApp sessions ---------------------------------------------- #
    wa_a = client.post("/api/whatsapp-sessions", json={"name": "WhatsApp A"}, **_as(token_a)).json()
    wa_b = client.post("/api/whatsapp-sessions", json={"name": "WhatsApp B"}, **_as(token_b)).json()

    assert client.get(f"/api/whatsapp-sessions/{wa_a['id']}", **_as(token_b)).status_code == 404
    assert client.post(f"/api/whatsapp-sessions/{wa_a['id']}/rename", json={"name": "hackeado"}, **_as(token_b)).status_code == 404
    assert client.delete(f"/api/whatsapp-sessions/{wa_a['id']}", **_as(token_b)).status_code == 404
    ids_visible_to_b = {row["id"] for row in client.get("/api/whatsapp-sessions", **_as(token_b)).json()}
    assert wa_a["id"] not in ids_visible_to_b

    # A rename real (dono correto) continua funcionando.
    assert client.post(f"/api/whatsapp-sessions/{wa_a['id']}/rename", json={"name": "Renomeado"}, **_as(token_a)).status_code == 200

    # --- Conversas / chats ------------------------------------------------ #
    assert client.get(f"/api/whatsapp-sessions/{wa_a['id']}/chats", **_as(token_b)).status_code == 404
    assert client.get(f"/ui/chats/{wa_a['id']}", **_as(token_b)).status_code == 404

    # --- Agendamentos ------------------------------------------------------ #
    sched_a = client.post(
        "/api/schedules",
        json={"recipient": "5511999998888", "text": "confidencial", "send_at": "2999-01-01T09:00:00", "session": wa_a["session_name"]},
        **_as(token_a),
    ).json()
    assert client.get(f"/api/schedules/{sched_a['id']}", **_as(token_b)).status_code == 404
    assert client.delete(f"/api/schedules/{sched_a['id']}", **_as(token_b)).status_code == 404
    ids_visible_to_b = {row["id"] for row in client.get("/api/schedules", **_as(token_b)).json()}
    assert sched_a["id"] not in ids_visible_to_b

    # B não pode criar um agendamento citando a sessão WhatsApp de A.
    resp = client.post(
        "/api/schedules",
        json={"recipient": "5511999998888", "text": "x", "send_at": "2999-01-01T09:00:00", "session": wa_a["session_name"]},
        **_as(token_b),
    )
    assert resp.status_code == 422

    # --- Calendário / eventos / conexões ----------------------------------- #
    conn_a_id, event_a_id = _make_connection_and_event(user_a.id)

    assert client.get(f"/ui/calendario/events/{event_a_id}", params={"year": 2026, "month": 9}, **_as(token_b)).status_code == 404
    assert client.get(f"/ui/calendario/events/{event_a_id}/edit", params={"year": 2026, "month": 9}, **_as(token_b)).status_code == 404

    events_visible_to_b = [e["id"] for e in client.get("/api/calendar/events", **_as(token_b)).json()]
    assert event_a_id not in events_visible_to_b

    conns_visible_to_b = [c["id"] for c in client.get("/api/calendar/connections", **_as(token_b)).json()]
    assert conn_a_id not in conns_visible_to_b
    assert client.delete(f"/api/calendar/connections/{conn_a_id}", **_as(token_b)).status_code == 404

    # --- Automação: B não consegue criar automação no evento de A --------- #
    resp = client.post(
        f"/api/calendar/events/{event_a_id}/automations",
        json={
            "recipients": ["+55 11 90000-0000"], "messages": ["x"], "offset_amount": 1,
            "offset_unit": "hours", "offset_direction": "before", "whatsapp_session_id": wa_b["id"],
        },
        **_as(token_b),
    )
    assert resp.status_code == 422  # calendar_service.create_event_automation rejeita evento que não é do user_id


def test_timezone_preference_never_leaks_between_users(client):
    """Regressão do bug de isolamento corrigido na fase 3: settings.
    default_timezone era uma variável global mutável — o usuário B mudando
    seu fuso afetava o usuário A também."""
    token_a, _ = _login_cookie(client, name="Usuário Fuso A", email="fuso-a@example.com")
    token_b, _ = _login_cookie(client, name="Usuário Fuso B", email="fuso-b@example.com")

    resp = client.post(
        "/configuracoes/preferencias/timezone", data={"timezone_name": "Asia/Tokyo"}, **_as(token_a)
    )
    assert resp.status_code == 200
    assert "Asia/Tokyo" in resp.text

    # B nunca pediu nada — continua no fallback padrão, não herda Tokyo.
    b_prefs = client.get("/configuracoes", **_as(token_b)).text
    assert 'value="Asia/Tokyo" selected' not in b_prefs

    a_prefs = client.get("/configuracoes", **_as(token_a)).text
    assert 'value="Asia/Tokyo" selected' in a_prefs


def test_qr_code_is_only_served_to_the_owner_of_the_whatsapp_session(client):
    """O QR de pareamento dá controle total do WhatsApp de quem escanear: tem de
    ser entregue só ao dono da conexão, mesmo sabendo o id (IDOR), e nunca em
    cache compartilhado (Cloudflare/proxy)."""
    token_a, user_a = _login_cookie(client, name="A", email="qr-a@example.com")
    token_b, _ = _login_cookie(client, name="B", email="qr-b@example.com")
    with Session(get_engine()) as db:
        session_a = whatsapp_service.primary_session(db, user_a.id)
        session_id_a = session_a.id

    for route in (f"/ui/whatsapps/{session_id_a}/qr", f"/api/whatsapp-sessions/{session_id_a}/qr"):
        own = client.get(route, **_as(token_a))
        assert own.status_code == 200, route
        assert own.headers["cache-control"] == "no-store", route

        assert client.get(route, **_as(token_b)).status_code == 404, route

    anonymous = TestClient(app, follow_redirects=False)
    assert anonymous.get(f"/ui/whatsapps/{session_id_a}/qr").status_code in (303, 401)
