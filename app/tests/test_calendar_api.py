from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import register_and_login, whatsapp_session_id
from whatsapp_scheduler import crypto
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import Calendar, CalendarConnection, CalendarConnectionStatus, Event, EventSource


@pytest.fixture
def client():
    with TestClient(app) as c:
        user = register_and_login(c)
        c.user = user
        yield c


def make_connection_calendar_event(user_id: str) -> tuple[str, str, str]:
    now = utcnow()
    with Session(get_engine()) as db:
        conn = CalendarConnection(
            user_id=user_id,
            provider="google",
            account_identifier="user@example.com",
            access_token_enc=crypto.encrypt("super-secret-access-token"),
            refresh_token_enc=crypto.encrypt("super-secret-refresh-token"),
            token_expires_at=now + timedelta(hours=1),
            status=CalendarConnectionStatus.active,
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)
        cal = Calendar(connection_id=conn.id, external_id="primary", name="Meu calendário", enabled=True)
        db.add(cal)
        db.commit()
        db.refresh(cal)
        event = Event(
            user_id=user_id,
            source=EventSource.google,
            calendar_id=cal.id,
            external_id="ext-1",
            title="Consulta com Leonardo",
            start_utc=now + timedelta(hours=2),
            end_utc=now + timedelta(hours=3),
            timezone="America/Sao_Paulo",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return conn.id, cal.id, event.id


def test_list_connections_never_exposes_tokens(client):
    conn_id, _, _ = make_connection_calendar_event(client.user.id)
    resp = client.get("/api/calendar/connections")
    assert resp.status_code == 200
    body_text = resp.text
    assert "super-secret-access-token" not in body_text
    assert "super-secret-refresh-token" not in body_text
    ids = [c["id"] for c in resp.json()]
    assert conn_id in ids
    assert "access_token" not in resp.json()[0]
    assert "refresh_token" not in resp.json()[0]


def test_toggle_calendar(client):
    _, cal_id, _ = make_connection_calendar_event(client.user.id)
    resp = client.post(f"/api/calendar/calendars/{cal_id}/toggle", json={"enabled": False})
    assert resp.status_code == 200, resp.text
    assert resp.json()["enabled"] is False


def test_create_automation_produces_one_of_each(client):
    _, _, event_id = make_connection_calendar_event(client.user.id)
    resp = client.post(
        f"/api/calendar/events/{event_id}/automations",
        json={
            "recipients": ["+55 11 99999-8888"],
            "messages": ["Olá Leonardo, passando para lembrar da nossa consulta."],
            "offset_amount": 2,
            "offset_unit": "hours",
            "offset_direction": "before",
            "whatsapp_session_id": whatsapp_session_id(client),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["recipients"] == ["+55 11 99999-8888"]
    assert body["messages"] == ["Olá Leonardo, passando para lembrar da nossa consulta."]
    assert body["offset_amount"] == 2

    events = client.get("/api/calendar/events").json()
    event = next(e for e in events if e["id"] == event_id)
    assert len(event["automations"]) == 1
    assert event["is_external"] is True


def test_delete_automation_cancels_without_deleting_event(client):
    _, _, event_id = make_connection_calendar_event(client.user.id)
    created = client.post(
        f"/api/calendar/events/{event_id}/automations",
        json={
            "recipients": ["+55 11 99999-8888"],
            "messages": ["x"],
            "offset_amount": 1,
            "offset_unit": "hours",
            "offset_direction": "before",
            "whatsapp_session_id": whatsapp_session_id(client),
        },
    ).json()
    automation_id = created["id"]

    resp = client.delete(f"/api/calendar/automations/{automation_id}")
    assert resp.status_code == 200

    events = client.get("/api/calendar/events").json()
    assert any(e["id"] == event_id for e in events)  # evento continua existindo


def test_create_automation_with_multiple_messages_and_recipients(client):
    _, _, event_id = make_connection_calendar_event(client.user.id)
    resp = client.post(
        f"/api/calendar/events/{event_id}/automations",
        json={
            "recipients": ["+55 11 99999-8888", "+55 11 98888-7777"],
            "messages": ["um", "dois", "três"],
            "offset_amount": 1,
            "offset_unit": "hours",
            "offset_direction": "before",
            "whatsapp_session_id": whatsapp_session_id(client),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert set(body["recipients"]) == {"+55 11 99999-8888", "+55 11 98888-7777"}
    assert body["messages"] == ["um", "dois", "três"]


def test_create_automation_rejects_empty_recipients(client):
    _, _, event_id = make_connection_calendar_event(client.user.id)
    resp = client.post(
        f"/api/calendar/events/{event_id}/automations",
        json={
            "recipients": [], "messages": ["x"], "offset_amount": 1, "offset_unit": "hours", "offset_direction": "before",
            "whatsapp_session_id": whatsapp_session_id(client),
        },
    )
    assert resp.status_code == 422


def test_disconnect_connection(client):
    conn_id, _, _ = make_connection_calendar_event(client.user.id)
    resp = client.delete(f"/api/calendar/connections/{conn_id}")
    assert resp.status_code == 200
    conns = client.get("/api/calendar/connections").json()
    # Desconectada = soft-delete: some da lista (nao aparece mais como conta
    # conectada nem vira a "conexao principal" do Dashboard), mesmo a linha
    # continuando no banco para preservar o historico de schedules cancelados.
    assert conn_id not in [c["id"] for c in conns]
