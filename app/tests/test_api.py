import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeWaha, register_and_login, whatsapp_session_id
from whatsapp_scheduler.main import app
from whatsapp_scheduler.waha import WahaError

FUTURE = "2999-01-01T09:00:00"


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        user = register_and_login(c)
        c.user = user
        yield c


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_create_and_list(client):
    resp = client.post(
        "/api/schedules",
        json={"recipient": "+55 11 99999-8888", "text": "oi", "send_at": FUTURE, "recurrence": "daily 09:00"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["chat_id"] == "5511999998888@c.us"
    assert body["recurrence"] == "0 9 * * *"
    assert body["next_dispatch"]["status"] == "pending"

    listed = client.get("/api/schedules").json()
    assert [s["id"] for s in listed] == [body["id"]]


def test_create_rejects_bad_recipient(client):
    resp = client.post("/api/schedules", json={"recipient": "abc", "text": "oi", "send_at": FUTURE})
    assert resp.status_code == 422


def test_create_rejects_bad_recurrence(client):
    resp = client.post(
        "/api/schedules",
        json={"recipient": "5511999998888", "text": "oi", "send_at": FUTURE, "recurrence": "todo dia"},
    )
    assert resp.status_code == 422


def test_get_missing_is_404(client):
    assert client.get("/api/schedules/nope").status_code == 404


def test_delete_cancels(client):
    sid = client.post(
        "/api/schedules", json={"recipient": "5511999998888", "text": "oi", "send_at": FUTURE}
    ).json()["id"]

    assert client.delete(f"/api/schedules/{sid}").status_code == 200

    got = client.get(f"/api/schedules/{sid}").json()
    assert got["enabled"] is False
    assert all(d["status"] == "canceled" for d in got["dispatches"])

    assert client.delete(f"/api/schedules/{sid}").status_code == 404


def test_run_now_creates_immediate_dispatch(client):
    sid = client.post(
        "/api/schedules", json={"recipient": "5511999998888", "text": "oi", "send_at": FUTURE}
    ).json()["id"]

    resp = client.post(f"/api/schedules/{sid}/run-now")
    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"


def test_session_status_and_qr(client):
    sid = whatsapp_session_id(client)
    assert client.get(f"/api/whatsapp-sessions/{sid}").json()["status"] == "WORKING"
    qr = client.get(f"/api/whatsapp-sessions/{sid}/qr")
    assert qr.status_code == 200
    assert qr.content == b"PNGDATA"


def test_session_start_restarts_a_failed_session(client):
    sid = whatsapp_session_id(client)
    client.waha.status = "FAILED"

    resp = client.post(f"/api/whatsapp-sessions/{sid}/start")
    assert resp.status_code == 202
    assert client.waha.restart_calls == 1
    # o status "no lado do WAHA" já reflete a tentativa de reconexão
    assert client.get(f"/api/whatsapp-sessions/{sid}").json()["status"] == "STARTING"


def test_session_status_and_start_404_for_unowned_session(client):
    assert client.get("/api/whatsapp-sessions/does-not-exist").status_code == 404
    assert client.post("/api/whatsapp-sessions/does-not-exist/start").status_code == 404


def test_ui_whatsapp_start_renders_updated_list_with_feedback(client):
    sid = whatsapp_session_id(client)
    client.waha.status = "FAILED"

    resp = client.post(f"/whatsapps/{sid}/start")
    assert resp.status_code == 200
    assert client.waha.restart_calls == 1
    # depois do restart a lista já deve mostrar o novo estado (pareando), não mais desconectado
    assert "conectando" in resp.text.lower()


def test_ui_whatsapp_start_shows_error_when_waha_unreachable(client):
    sid = whatsapp_session_id(client)
    client.waha.restart_error = WahaError("conexão recusada")

    resp = client.post(f"/whatsapps/{sid}/start")
    assert resp.status_code == 200
    assert "conexão recusada" in resp.text


def test_agendamentos_page_renders(client):
    resp = client.get("/agendamentos")
    assert resp.status_code == 200
    assert "Agendamentos" in resp.text
    assert "Conversas" in resp.text  # barra lateral


# --------------------------------------------------------------------------- #
# Dashboard — agora é "/"; Agendamentos foi para "/agendamentos".
# --------------------------------------------------------------------------- #
def test_dashboard_is_now_the_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Olá" in resp.text
    assert "Eventos hoje" in resp.text
    assert "Agendamentos" in resp.text  # ainda linkado na sidebar


def test_dashboard_summary_partial_renders_standalone(client):
    resp = client.get("/ui/dashboard/summary")
    assert resp.status_code == 200
    assert 'id="dashboard-summary"' in resp.text


def test_dashboard_does_not_auto_poll_inside_modal_trigger_scope(client):
    """Regressão: a Dashboard já teve um `hx-trigger="every Ns"` envolvendo
    botões que abrem modal (hx-target="#modal-root") — o poll automático
    corrompia o `#modal-root` compartilhado (usado por toda ação de
    evento/automação no app) quando disparava perto de um clique nesses
    botões. Substituído por um botão "Atualizar" manual (mesmo padrão do
    `_table.html`). Não pode voltar a ter polling automático na página."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'hx-trigger="every 30s"' not in resp.text
    assert "Atualizar" in resp.text  # botão manual no lugar do poll
