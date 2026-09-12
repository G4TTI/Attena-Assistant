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
