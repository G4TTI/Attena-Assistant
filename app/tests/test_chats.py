import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.conftest import FakeWaha, register_and_login, whatsapp_session_id
from whatsapp_scheduler import chatsvc
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import CachedMessage, Schedule

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
    chatsvc._chat_cache.update(at=0.0, data=[])
    yield
    chatsvc._chat_cache.update(at=0.0, data=[])


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
    chats = await chatsvc.list_chats(waha, test_user.waha_session, force=True)
    assert [c["id"] for c in chats] == ["12036300000000@g.us", "5511999998888@c.us"]  # mais recente 1º
    grp = chats[0]
    assert grp["is_group"] is True
    assert grp["last_preview"] == "[imagem]"
    assert grp["last_from_me"] is True
    assert chats[1]["last_preview"] == "oi tudo bem?"


async def test_get_history_caches(db: Session, test_user):
    waha = FakeWaha()
    waha.messages = MESSAGES

    first = await chatsvc.get_history(db, waha, test_user.id, test_user.waha_session, "5511999998888@c.us")
    assert first.from_cache is False
    assert [m["text"] for m in first.messages] == ["oi", "ola", "[imagem]"]

    waha.messages_error = RuntimeError("não deveria ser chamado")
    second = await chatsvc.get_history(db, waha, test_user.id, test_user.waha_session, "5511999998888@c.us")
    assert second.from_cache is True
    assert len(second.messages) == 3


async def test_get_history_falls_back_to_cache_on_error(db: Session, test_user):
    from whatsapp_scheduler.waha import WahaError

    waha = FakeWaha()
    waha.messages = MESSAGES
    await chatsvc.get_history(db, waha, test_user.id, test_user.waha_session, "chat@c.us")

    waha.messages_error = WahaError("timeout")
    out = await chatsvc.get_history(db, waha, test_user.id, test_user.waha_session, "chat@c.us", force=True)
    assert out.from_cache is True
    assert out.error is not None
    assert len(out.messages) == 3


async def test_send_now_records_outgoing_message(db: Session, test_user):
    waha = FakeWaha()
    await chatsvc.send_now(db, waha, test_user.id, test_user.waha_session, "5511999998888@c.us", "mensagem enviada")
    rows = db.exec(select(CachedMessage).where(CachedMessage.chat_id == "5511999998888@c.us")).all()
    assert len(rows) == 1
    assert rows[0].from_me is True
    assert rows[0].body == "mensagem enviada"
    assert waha.sent[0]["text"] == "mensagem enviada"


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
    assert sch.chat_id == "12036300000000@g.us"
    assert sch.text == "lembrete do grupo"
