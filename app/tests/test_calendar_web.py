import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from tests.conftest import FakeWaha, register_and_login, whatsapp_session_id
from whatsapp_scheduler import calendar_service
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import Automation, Event, EventSource, WhatsAppSession


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
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


def test_automation_modal_shows_repeat_toggle_defaulting_to_no_without_querying_similar_events(client, monkeypatch):
    """Regressão de performance: `similar_events` varre todos os eventos
    futuros do usuário e virou o gargalo seguinte depois que resolvemos o
    dos contatos — abrir o modal não pode mais rodar essa busca de cara,
    só quando a pessoa escolhe "Sim" no seletor."""
    def boom(*args, **kwargs):
        raise AssertionError("abrir o modal não deveria calcular eventos iguais")

    monkeypatch.setattr(calendar_service, "similar_events", boom)

    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))

    resp = client.get(
        f"/ui/calendario/events/{event_a}/automation/new", params={"year": 2026, "month": 9}
    )
    assert resp.status_code == 200
    assert 'hx-get="/ui/calendario/events/' in resp.text
    assert '<option value="nao" selected>Não</option>' in resp.text
    assert "select-all-similar-events" not in resp.text  # checklist não veio pré-carregada


def test_choosing_sim_opens_the_box_first_without_running_the_search(client, monkeypatch):
    """Passo 1: escolher "Sim" só abre a caixa (com a bolinha) — a varredura
    de eventos iguais não pode rodar aqui, só quando a caixa dispara o passo 2."""
    def boom(*args, **kwargs):
        raise AssertionError("abrir a caixa não deveria buscar eventos iguais")

    monkeypatch.setattr(calendar_service, "similar_events", boom)

    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))

    resp = client.get(f"/ui/calendario/events/{event_a}/similar-events", params={"repeat_choice": "sim"})
    assert resp.status_code == 200
    assert "Buscando quando este evento se repete" in resp.text
    # a caixa dispara a busca sozinha, e fixa o próprio alvo (o <form> pai tem
    # hx-target="#modal-root", que o htmx herdaria e apagaria o modal inteiro)
    assert 'hx-trigger="load"' in resp.text
    assert 'hx-target="this"' in resp.text
    assert "search=1" in resp.text


def test_similar_events_search_step_lists_future_matches(client):
    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    _make_event(client.user.id, "Aula Tales", now + timedelta(days=8), now + timedelta(days=8, hours=1))

    resp = client.get(
        f"/ui/calendario/events/{event_a}/similar-events", params={"repeat_choice": "sim", "search": 1}
    )
    assert resp.status_code == 200
    assert "Selecionar todas (1)" in resp.text
    assert "similar-event-checkbox" in resp.text


def test_similar_events_search_step_empty_state_when_no_matches(client):
    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))

    resp = client.get(
        f"/ui/calendario/events/{event_a}/similar-events", params={"repeat_choice": "sim", "search": 1}
    )
    assert resp.status_code == 200
    assert "não se repete" in resp.text


def test_lazy_similar_events_endpoint_returns_nothing_and_skips_the_query_when_repeat_choice_is_not_sim(client, monkeypatch):
    """O seletor dispara esta rota em toda mudança (não só "sim" -> "não"
    também manda um GET, pra limpar o painel sem depender de um onchange
    em paralelo brigando com o htmx por causa de ordem de eventos). Esse
    caminho não pode rodar `similar_events` (a varredura cara) — só o
    caminho "sim" precisa dela."""
    def boom(*args, **kwargs):
        raise AssertionError("repeat_choice != sim não deveria calcular eventos iguais")

    monkeypatch.setattr(calendar_service, "similar_events", boom)

    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))

    resp = client.get(f"/ui/calendario/events/{event_a}/similar-events", params={"repeat_choice": "nao"})
    assert resp.status_code == 200
    assert resp.text == ""


def test_lazy_similar_events_endpoint_ignored_for_another_users_event(client):
    now = utcnow()
    original_email = client.user.email
    other = register_and_login(client, name="Outro", email="calendar-other-similar@example.com")
    event_other = _make_event(other.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    client.post("/login", data={"email": original_email, "password": "testpass123", "next": ""}, follow_redirects=False)

    resp = client.get(f"/ui/calendario/events/{event_other}/similar-events")
    assert resp.status_code == 404


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


def test_bulk_automation_creation_is_offloaded_to_a_worker_thread(client, monkeypatch):
    """Regressão de performance: uma recorrência com muitas ocorrências (ex.:
    uma aula semanal com um ano de eventos) marcada em "Selecionar todos"
    dispara dezenas de create_event_automation, cada um com vários commits no
    SQLite. Feito direto na coroutine da rota, isso bloquearia o único event
    loop do processo pelo tempo somado de todos — nem o poll da sidebar nem
    outro usuário seriam atendidos nesse meio tempo (foi exatamente o que
    deixou "o sistema lento" depois desta feature). A rota precisa despachar
    esse trabalho via asyncio.to_thread."""
    from whatsapp_scheduler.web import calendar_routes

    calls = []
    real_to_thread = asyncio.to_thread

    async def spy_to_thread(func, *args, **kwargs):
        calls.append(func)
        return await real_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(calendar_routes.asyncio, "to_thread", spy_to_thread)

    now = utcnow()
    event_a = _make_event(client.user.id, "Aula Tales", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    event_b = _make_event(client.user.id, "Aula Tales", now + timedelta(days=8), now + timedelta(days=8, hours=1))
    wa_id = whatsapp_session_id(client)

    resp = client.post(
        f"/ui/calendario/events/{event_a}/automation",
        data={
            "recipients": ["5511999998888"], "messages": ["Lembrete"],
            "offset_interval": "1:hours", "offset_direction": "before",
            "whatsapp_session_id": wa_id, "apply_to_event_ids": [event_b], "year": 2026, "month": 9,
        },
    )
    assert resp.status_code == 200
    assert len(calls) == 1  # a criação em lote foi despachada via asyncio.to_thread, não direto na coroutine
    assert len(_automations_of(event_a)) == 1
    assert len(_automations_of(event_b)) == 1


# --------------------------------------------------------------------------- #
# Modal de automação abre instantâneo — contatos carregam à parte (v1.3)
# --------------------------------------------------------------------------- #
def test_opening_automation_modal_never_calls_waha_for_contacts(client):
    """A única coisa no modal que dependia de rede (lista de contatos do
    WAHA) agora é buscada à parte, depois do modal já estar na tela — abrir
    "Adicionar automação" precisa ser instantâneo mesmo se o WAHA estiver
    lento ou fora do ar."""
    event_a = _make_event(client.user.id, "Aula Tales", utcnow() + timedelta(days=1), utcnow() + timedelta(days=1, hours=1))

    async def boom(*args, **kwargs):
        raise AssertionError("abrir o modal não deveria chamar o WAHA")

    client.waha.get_chats_overview = boom

    resp = client.get(f"/ui/calendario/events/{event_a}/automation/new", params={"year": 2026, "month": 9})
    assert resp.status_code == 200
    assert "Carregando contatos" in resp.text


def test_automation_modal_popover_points_to_the_lazy_contacts_endpoint(client):
    event_a = _make_event(client.user.id, "Aula Tales", utcnow() + timedelta(days=1), utcnow() + timedelta(days=1, hours=1))

    resp = client.get(f"/ui/calendario/events/{event_a}/automation/new", params={"year": 2026, "month": 9})
    assert resp.status_code == 200
    # Ao criar (sem edição prévia), nenhum WhatsApp está "selecionado" ainda
    # — o parâmetro vai vazio e o endpoint preguiçoso cai pro primary_session.
    assert 'hx-get="/ui/calendario/contacts?whatsapp_session_id="' in resp.text
    # carrega quando o modal abre e de novo quando o usuário troca o WhatsApp ("reload", ver whatsappPickerChanged)
    assert 'hx-trigger="load, reload"' in resp.text


def test_lazy_contacts_endpoint_returns_contacts_for_the_given_whatsapp(client):
    client.waha.chats = [
        {"id": "5511999998888@c.us", "name": "Fulano", "lastMessage": {}},
    ]
    wa_id = whatsapp_session_id(client)

    resp = client.get("/ui/calendario/contacts", params={"whatsapp_session_id": wa_id})
    assert resp.status_code == 200
    assert "Fulano" in resp.text


def test_lazy_contacts_endpoint_ignored_for_unowned_whatsapp_session(client):
    resp = client.get("/ui/calendario/contacts", params={"whatsapp_session_id": "does-not-exist"})
    assert resp.status_code == 200
    assert "Conecte um WhatsApp" in resp.text


def test_edit_automation_modal_pins_down_whatsapp_and_prefill_ids_for_the_lazy_fetch(client):
    event_a = _make_event(client.user.id, "Aula Tales", utcnow() + timedelta(days=1), utcnow() + timedelta(days=1, hours=1))
    wa_id = whatsapp_session_id(client)
    with Session(get_engine()) as db:
        wa_session_name = db.get(WhatsAppSession, wa_id).session_name
        automation = calendar_service.create_event_automation(
            db, event_id=event_a, user_id=client.user.id, waha_session=wa_session_name,
            recipients=["+55 11 99999-8888"], messages=["Lembrete"],
            offset_amount=1, offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id

    resp = client.get(f"/ui/calendario/automations/{automation_id}/edit", params={"year": 2026, "month": 9})
    assert resp.status_code == 200
    assert f"whatsapp_session_id={wa_id}" in resp.text
    assert "prefill_id=5511999998888%40c.us" in resp.text
