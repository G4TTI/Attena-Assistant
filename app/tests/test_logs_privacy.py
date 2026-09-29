"""Logs seguros: nem os call sites nem bibliotecas vazam conteúdo, telefone, token,
senha, cookie, CPF ou QR — e o sanitizador central pega o que escapar."""

import asyncio
import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import FakeWaha, register_and_login, whatsapp_session_id
from whatsapp_scheduler import log_sanitizer, timing
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import WhatsAppSession
from whatsapp_scheduler.scheduler import SchedulerService
from whatsapp_scheduler.service import create_sequence


@pytest.mark.parametrize(
    "raw, leaked",
    [
        ("dispatch enviada para 5514991110001@c.us", "5514991110001"),
        ("id true_5514991110001@c.us_3EB0ABCDEF", "5514991110001"),
        ("GET /api/u_1/chats/5511999998888@c.us/messages?limit=50", "5511999998888"),
        ("Authorization: Bearer ya29.a0AfH6SMBsecret", "ya29.a0AfH6SMBsecret"),
        ('{"access_token": "ya29.token", "refresh_token": "1//refresh"}', "1//refresh"),
        ("callback ?code=4/0AbCdEf&state=xyz123", "4/0AbCdEf"),
        ("link /redefinir-senha/AbCdEf123456_-tok", "AbCdEf123456_-tok"),
        ("password=hunter2hunter2", "hunter2hunter2"),
        ("Cookie: attena_session=abcdef123456", "abcdef123456"),
        ("CPF 123.456.789-09 do cliente", "123.456.789-09"),
        ("telefone +55 (14) 99111-0001", "99111-0001"),
        ("qr 2@AbCdEfGhIjKlMnOpQrStUv,xyz,abc", "2@AbCdEfGhIjKlMnOpQrStUv"),
        ("img data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==", "iVBORw0KGgo"),
        ("e-mail fulano@example.com tentou", "fulano@example.com"),
        ('webhook {"body": "mensagem privada do cliente"}', "mensagem privada do cliente"),
    ],
)
def test_redact_removes_sensitive_data(raw, leaked):
    assert leaked not in log_sanitizer.redact(raw)


def test_redact_keeps_operational_metadata():
    line = "dispatch 550e8400-e29b-41d4-a716-446655440000 falhou (tentativa 2/3, waha_rejected), retry em 300s em 2026-09-29 10:00:00"
    assert log_sanitizer.redact(line) == line


def test_access_log_path_loses_query_and_tokens():
    assert log_sanitizer.redact_path("/ui/chats/abc/messages?chat=5511999998888%40c.us") == "/ui/chats/abc/messages?[redacted]"
    assert "tok123" not in log_sanitizer.redact_path("/verificar-email/tok123")


def test_filter_sanitizes_messages_args_and_tracebacks():
    record = logging.LogRecord("x", logging.ERROR, __file__, 1, "enviado para %s", ("5514991110001@c.us",), None)
    try:
        raise RuntimeError("falhou com token=supersecreto123")
    except RuntimeError:
        import sys

        record.exc_info = sys.exc_info()
    log_sanitizer.SanitizingFilter().filter(record)
    assert "5514991110001" not in record.getMessage()
    assert "supersecreto123" not in record.exc_text


def test_uvicorn_access_record_keeps_format_but_redacts_path():
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
        ("1.2.3.4:5", "GET", "/calendario/oauth/callback?code=SECRET&state=S", "1.1", 303), None,
    )
    log_sanitizer.SanitizingFilter().filter(record)
    assert "SECRET" not in record.getMessage() and "/calendario/oauth/callback?[redacted]" in record.getMessage()


def test_handlers_have_the_filter_and_httpx_is_quiet():
    log_sanitizer.install()
    root = logging.getLogger()
    assert all(any(isinstance(f, log_sanitizer.SanitizingFilter) for f in h.filters) for h in root.handlers)
    assert logging.getLogger("httpx").level >= logging.WARNING


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        c.user = register_and_login(c)
        c.sid = whatsapp_session_id(c)
        yield c


def test_sending_a_scheduled_message_logs_no_content_or_phone(client, caplog):
    caplog.set_level(logging.DEBUG)
    with Session(get_engine()) as db:
        session_name = db.get(WhatsAppSession, client.sid).session_name
        create_sequence(
            db, user_id=client.user.id, session=session_name, recipient="+55 14 99111-0001",
            messages=["texto super confidencial"], start=timing.to_local(utcnow(), "America/Sao_Paulo") - timedelta(minutes=1),
            timezone="America/Sao_Paulo",
        )
    asyncio.run(SchedulerService(client.waha).run_once())
    assert client.waha.sent
    assert "enviada" in caplog.text  # houve log operacional…
    assert "confidencial" not in caplog.text and "991110001" not in caplog.text  # …sem conteúdo nem telefone


def test_password_reset_and_login_never_log_tokens_or_passwords(client, caplog):
    caplog.set_level(logging.DEBUG)
    client.post("/esqueci-senha", data={"email": "tester@example.com"})
    client.post("/login", data={"email": "tester@example.com", "password": "senha-errada-123"})
    assert "/redefinir-senha/" not in caplog.text
    assert "senha-errada-123" not in caplog.text
    assert "tester@example.com" not in caplog.text
