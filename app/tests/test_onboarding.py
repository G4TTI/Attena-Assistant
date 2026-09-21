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
