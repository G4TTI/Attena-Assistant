"""Ciclo de vida do conteúdo privado (v1.4):

- mensagem programada nunca em texto puro no banco (varredura SQL crua);
- conteúdo e destinatário somem ao enviar, cancelar, falhar de vez ou ser ignorado;
- recorrência ativa mantém o conteúdo até ser cancelada;
- mensagens recebidas, histórico e contatos do WhatsApp nunca são gravados;
- job privacy_cleanup: sobras, prazos de retenção, tokens obsoletos, sessões WAHA.
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from tests.conftest import (
    FakeWaha,
    db_locations_containing,
    make_schedule,
    register_and_login,
    text_of,
    whatsapp_session_id,
)
from whatsapp_scheduler import calendar_service, crypto, privacy, retention, timing
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import (
    AuditEventType,
    AutomationMessage,
    CalendarConnection,
    CalendarConnectionStatus,
    Dispatch,
    DispatchStatus,
    Event,
    EventSource,
    LoginAuditEvent,
    Schedule,
    ScheduleGroup,
    User,
    WhatsAppSession,
)
from whatsapp_scheduler.scheduler import SchedulerService, dispatch_due, materialize_due
from whatsapp_scheduler.service import cancel_group, create_sequence

TZ = "America/Sao_Paulo"
JOAO = "5514991110001@c.us"
SECRET = "Olá João, sua consulta é amanhã às 15h."


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        c.user = register_and_login(c)
        c.sid = whatsapp_session_id(c)
        yield c


def _session_name(client) -> str:
    with Session(get_engine()) as db:
        return db.get(WhatsAppSession, client.sid).session_name


def _create(client, *, messages=(SECRET,), start=None, recurrence=None, max_attempts=3) -> str:
    with Session(get_engine()) as db:
        group, _ = create_sequence(
            db, user_id=client.user.id, session=_session_name(client), recipient=JOAO, recipient_name="João da Silva",
            messages=list(messages), start=start or datetime(2999, 1, 1, 9, 0), timezone=TZ,
            recurrence=recurrence, max_attempts=max_attempts,
        )
        return group.id


def _assert_no_trace(*needles: str) -> None:
    for needle in needles:
        assert db_locations_containing(needle) == [], needle


def _schedules(group_id: str) -> list[Schedule]:
    with Session(get_engine()) as db:
        return list(db.exec(select(Schedule).where(col(Schedule.group_id) == group_id).order_by(col(Schedule.position))).all())


# --------------------------------------------------------------------------- #
# Cifrado no banco
# --------------------------------------------------------------------------- #
def test_scheduled_message_is_encrypted_in_the_database(client):
    r = client.post("/ui/schedules", data={
        "recipients": ["+55 14 99111-0001"], "recipient_names": ["João da Silva"], "messages": [SECRET],
        "whatsapp_session_id": client.sid, "send_date": "2999-09-20", "send_time": "18:00",
    })
    assert "Agendamento criado." in r.text
    # O banco sozinho não revela conteúdo, telefone nem nome do contato…
    _assert_no_trace(SECRET, "consulta é amanhã", "991110001", "João da Silva")
    (group_id,) = {s.group_id for s in _schedules_all()}
    (schedule,) = _schedules(group_id)
    assert schedule.message_ciphertext and schedule.encryption_nonce and schedule.encryption_key_version == 1
    assert schedule.recipient_phone_hash and len(schedule.recipient_phone_hash) == 64
    # …mas o dono autenticado vê a própria mensagem.
    assert SECRET in client.get(f"/ui/schedules/{group_id}").text


def _schedules_all() -> list[Schedule]:
    with Session(get_engine()) as db:
        return list(db.exec(select(Schedule)).all())


def test_other_user_cannot_see_the_message(client):
    group_id = _create(client)
    client.cookies.clear()
    register_and_login(client, name="B", email="b-priv@example.com")
    assert client.get(f"/ui/schedules/{group_id}").status_code == 404
    assert SECRET not in client.get("/ui/schedules").text


# --------------------------------------------------------------------------- #
# Expurgo nos estados finais
# --------------------------------------------------------------------------- #
def test_content_and_recipient_are_removed_after_sending(client):
    now_local = timing.to_local(utcnow(), TZ)
    group_id = _create(client, messages=["um segredo", "dois segredo"], start=now_local - timedelta(minutes=1))
    asyncio.run(SchedulerService(client.waha).run_once())
    assert [m["text"] for m in client.waha.sent] == ["um segredo", "dois segredo"]
    for schedule in _schedules(group_id):
        assert schedule.message_ciphertext is None and schedule.encryption_nonce is None
        assert schedule.recipient_phone_encrypted is None and schedule.content_purged_at is not None
        assert schedule.enabled is False
    with Session(get_engine()) as db:
        assert db.get(ScheduleGroup, group_id).recipient_encrypted is None
        dispatches = db.exec(select(Dispatch)).all()
        assert {d.status for d in dispatches} == {DispatchStatus.sent}
        assert all(d.waha_message_hash and "5514" not in d.waha_message_hash for d in dispatches)
    _assert_no_trace("segredo", "991110001", "João da Silva")
    # O histórico operacional continua (métricas sem conteúdo)
    assert "Enviado" in client.get("/ui/schedules").text


def test_content_is_removed_after_cancel(client):
    group_id = _create(client)
    assert client.post(f"/ui/schedules/{group_id}/cancel").status_code == 200
    for schedule in _schedules(group_id):
        assert schedule.message_ciphertext is None and schedule.recipient_phone_encrypted is None
    _assert_no_trace(SECRET, "991110001", "João da Silva")
    detail = client.get(f"/ui/schedules/{group_id}").text
    assert "Conteúdo apagado no cancelamento" in detail and SECRET not in detail


def test_single_message_cancel_from_the_chat_purges_only_that_message(client):
    group_id = _create(client, messages=["primeira", "segunda"])
    first, second = _schedules(group_id)
    r = client.post(f"/ui/chats/{client.sid}/scheduled/{first.id}/cancel", data={"chat": JOAO})
    assert r.status_code == 200
    first, second = _schedules(group_id)
    assert text_of(first) is None and text_of(second) == "segunda"
    with Session(get_engine()) as db:
        assert db.get(ScheduleGroup, group_id).recipient_encrypted is not None  # ainda há o que enviar


def test_failed_final_removes_content_but_retry_keeps_it(client):
    from whatsapp_scheduler.waha import WahaError

    now_local = timing.to_local(utcnow(), TZ)
    retry_group = _create(client, messages=["tenta de novo"], start=now_local - timedelta(minutes=1), max_attempts=3)
    client.waha.send_error = WahaError("WAHA respondeu 500: {\"message\": \"tenta de novo 5514991110001@c.us\"}", status_code=500)
    asyncio.run(dispatch_due_after_materialize(client.waha))
    (schedule,) = _schedules(retry_group)
    assert text_of(schedule) == "tenta de novo"  # ainda pode sair (retry)
    with Session(get_engine()) as db:
        (dispatch,) = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule.id)).all()
        assert dispatch.failure_code == "waha_server_error"
        assert "5514991110001" not in (dispatch.last_error or "") and "tenta de novo" not in (dispatch.last_error or "")

    final_group = _create(client, messages=["falha final"], start=now_local - timedelta(minutes=1), max_attempts=1)
    asyncio.run(dispatch_due_after_materialize(client.waha))
    (schedule,) = _schedules(final_group)
    assert schedule.message_ciphertext is None and schedule.content_purged_at is not None
    _assert_no_trace("falha final")


async def dispatch_due_after_materialize(waha) -> None:
    await asyncio.to_thread(materialize_due)
    await dispatch_due(waha)


def test_recurring_message_keeps_content_until_the_recurrence_ends(client):
    now_local = timing.to_local(utcnow(), TZ)
    group_id = _create(client, messages=["todo dia"], start=now_local - timedelta(minutes=1), recurrence="daily 09:00")
    asyncio.run(SchedulerService(client.waha).run_once())
    assert [m["text"] for m in client.waha.sent] == ["todo dia"]
    (schedule,) = _schedules(group_id)
    assert schedule.enabled is True and text_of(schedule) == "todo dia"  # a próxima ocorrência ainda precisa
    with Session(get_engine()) as db:
        assert cancel_group(db, group_id, user_id=client.user.id)
    (schedule,) = _schedules(group_id)
    assert schedule.message_ciphertext is None
    _assert_no_trace("todo dia")


def test_removing_an_automation_purges_its_messages(client):
    with Session(get_engine()) as db:
        event = Event(user_id=client.user.id, source=EventSource.internal, title="Aula",
                      start_utc=datetime(2999, 1, 2, 12, 0), end_utc=datetime(2999, 1, 2, 13, 0), timezone=TZ)
        db.add(event)
        db.commit()
        automation = calendar_service.create_event_automation(
            db, event_id=event.id, user_id=client.user.id, waha_session=_session_name(client),
            recipients=["+55 14 99111-0001"], messages=["texto da automação"], offset_amount=1,
            offset_unit="hours", offset_direction="before",
        )
        automation_id = automation.id
    _assert_no_trace("texto da automação")
    with Session(get_engine()) as db:
        (message,) = db.exec(select(AutomationMessage).where(col(AutomationMessage.automation_id) == automation_id)).all()
        assert text_of(message) == "texto da automação"
        assert calendar_service.remove_event_automation(db, automation_id, client.user.id)
    with Session(get_engine()) as db:
        (message,) = db.exec(select(AutomationMessage).where(col(AutomationMessage.automation_id) == automation_id)).all()
        assert message.message_ciphertext is None and message.content_purged_at is not None
        assert all(s.message_ciphertext is None for s in db.exec(select(Schedule)).all())


def test_api_never_returns_purged_or_foreign_content(client):
    r = client.post("/api/schedules", json={"recipient": "+55 14 99111-0001", "text": SECRET, "send_at": "2999-01-01T09:00"})
    assert r.status_code == 201 and r.json()["text"] == SECRET
    schedule_id = r.json()["id"]
    assert "message_ciphertext" not in r.text and "recipient_phone_hash" not in r.text
    assert client.delete(f"/api/schedules/{schedule_id}").status_code == 200
    data = client.get(f"/api/schedules/{schedule_id}").json()
    assert data["text"] is None and data["chat_id"] is None and data["content_removed"] is True


def test_suspended_account_messages_are_not_sent(client):
    now_local = timing.to_local(utcnow(), TZ)
    group_id = _create(client, messages=["não deve sair"], start=now_local - timedelta(minutes=1))
    with Session(get_engine()) as db:
        user = db.get(User, client.user.id)
        user.is_active = False
        db.add(user)
        db.commit()
    asyncio.run(SchedulerService(client.waha).run_once())
    assert client.waha.sent == []
    with Session(get_engine()) as db:
        (dispatch,) = db.exec(select(Dispatch)).all()
        assert dispatch.status == DispatchStatus.skipped and dispatch.failure_code == "account_suspended"
    (schedule,) = _schedules(group_id)
    assert schedule.message_ciphertext is None


# --------------------------------------------------------------------------- #
# Conversas: só visualização
# --------------------------------------------------------------------------- #
def test_received_messages_history_and_contacts_are_never_persisted(client):
    client.waha.chats = [{"id": JOAO, "name": "Contato Secreto Silva", "picture": "https://pps.whatsapp.net/x.jpg",
                          "lastMessage": {"timestamp": 1_760_000_000, "fromMe": False, "body": "preview secreto"}}]
    client.waha.messages = [
        {"id": "false_x_1", "timestamp": 1_760_000_000, "fromMe": False, "body": "mensagem recebida confidencial", "type": "chat"},
        {"id": "false_x_2", "timestamp": 1_760_000_010, "fromMe": False, "body": "", "type": "image", "hasMedia": True},
    ]
    assert "Contato Secreto Silva" in client.get(f"/ui/chats/{client.sid}").text
    hist = client.get(f"/ui/chats/{client.sid}/messages", params={"chat": JOAO}).text
    assert "mensagem recebida confidencial" in hist and "[imagem]" in hist
    api = client.get(f"/api/whatsapp-sessions/{client.sid}/chats/messages", params={"chat": JOAO, "refresh": 1}).json()
    assert api["messages"][0]["text"] == "mensagem recebida confidencial"
    contacts = client.get("/ui/calendario/contacts", params={"whatsapp_session_id": client.sid}).text
    assert "Contato Secreto Silva" in contacts
    _assert_no_trace("confidencial", "Contato Secreto", "preview secreto", "pps.whatsapp.net", "991110001")
    with get_engine().connect() as conn:
        from sqlalchemy import text

        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert "cached_messages" not in tables


def test_sending_now_from_a_conversation_is_not_stored(client):
    r = client.post(f"/ui/chats/{client.sid}/send", data={"chat": JOAO, "text": "enviada na hora, sem guardar"})
    assert r.status_code == 200 and client.waha.sent[-1]["text"] == "enviada na hora, sem guardar"
    _assert_no_trace("sem guardar", "991110001")


# --------------------------------------------------------------------------- #
# privacy_cleanup
# --------------------------------------------------------------------------- #
def test_privacy_cleanup_finds_leftovers_and_applies_retention(client, monkeypatch):
    now = utcnow()
    with Session(get_engine()) as db:
        # 1. sobra: mensagem encerrada que por algum motivo ainda tem conteúdo
        leftover = make_schedule(user_id=client.user.id, session="s", chat_id=JOAO, text="sobra antiga",
                                 timezone=TZ, first_run_local=datetime(2020, 1, 1), enabled=False)
        db.add(leftover)
        # 2. hash de destinatário de mensagem encerrada há mais de 30 dias
        old = Schedule(user_id=client.user.id, session="s", timezone=TZ, first_run_local=datetime(2020, 1, 1), enabled=False,
                       recipient_phone_hash="h" * 64, content_purged_at=now - timedelta(days=40))
        db.add(old)
        # 3. IP de login antigo
        db.add(LoginAuditEvent(user_id=client.user.id, event_type=AuditEventType.login_success, ip_address="203.0.113.9",
                               user_agent="Mozilla", created_at=now - timedelta(days=45)))
        # 4. conexão Google desconectada ainda com tokens
        db.add(CalendarConnection(user_id=client.user.id, provider="google", access_token_enc=crypto.encrypt("tok"),
                                  refresh_token_enc=crypto.encrypt("refresh"), token_expires_at=now,
                                  status=CalendarConnectionStatus.disconnected))
        db.commit()
        leftover_id, old_id = leftover.id, old.id

    counts = asyncio.run(retention.run_cleanup_async(None))
    assert counts["schedules_content"] >= 1 and counts["recipient_hashes"] >= 1
    assert counts["login_ips"] >= 1 and counts["google_tokens"] == 1
    with Session(get_engine()) as db:
        assert db.get(Schedule, leftover_id).message_ciphertext is None
        assert db.get(Schedule, old_id).recipient_phone_hash is None
        assert all(e.ip_address is None for e in db.exec(select(LoginAuditEvent)).all() if e.created_at < now - timedelta(days=31))
        conn = db.exec(select(CalendarConnection)).one()
        assert conn.access_token_enc == "" and conn.refresh_token_enc == ""
    _assert_no_trace("sobra antiga")


def test_privacy_cleanup_log_contains_only_counts(client, caplog):
    _create(client, messages=["conteúdo que não pode ir pro log"])
    with Session(get_engine()) as db:
        for s in db.exec(select(Schedule)).all():
            s.enabled = False
            db.add(s)
        db.commit()
    caplog.set_level("INFO")
    asyncio.run(retention.run_cleanup_async(None))
    assert "records_cleaned=" in caplog.text
    assert "não pode ir pro log" not in caplog.text and "5514991110001" not in caplog.text


def test_disconnecting_a_whatsapp_logs_out_and_deletes_the_waha_session(client):
    name = _session_name(client)
    r = client.post(f"/whatsapps/{client.sid}/disconnect")
    assert r.status_code == 200
    assert client.waha.logged_out == [name] and client.waha.deleted == [name]
    with Session(get_engine()) as db:
        session = db.get(WhatsAppSession, client.sid)
        assert session.disconnected_at is not None and session.waha_purged_at is not None


def test_disconnecting_google_wipes_the_tokens(client, fake_google, monkeypatch):
    monkeypatch.setattr(calendar_service, "get_provider", lambda key: fake_google)
    with Session(get_engine()) as db:
        connection = asyncio.run(calendar_service.finish_connect(db, provider_key="google", code="c", user_id=client.user.id))
        connection_id = connection.id
    assert client.post(f"/ui/configuracoes/connections/{connection_id}/disconnect").status_code == 200
    with Session(get_engine()) as db:
        connection = db.get(CalendarConnection, connection_id)
        assert connection.status == CalendarConnectionStatus.disconnected
        assert connection.access_token_enc == "" and connection.refresh_token_enc == ""
    _assert_no_trace("fake-access-token", "fake-refresh-token")
