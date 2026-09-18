from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import register_and_login
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import Event, EventSource


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
