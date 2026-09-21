import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import FakeWaha, register_and_login
from whatsapp_scheduler import onboarding_service
from whatsapp_scheduler.auth import hash_password
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import User


def _make_user(email: str) -> User:
    with Session(get_engine()) as session:
        user = User(name="Legado", email=email, password_hash=hash_password("testpass123"))
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def test_migrate_legacy_users_marks_existing_accounts_as_done_and_is_idempotent(db):
    user = _make_user("legado@example.com")
    assert user.onboarding_completed_at is None

    onboarding_service.migrate_legacy_users(db)
    migrated = db.get(User, user.id)
    assert migrated.onboarding_completed_at is not None

    # Não sobrescreve de novo numa segunda chamada (flag em AppSetting já existe).
    first_run_value = migrated.onboarding_completed_at
    onboarding_service.migrate_legacy_users(db)
    assert db.get(User, user.id).onboarding_completed_at == first_run_value


def test_first_incomplete_step_progression():
    assert onboarding_service.first_incomplete_step(
        {"whatsapp_connected": False, "google_connected": False, "timezone_set": False}
    ) == 1
    assert onboarding_service.first_incomplete_step(
        {"whatsapp_connected": True, "google_connected": False, "timezone_set": False}
    ) == 2
    assert onboarding_service.first_incomplete_step(
        {"whatsapp_connected": True, "google_connected": True, "timezone_set": False}
    ) == 3
    assert onboarding_service.first_incomplete_step(
        {"whatsapp_connected": True, "google_connected": True, "timezone_set": True}
    ) == 4


@pytest.fixture
def client():
    """Usuário recém-cadastrado, SEM pular onboarding — pra exercitar o
    fluxo/gate de verdade (a maioria dos outros testes usa
    `skip_onboarding=True`, o padrão de `register_and_login`)."""
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        user = register_and_login(c, skip_onboarding=False)
        c.user = user
        yield c


def test_fresh_user_is_redirected_to_onboarding(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/onboarding"


def test_onboarding_page_defaults_to_first_step(client):
    client.waha.status = "SCAN_QR_CODE"  # sem isso o FakeWaha reporta WORKING por padrão
    resp = client.get("/onboarding")
    assert resp.status_code == 200
    assert "Conecte seu WhatsApp" in resp.text


def test_skip_whatsapp_step_advances_to_google(client):
    resp = client.get("/onboarding/pular", params={"step": 1})
    assert resp.status_code == 200
    assert "Conecte seu calendário" in resp.text


def test_whatsapp_step_form_has_phone_field(client):
    client.waha.status = "SCAN_QR_CODE"  # sem isso o FakeWaha reporta WORKING e pula pro passo 2
    resp = client.get("/onboarding")
    assert resp.status_code == 200
    assert 'name="phone"' in resp.text
    assert "Seu número de WhatsApp" in resp.text


def test_starting_pairing_saves_the_phone_number(client):
    resp = client.post("/onboarding/whatsapp/start", data={"phone": "+55 11 99999-8888"})
    assert resp.status_code == 200

    with Session(get_engine()) as db:
        user = db.get(User, client.user.id)
        assert user.phone == "+55 11 99999-8888"


def test_set_timezone_persists_and_advances_to_done(client):
    resp = client.post("/onboarding/timezone", data={"timezone_name": "Europe/Lisbon"})
    assert resp.status_code == 200
    assert "Tudo pronto" in resp.text

    with Session(get_engine()) as db:
        user = db.get(User, client.user.id)
        assert user.timezone == "Europe/Lisbon"


def test_invalid_timezone_shows_error_and_stays_on_step_3(client):
    resp = client.post("/onboarding/timezone", data={"timezone_name": "", "custom_timezone": "Not/AZone"})
    assert resp.status_code == 200
    assert "Timezone inválida" in resp.text

    with Session(get_engine()) as db:
        user = db.get(User, client.user.id)
        assert user.timezone is None


def test_finish_marks_completed_and_unblocks_the_rest_of_the_app(client):
    resp = client.post("/onboarding/finish", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"

    with Session(get_engine()) as db:
        user = db.get(User, client.user.id)
        assert user.onboarding_completed_at is not None

    # Agora navega livremente sem ser redirecionado de volta.
    assert client.get("/").status_code == 200
    assert client.get("/agendamentos").status_code == 200
    assert client.get("/onboarding", follow_redirects=False).status_code == 303  # não mostra o wizard de novo


def test_api_and_htmx_partials_are_never_redirected_while_onboarding_pending(client):
    """O gate de onboarding só se aplica a páginas GET 'de humano' — API REST
    e parciais htmx continuam respondendo normalmente (Parte 25: onboarding
    orienta, nunca bloqueia)."""
    assert client.get("/api/schedules").status_code == 200
    assert client.get("/ui/dashboard/summary").status_code == 200


# --- usuário novo: a sessão só existe no banco do app, não no WAHA ---------- #
def test_opening_onboarding_creates_the_missing_waha_session(client):
    """Regressão do "WAHA respondeu 404 ... Session not found" que usuários
    novos viam: a sessão `u_<hex>` nascia só no banco e o WAHA só a criava se a
    pessoa clicasse em "Iniciar pareamento"."""
    client.waha.session_exists = False
    resp = client.get("/onboarding")
    assert resp.status_code == 200
    assert len(client.waha.created) == 1
    assert "Session not found" not in resp.text
    assert "WAHA respondeu 404" not in resp.text


def test_polling_the_whatsapp_step_does_not_create_the_session_twice(client):
    client.waha.session_exists = False
    client.get("/onboarding")
    client.get("/ui/onboarding/whatsapp")
    client.get("/ui/onboarding/whatsapp")
    assert len(client.waha.created) == 1


def test_qr_image_only_appears_once_waha_has_a_qr(client):
    client.waha.status = "STARTING"
    starting = client.get("/ui/onboarding/whatsapp").text
    assert 'alt="QR code"' not in starting
    assert "Preparando o QR" in starting

    client.waha.status = "SCAN_QR_CODE"
    ready = client.get("/ui/onboarding/whatsapp").text
    assert 'alt="QR code"' in ready


def test_start_pairing_works_without_a_phone_number(client):
    client.waha.status = "SCAN_QR_CODE"
    assert 'name="phone"' in client.get("/ui/onboarding/whatsapp").text
    assert "required" not in client.get("/ui/onboarding/whatsapp").text.split('name="phone"')[1].split(">")[0]
    resp = client.post("/onboarding/whatsapp/start", data={"phone": ""})
    assert resp.status_code == 200
    assert client.waha.restart_calls == 1


def test_start_pairing_shows_the_waha_error_instead_of_swallowing_it(client):
    from whatsapp_scheduler.waha import WahaError

    client.waha.status = "SCAN_QR_CODE"
    client.waha.restart_error = WahaError("WAHA respondeu 422 em POST /api/sessions: OnlyDefaultSessionIsAllowed", status_code=422)
    resp = client.post("/onboarding/whatsapp/start", data={"phone": "+55 11 99999-8888"})
    assert resp.status_code == 200
    assert "OnlyDefaultSessionIsAllowed" in resp.text


def test_passive_status_polling_never_creates_sessions(client):
    """Sidebar/dashboard consultam a cada poucos segundos: não podem sair
    criando Chromium para quem nem está conectando."""
    client.waha.session_exists = False
    client.get("/ui/sidebar-status")
    client.get("/ui/dashboard/summary")
    assert client.waha.created == []


def test_failed_session_offers_a_way_to_generate_a_new_qr(client):
    """Servidor sobrecarregado: o WEBJS pode estourar o tempo de subida e a
    sessão ir pra FAILED. A pessoa não pode ficar olhando um quadrado vazio."""
    client.waha.status = "FAILED"
    html = client.get("/ui/onboarding/whatsapp").text
    assert 'alt="QR code"' not in html
    assert "Não foi possível gerar o QR" in html
    assert "Gerar novo QR" in html

    resp = client.post("/onboarding/whatsapp/start", data={"phone": ""})
    assert resp.status_code == 200
    assert client.waha.restart_calls == 1


def _qr_img_tag(html: str) -> str:
    import re

    match = re.search(r"<img[^>]*alt=\"QR code\"[^>]*>", html)
    assert match, "QR <img> não encontrado"
    return match.group(0)


def test_qr_image_is_preserved_across_the_periodic_refresh(client):
    """Regressão: o passo se re-renderiza a cada 3s e recriava o <img> com um
    ?ts= novo, então o QR sumia e reaparecia o tempo todo. Precisa de id +
    hx-preserve (o htmx mantém o elemento) e de data-qr-src (o timer de
    base.html renova a imagem sem recriar o elemento)."""
    client.waha.status = "SCAN_QR_CODE"
    img = _qr_img_tag(client.get("/ui/onboarding/whatsapp").text)
    assert 'id="onb-qr"' in img
    assert 'hx-preserve="true"' in img
    assert 'data-qr-src="/ui/whatsapps/' in img


def test_qr_image_has_no_src_in_the_html_so_polls_do_not_redownload_it(client):
    """O htmx baixa qualquer <img> com src da resposta antes de descartá-lo em
    favor do preservado: com src, cada poll (3s, por pessoa) custava uma
    chamada ao WAHA. O carregamento é feito por loadNewQrImages() em base.html."""
    client.waha.status = "SCAN_QR_CODE"
    img = _qr_img_tag(client.get("/ui/onboarding/whatsapp").text)
    assert " src=" not in img


# --- botão e QR piscando na tela de primeiros passos -------------------------- #
def _step_sig(html: str) -> str:
    import re

    match = re.search(r'hx-get="/ui/onboarding/whatsapp\?sig=([0-9a-f]+)"', html)
    assert match, "assinatura (sig) não encontrada no contêiner do passo"
    return match.group(1)


def test_periodic_poll_returns_204_when_nothing_changed(client):
    """Regressão: o passo era recriado a cada 3s (botão e QR piscavam). Com a assinatura do que a
    tela já mostra, o servidor responde 204 e o htmx não troca nada."""
    client.waha.status = "SCAN_QR_CODE"
    sig = _step_sig(client.get("/ui/onboarding/whatsapp").text)
    assert client.get("/ui/onboarding/whatsapp", params={"sig": sig}).status_code == 204
    assert client.get("/ui/onboarding/whatsapp", params={"sig": sig}).status_code == 204  # de novo: continua igual


def test_poll_renders_again_as_soon_as_the_state_changes(client):
    client.waha.status = "SCAN_QR_CODE"
    sig = _step_sig(client.get("/ui/onboarding/whatsapp").text)
    client.waha.status = "WORKING"
    changed = client.get("/ui/onboarding/whatsapp", params={"sig": sig})
    assert changed.status_code == 200 and "WhatsApp conectado" in changed.text
    assert _step_sig(changed.text) != sig                                   # a nova assinatura acompanha o novo estado
    assert client.get("/ui/onboarding/whatsapp", params={"sig": "obsoleto"}).status_code == 200
    assert client.get("/ui/onboarding/whatsapp").status_code == 200         # sem sig (primeira carga) sempre renderiza


def test_polling_container_is_marked_so_it_does_not_flip_the_buttons_label(client):
    """O contêiner de polling ganha `htmx-request` a cada consulta; o CSS do "gerando…" tem que ignorá-lo."""
    from pathlib import Path

    client.waha.status = "SCAN_QR_CODE"
    import re

    html = client.get("/ui/onboarding/whatsapp").text
    wrapper = re.search(r'<div id="onboarding-whatsapp-step"[^>]*>', html).group(0)
    assert "data-poll" in wrapper and 'hx-swap="outerHTML"' in wrapper
    base = (Path(__file__).parent.parent / "whatsapp_scheduler/web/templates/base.html").read_text(encoding="utf-8")
    assert ".htmx-request:not([data-poll]) .hide-loading" in base
    assert ".htmx-request:not([data-poll]) .spin" in base
    assert ".htmx-request .hide-loading" not in base.replace(".htmx-request:not([data-poll]) .hide-loading", "")


def test_new_qr_is_decoded_before_it_replaces_the_old_one_and_identical_qr_is_skipped(client):
    from pathlib import Path

    base = (Path(__file__).parent.parent / "whatsapp_scheduler/web/templates/base.html").read_text(encoding="utf-8")
    load_qr = base.split("function loadQr(img)")[1].split("function refreshQrImages")[0]
    assert "pre.decode" in load_qr and "img.getAttribute('src')" in load_qr
