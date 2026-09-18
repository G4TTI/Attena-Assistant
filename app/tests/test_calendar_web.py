from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from tests.conftest import register_and_login, whatsapp_session_id
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import Automation, Event, EventSource


@pytest.fixture
def client():
    with TestClient(app) as c:
        user = register_and_login(c)
        c.user = user
        yield c


def _make_event(user_id: str, title: str, start_utc, end_utc) -> str:
    with Session(get_engine()) as db:
        event = Event(
            user_id=user_id, source=EventSource.internal, title=title, start_utc=start_utc, end_utc=end_utc,
            timezone="America/Sao_Paulo",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event.id


def test_month_grid_hoje_button_links_to_day_view(client):
    resp = client.get("/calendario")
    assert resp.status_code == 200
    assert 'href="/calendario/dia?date=' in resp.text
    # regressão do bug original: "Hoje" não pode mais só recarregar o mês.
    assert 'hx-get="/ui/calendario/grid?year={{ today_year }}' not in resp.text


def test_day_view_page_shows_todays_event(client):
    now = utcnow()
    _make_event(client.user.id, "Reunião de hoje", now + timedelta(hours=1), now + timedelta(hours=2))

    resp = client.get("/calendario/dia")
    assert resp.status_code == 200
    assert "Reunião de hoje" in resp.text


def test_day_view_partial_navigates_between_days(client):
    resp = client.get("/calendario/dia", params={"date": "2026-09-17"})
    assert resp.status_code == 200
    assert "2026-09-16" in resp.text  # dia anterior no nav
    assert "2026-09-18" in resp.text  # próximo dia no nav

    partial = client.get("/ui/calendario/dia", params={"date": "2026-09-17"})
    assert partial.status_code == 200
    assert 'id="calendar-day-view"' in partial.text


def test_day_view_does_not_leak_other_days_events(client):
    now = utcnow()
    _make_event(client.user.id, "Evento de hoje", now, now + timedelta(hours=1))
    _make_event(client.user.id, "Semana que vem", now + timedelta(days=7), now + timedelta(days=7, hours=1))

    resp = client.get("/calendario/dia")
    assert "Evento de hoje" in resp.text
    assert "Semana que vem" not in resp.text


# --------------------------------------------------------------------------- #
# "Repetir esta automação" em eventos iguais
# --------------------------------------------------------------------------- #
def _automations_of(event_id: str) -> list[Automation]:
    with Session(get_engine()) as db:
        return list(db.exec(select(Automation).where(col(Automation.event_id) == event_id)).all())


def test_automation_modal_lists_similar_future_events(client):
    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    _make_event(client.user.id, "Aula Tales", now + timedelta(days=8), now + timedelta(days=8, hours=1))

    resp = client.get(
        f"/ui/calendario/events/{event_a}/automation/new", params={"year": 2026, "month": 9}
    )
    assert resp.status_code == 200
    assert "Repetir esta automação" in resp.text
    assert "1 evento igual" in resp.text


def test_create_automation_applies_to_selected_similar_events(client):
    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    event_b = _make_event(client.user.id, "Aula Tales", now + timedelta(days=8), now + timedelta(days=8, hours=1))
    wa_id = whatsapp_session_id(client)

    resp = client.post(
        f"/ui/calendario/events/{event_a}/automation",
        data={
            "recipients": ["5511999998888"], "messages": ["Lembrete da aula"],
            "offset_interval": "1:hours", "offset_direction": "before",
            "whatsapp_session_id": wa_id, "apply_to_event_ids": [event_b], "year": 2026, "month": 9,
        },
    )
    assert resp.status_code == 200

    assert len(_automations_of(event_a)) == 1
    assert len(_automations_of(event_b)) == 1


def test_create_automation_ignores_unrelated_event_id_even_if_submitted(client):
    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    event_c = _make_event(client.user.id, "Reunião não relacionada", now + timedelta(days=2), now + timedelta(days=2, hours=1))
    wa_id = whatsapp_session_id(client)

    resp = client.post(
        f"/ui/calendario/events/{event_a}/automation",
        data={
            "recipients": ["5511999998888"], "messages": ["Lembrete"],
            "offset_interval": "1:hours", "offset_direction": "before",
            "whatsapp_session_id": wa_id, "apply_to_event_ids": [event_c], "year": 2026, "month": 9,
        },
    )
    assert resp.status_code == 200

    assert len(_automations_of(event_a)) == 1
    assert len(_automations_of(event_c)) == 0


def test_create_automation_ignores_another_users_event_id_even_if_submitted(client):
    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    wa_id = whatsapp_session_id(client)

    original_email = client.user.email
    other = register_and_login(client, name="Outro", email="calendar-other@example.com")
    event_other = _make_event(other.id, "Aula Tales", now + timedelta(days=8), now + timedelta(days=8, hours=1))
    # login de volta como o usuário original (register_and_login trocou o cookie do client pro "outro")
    login_resp = client.post(
        "/login", data={"email": original_email, "password": "testpass123", "next": ""}, follow_redirects=False
    )
    assert login_resp.status_code == 303

    resp = client.post(
        f"/ui/calendario/events/{event_a}/automation",
        data={
            "recipients": ["5511999998888"], "messages": ["Lembrete"],
            "offset_interval": "1:hours", "offset_direction": "before",
            "whatsapp_session_id": wa_id, "apply_to_event_ids": [event_other], "year": 2026, "month": 9,
        },
    )
    assert resp.status_code == 200

    assert len(_automations_of(event_a)) == 1
    assert len(_automations_of(event_other)) == 0
