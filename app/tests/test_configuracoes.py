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


# --- lista de conexões: atualiza sozinha e não mostra QR fantasma ----------- #
def test_connections_list_polls_fast_until_the_whatsapp_is_connected(client):
    """Regressão: depois de escanear o QR o cartão ficava em "conectando" pra
    sempre, porque a lista (aba Conexões) não tinha nenhuma atualização."""
    client.waha.status = "SCAN_QR_CODE"
    html = client.get("/ui/whatsapps").text
    assert 'hx-get="/ui/whatsapps"' in html
    assert "every 3s" in html

    client.waha.status = "WORKING"
    html = client.get("/ui/whatsapps").text
    assert "every 15s" in html and "every 3s" not in html
    assert "conectado" in html


def test_connections_list_only_shows_the_qr_when_waha_has_one(client):
    client.waha.status = "STARTING"
    starting = client.get("/ui/whatsapps").text
    assert 'alt="QR code"' not in starting
    assert "Conectando ao WhatsApp" in starting
    assert "Escaneie o QR" not in starting

    client.waha.status = "SCAN_QR_CODE"
    ready = client.get("/ui/whatsapps").text
    assert 'alt="QR code"' in ready
    assert "Escaneie o QR" in ready


def test_connections_list_keeps_polling_after_a_waha_error(client):
    """Erro de status (WAHA fora do ar) não pode parar a atualização: quando
    o WAHA volta, o cartão precisa se corrigir sozinho."""
    from whatsapp_scheduler.waha import WahaError

    client.waha.status_error = WahaError("Falha de conexão com o WAHA")
    html = client.get("/ui/whatsapps").text
    assert "every 3s" in html


def test_connections_list_preserves_the_qr_image_across_polls(client):
    import re

    client.waha.status = "SCAN_QR_CODE"
    html = client.get("/ui/whatsapps").text
    img = re.search(r"<img[^>]*alt=\"QR code\"[^>]*>", html).group(0)
    assert re.search(r'id="qr-[0-9a-f-]+"', img)
    assert 'hx-preserve="true"' in img
    assert 'data-qr-src="/ui/whatsapps/' in img


def test_connections_list_qr_image_has_no_src_in_the_html(client):
    import re

    client.waha.status = "SCAN_QR_CODE"
    img = re.search(r"<img[^>]*alt=\"QR code\"[^>]*>", client.get("/ui/whatsapps").text).group(0)
    assert " src=" not in img
