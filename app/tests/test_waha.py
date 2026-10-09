import httpx
import pytest
import respx

from whatsapp_scheduler.waha import WahaClient, WahaError, extract_message_id

BASE = "http://waha.test"


@pytest.fixture
async def waha():
    client = WahaClient(BASE, "k", timeout=5)
    yield client
    await client.aclose()


@respx.mock
async def test_send_text_ok(waha):
    route = respx.post(f"{BASE}/api/sendText").mock(
        return_value=httpx.Response(201, json={"id": {"_serialized": "true_123@c.us_ABC"}})
    )
    out = await waha.send_text("default", "123@c.us", "oi")
    assert route.called
    sent = route.calls.last.request
    assert b'"chatId": "123@c.us"' in sent.content or b'"chatId":"123@c.us"' in sent.content
    assert extract_message_id(out) == "true_123@c.us_ABC"


@respx.mock
async def test_error_status_becomes_waha_error(waha):
    respx.get(f"{BASE}/api/sessions/default").mock(return_value=httpx.Response(500, text="kaboom"))
    with pytest.raises(WahaError):
        await waha.get_session_status("default")


@respx.mock
async def test_connection_error_becomes_waha_error(waha):
    respx.post(f"{BASE}/api/sendText").mock(side_effect=httpx.ConnectError("no route"))
    with pytest.raises(WahaError):
        await waha.send_text("default", "1@c.us", "x")


@respx.mock
async def test_restart_session_uses_restart_endpoint_when_available(waha):
    route = respx.post(f"{BASE}/api/sessions/default/restart").mock(
        return_value=httpx.Response(200, json={"name": "default", "status": "STARTING"})
    )
    out = await waha.restart_session("default")
    assert route.called
    assert out["status"] == "STARTING"


@respx.mock
async def test_restart_session_falls_back_to_stop_then_start(waha):
    respx.post(f"{BASE}/api/sessions/default/restart").mock(return_value=httpx.Response(404))
    stop = respx.post(f"{BASE}/api/sessions/default/stop").mock(return_value=httpx.Response(200, json={}))
    start = respx.post(f"{BASE}/api/sessions/default/start").mock(
        return_value=httpx.Response(200, json={"name": "default", "status": "STARTING"})
    )
    out = await waha.restart_session("default")
    assert stop.called
    assert start.called
    assert out["status"] == "STARTING"


@respx.mock
async def test_restart_session_recovers_even_if_stop_fails(waha):
    """Sessão que nunca existiu: /stop falha (404), mas o /start ainda deve rodar."""
    respx.post(f"{BASE}/api/sessions/default/restart").mock(return_value=httpx.Response(404))
    respx.post(f"{BASE}/api/sessions/default/stop").mock(return_value=httpx.Response(404))
    start = respx.post(f"{BASE}/api/sessions/default/start").mock(
        return_value=httpx.Response(200, json={"name": "default", "status": "STARTING"})
    )
    out = await waha.restart_session("default")
    assert start.called
    assert out["status"] == "STARTING"


@respx.mock
async def test_error_carries_http_status_code(waha):
    respx.get(f"{BASE}/api/sessions/u_x").mock(return_value=httpx.Response(404, json={"message": "Session not found"}))
    with pytest.raises(WahaError) as exc_info:
        await waha.get_session_status("u_x")
    assert exc_info.value.status_code == 404


@respx.mock
async def test_ensure_session_creates_it_when_missing(waha):
    respx.get(f"{BASE}/api/sessions/u_new").mock(return_value=httpx.Response(404))
    create = respx.post(f"{BASE}/api/sessions").mock(
        return_value=httpx.Response(201, json={"name": "u_new", "status": "STARTING"})
    )
    out = await waha.ensure_session("u_new")
    assert create.called
    assert b'"name": "u_new"' in create.calls.last.request.content or b'"name":"u_new"' in create.calls.last.request.content
    assert out["status"] == "STARTING"


@respx.mock
async def test_ensure_session_leaves_an_existing_session_alone(waha):
    respx.get(f"{BASE}/api/sessions/u_ok").mock(
        return_value=httpx.Response(200, json={"name": "u_ok", "status": "SCAN_QR_CODE"})
    )
    create = respx.post(f"{BASE}/api/sessions").mock(return_value=httpx.Response(201, json={}))
    restart = respx.post(f"{BASE}/api/sessions/u_ok/restart").mock(return_value=httpx.Response(200, json={}))
    out = await waha.ensure_session("u_ok")
    assert out["status"] == "SCAN_QR_CODE"
    assert not create.called
    assert not restart.called


@respx.mock
async def test_ensure_session_does_not_restart_failed_sessions(waha):
    """FAILED fica com o usuário: reiniciar sozinho a cada poll viraria loop."""
    respx.get(f"{BASE}/api/sessions/u_f").mock(return_value=httpx.Response(200, json={"name": "u_f", "status": "FAILED"}))
    restart = respx.post(f"{BASE}/api/sessions/u_f/restart").mock(return_value=httpx.Response(200, json={}))
    start = respx.post(f"{BASE}/api/sessions/u_f/start").mock(return_value=httpx.Response(200, json={}))
    out = await waha.ensure_session("u_f")
    assert out["status"] == "FAILED"
    assert not restart.called and not start.called


@respx.mock
async def test_ensure_session_starts_a_stopped_session(waha):
    respx.get(f"{BASE}/api/sessions/u_s").mock(return_value=httpx.Response(200, json={"name": "u_s", "status": "STOPPED"}))
    start = respx.post(f"{BASE}/api/sessions/u_s/start").mock(
        return_value=httpx.Response(201, json={"name": "u_s", "status": "STARTING"})
    )
    out = await waha.ensure_session("u_s")
    assert start.called
    assert out["status"] == "STARTING"


@respx.mock
async def test_ensure_session_propagates_non_404_errors(waha):
    """WAHA fora do ar / chave errada não deve virar 'vou criar a sessão'."""
    respx.get(f"{BASE}/api/sessions/u_e").mock(return_value=httpx.Response(401, text="unauthorized"))
    create = respx.post(f"{BASE}/api/sessions").mock(return_value=httpx.Response(201, json={}))
    with pytest.raises(WahaError) as exc_info:
        await waha.ensure_session("u_e")
    assert exc_info.value.status_code == 401
    assert not create.called


@respx.mock
async def test_ensure_session_concurrent_calls_create_only_once(waha):
    import asyncio

    state = {"exists": False}

    def _get(request):
        if state["exists"]:
            return httpx.Response(200, json={"name": "u_c", "status": "STARTING"})
        return httpx.Response(404)

    def _create(request):
        state["exists"] = True
        return httpx.Response(201, json={"name": "u_c", "status": "STARTING"})

    respx.get(f"{BASE}/api/sessions/u_c").mock(side_effect=_get)
    create = respx.post(f"{BASE}/api/sessions").mock(side_effect=_create)
    await asyncio.gather(*(waha.ensure_session("u_c") for _ in range(5)))
    assert create.call_count == 1


@respx.mock
async def test_create_session_enables_noweb_store_so_chats_work_on_that_engine(waha):
    import json

    create = respx.post(f"{BASE}/api/sessions").mock(return_value=httpx.Response(201, json={"name": "u_n"}))
    await waha.create_session("u_n")
    body = json.loads(create.calls.last.request.content)
    assert body["name"] == "u_n" and body["start"] is True
    assert body["config"]["noweb"]["store"]["enabled"] is True
