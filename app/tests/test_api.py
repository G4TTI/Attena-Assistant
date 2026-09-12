import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeWaha
from whatsapp_scheduler.main import app
from whatsapp_scheduler.waha import WahaError

FUTURE = "2999-01-01T09:00:00"


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
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
    assert client.get("/api/session").json()["status"] == "WORKING"
    qr = client.get("/api/session/qr")
    assert qr.status_code == 200
    assert qr.content == b"PNGDATA"


def test_session_start_restarts_a_failed_session(client):
    client.waha.status = "FAILED"

    resp = client.post("/api/session/start")
    assert resp.status_code == 202
    assert client.waha.restart_calls == 1
    # o status "no lado do WAHA" já reflete a tentativa de reconexão
    assert client.get("/api/session").json()["status"] == "STARTING"


def test_ui_session_start_renders_updated_panel_with_feedback(client):
    client.waha.status = "FAILED"

    resp = client.post("/ui/session/start")
    assert resp.status_code == 200
    assert client.waha.restart_calls == 1
    # depois do restart o painel já deve mostrar o novo estado, não a tela travada
    assert "FAILED" not in resp.text
    assert "starting" in resp.text.lower()


def test_ui_session_start_shows_error_when_waha_unreachable(client):
    client.waha.restart_error = WahaError("conexão recusada")

    resp = client.post("/ui/session/start")
    assert resp.status_code == 200
    assert "conexão recusada" in resp.text


def test_index_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Agendamentos" in resp.text
    assert "Conversas" in resp.text  # barra lateral
