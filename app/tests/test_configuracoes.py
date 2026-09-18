import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeWaha, register_and_login
from whatsapp_scheduler.main import app


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        user = register_and_login(c)
        c.user = user
        yield c


def test_configuracoes_page_has_both_tabs_in_one_response(client):
    """WhatsApps deixou de ser página própria — vira a aba "Conexões" de
    Configurações, ao lado de "Preferências". As duas abas são renderizadas
    na mesma resposta (o JS só alterna a visibilidade), então uma única
    requisição já contém tudo."""
    resp = client.get("/configuracoes")
    assert resp.status_code == 200
    assert "Preferências" in resp.text
    assert "Conexões" in resp.text
    assert "Minha conta" in resp.text
    assert "WhatsApps" in resp.text
    assert "Calendários" in resp.text
    assert 'data-tab-panel="preferencias"' in resp.text
    assert 'data-tab-panel="conexoes"' in resp.text


def test_whatsapps_route_redirects_to_configuracoes_conexoes_tab(client):
    resp = client.get("/whatsapps", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/configuracoes?tab=conexoes"


def test_dashboard_no_longer_links_the_old_whatsapps_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'href="/whatsapps"' not in resp.text
    assert 'href="/configuracoes?tab=conexoes"' in resp.text
