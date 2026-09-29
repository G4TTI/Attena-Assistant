import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.conftest import FakeWaha, db_locations_containing, register_and_login, whatsapp_session_id
from whatsapp_scheduler import chatsvc, privacy
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import Schedule

OVERVIEW = [
    {
        "id": "5511999998888@c.us",
        "name": "Fulano",
        "picture": None,
        "lastMessage": {"timestamp": 1_760_000_000, "fromMe": False, "body": "oi tudo bem?"},
    },
    {
        "id": "12036300000000@g.us",
        "name": "Grupo X",
        "lastMessage": {"timestamp": 1_760_000_500, "fromMe": True, "body": "", "hasMedia": True, "type": "image"},
    },
]

MESSAGES = [
    {"id": "AAA", "timestamp": 1_760_000_000, "fromMe": False, "body": "oi", "type": "chat"},
    {"id": "BBB", "timestamp": 1_760_000_050, "fromMe": True, "body": "ola", "type": "chat"},
    {"id": "CCC", "timestamp": 1_760_000_100, "fromMe": False, "body": "", "type": "image", "hasMedia": True},
]


@pytest.fixture(autouse=True)
def _reset_chat_cache():
    chatsvc._chat_cache.clear()
    chatsvc._history_cache.clear()
    yield
    chatsvc._chat_cache.clear()
    chatsvc._history_cache.clear()


@pytest.fixture
def client():
    waha = FakeWaha()
    waha.chats = OVERVIEW
    waha.messages = MESSAGES
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        user = register_and_login(c)
        c.user = user
        yield c


async def test_list_chats_normalizes_and_sorts(test_user):
    waha = FakeWaha()
    waha.chats = OVERVIEW
    chats = await chatsvc.list_chats(waha, test_user.waha_session, "America/Sao_Paulo", force=True)
    assert [c["id"] for c in chats] == ["12036300000000@g.us", "5511999998888@c.us"]  # mais recente 1º
    grp = chats[0]
    assert grp["is_group"] is True
    assert grp["last_preview"] == "[imagem]"
    assert grp["last_from_me"] is True
    assert chats[1]["last_preview"] == "oi tudo bem?"


async def test_get_history_caches_only_in_memory(test_user):
    waha = FakeWaha()
    waha.messages = MESSAGES

    first = await chatsvc.get_history(waha, test_user.id, test_user.waha_session, "5511999998888@c.us", "America/Sao_Paulo")
    assert first.from_cache is False
    assert [m["text"] for m in first.messages] == ["oi", "ola", "[imagem]"]

    waha.messages_error = RuntimeError("não deveria ser chamado")
    second = await chatsvc.get_history(waha, test_user.id, test_user.waha_session, "5511999998888@c.us", "America/Sao_Paulo")
    assert second.from_cache is True
    assert len(second.messages) == 3
    # ...e nada disso foi para o banco.
    assert db_locations_containing("ola") == []


async def test_history_cache_expires_and_is_removed(test_user, monkeypatch):
    waha = FakeWaha()
    waha.messages = MESSAGES
    await chatsvc.get_history(waha, test_user.id, test_user.waha_session, "chat@c.us", "America/Sao_Paulo")
    assert chatsvc._history_cache
    monkeypatch.setattr(chatsvc.settings, "chat_messages_cache_seconds", 0)
    assert chatsvc.purge_expired() >= 1
    assert chatsvc._history_cache == {}


async def test_get_history_falls_back_to_memory_on_error(test_user):
    from whatsapp_scheduler.waha import WahaError

    waha = FakeWaha()
    waha.messages = MESSAGES
    await chatsvc.get_history(waha, test_user.id, test_user.waha_session, "chat@c.us", "America/Sao_Paulo")

    waha.messages_error = WahaError("timeout")
    out = await chatsvc.get_history(waha, test_user.id, test_user.waha_session, "chat@c.us", "America/Sao_Paulo", force=True)
    assert out.from_cache is True
    assert out.error is not None
    assert len(out.messages) == 3


async def test_send_now_persists_nothing(test_user):
    waha = FakeWaha()
    await chatsvc.send_now(waha, test_user.id, test_user.waha_session, "5511999998888@c.us", "mensagem enviada agora")
    assert waha.sent[0]["text"] == "mensagem enviada agora"
    assert db_locations_containing("mensagem enviada agora") == []
    assert db_locations_containing("5511999998888") == []


def test_api_list_chats(client):
    sid = whatsapp_session_id(client)
    data = client.get(f"/api/whatsapp-sessions/{sid}/chats").json()
    assert {c["id"] for c in data} == {"5511999998888@c.us", "12036300000000@g.us"}


def test_api_messages(client):
    sid = whatsapp_session_id(client)
    data = client.get(f"/api/whatsapp-sessions/{sid}/chats/messages", params={"chat": "5511999998888@c.us"}).json()
    assert data["chat"] == "5511999998888@c.us"
    assert [m["text"] for m in data["messages"]] == ["oi", "ola", "[imagem]"]


def test_api_chats_404_for_unowned_session(client):
    assert client.get("/api/whatsapp-sessions/does-not-exist/chats").status_code == 404


def test_api_send(client):
    sid = whatsapp_session_id(client)
    session_name = client.get("/api/whatsapp-sessions").json()[0]["session_name"]
    r = client.post(f"/api/whatsapp-sessions/{sid}/chats/send", json={"chat": "5511999998888@c.us", "text": "oi"})
    assert r.status_code == 200
    assert client.waha.sent[0] == {"session": session_name, "chatId": "5511999998888@c.us", "text": "oi"}


def test_api_send_rejects_empty(client):
    sid = whatsapp_session_id(client)
    assert client.post(f"/api/whatsapp-sessions/{sid}/chats/send", json={"chat": "x@c.us", "text": "  "}).status_code == 422


def test_conversas_page_and_partials(client):
    sid = whatsapp_session_id(client)
    assert client.get("/conversas").status_code == 200
    assert "Fulano" in client.get(f"/ui/chats/{sid}").text
    view = client.get(f"/ui/chats/{sid}/view", params={"chat": "5511999998888@c.us"})
    assert "Fulano" in view.text
    assert "5511999998888@c.us" in view.text


def test_stale_or_foreign_whatsapp_link_opens_own_conversations(client):
    """Link velho (id que não existe nesta base) ou de outra conta: volta pras conversas do
    WhatsApp principal em vez de um JSON "WhatsApp não encontrado." — sem revelar nada."""
    own = whatsapp_session_id(client)
    r = client.get("/conversas/4a7c04e7-41c7-478f-8677-660ea32d3e0f", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/conversas"
    assert client.get("/conversas/4a7c04e7-41c7-478f-8677-660ea32d3e0f").url.path == f"/conversas/{own}"
    client.cookies.clear()
    register_and_login(client, name="B", email="b-link@example.com")
    other = client.get(f"/conversas/{own}")
    assert other.status_code == 200 and other.url.path == f"/conversas/{whatsapp_session_id(client)}"
    assert other.url.path != f"/conversas/{own}"


def test_schedule_from_chat_view(client):
    sid = whatsapp_session_id(client)
    r = client.post(
        f"/ui/chats/{sid}/schedule",
        data={
            "chat": "12036300000000@g.us",
            "text": "lembrete do grupo",
            "send_at": "2999-01-01T09:00",
            "recurrence": "",
        },
    )
    assert r.status_code == 200
    assert "Agendamento criado" in r.text

    with Session(get_engine()) as s:
        sch = s.exec(select(Schedule)).one()
    assert privacy.schedule_recipient(sch) == "12036300000000@g.us"
    assert privacy.schedule_message(sch) == "lembrete do grupo"
    assert db_locations_containing("lembrete do grupo") == []
    assert db_locations_containing("12036300000000") == []
