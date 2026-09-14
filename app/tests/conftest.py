"""Fixtures compartilhadas. Precisa configurar o ambiente ANTES de importar o app."""

from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="wascheduler-test-"))
os.environ.setdefault("DB_PATH", str(_TMP / "test.db"))
os.environ.setdefault("WAHA_BASE_URL", "http://waha.test")
os.environ.setdefault("WAHA_API_KEY", "test-key")
os.environ.setdefault("WAHA_SESSION", "default")
os.environ.setdefault("DEFAULT_TIMEZONE", "America/Sao_Paulo")
os.environ.setdefault("MAX_OVERDUE_MINUTES", "120")
os.environ.setdefault("SEND_JITTER_SECONDS", "0")
os.environ.setdefault("TICK_SECONDS", "3600")  # o loop não dispara sozinho durante os testes
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8090/calendario/oauth/callback")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "8bxweqvwKGVGSYYLOSnwiZWC6TbNYabjfPe-6QBio10=")
os.environ.setdefault("CALENDAR_SYNC_SECONDS", "3600")  # idem: não dispara sozinho durante os testes

import pytest  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

import whatsapp_scheduler.models  # noqa: E402,F401  (registra as tabelas)
from whatsapp_scheduler.calendar_providers.base import (  # noqa: E402
    OAuthTokens,
    RemoteCalendar,
    RemoteEvent,
    RemoteEventPage,
)
from whatsapp_scheduler.clock import utcnow  # noqa: E402
from whatsapp_scheduler.db import get_engine  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db():
    with Session(get_engine()) as session:
        yield session


class FakeWaha:
    """Stub do WahaClient para os testes do scheduler."""

    def __init__(self, status: str = "WORKING") -> None:
        self.status = status
        self.sent: list[dict] = []
        self.send_error: Exception | None = None
        self.status_error: Exception | None = None
        self.chats: list[dict] = []
        self.messages: list[dict] = []
        self.chats_error: Exception | None = None
        self.messages_error: Exception | None = None
        self.restart_error: Exception | None = None
        self.restart_calls = 0

    async def get_session_status(self, session: str) -> dict:
        if self.status_error:
            raise self.status_error
        return {"name": session, "status": self.status}

    async def send_text(self, session: str, chat_id: str, text: str) -> dict:
        if self.send_error:
            raise self.send_error
        self.sent.append({"session": session, "chatId": chat_id, "text": text})
        return {"id": f"true_{chat_id}_{len(self.sent)}"}

    async def get_qr(self, session: str) -> tuple[bytes, str]:
        return b"PNGDATA", "image/png"

    async def start_session(self, session: str) -> dict:
        return {"name": session, "status": "STARTING"}

    async def restart_session(self, session: str) -> dict:
        self.restart_calls += 1
        if self.restart_error:
            raise self.restart_error
        self.status = "STARTING"
        return {"name": session, "status": "STARTING"}

    async def get_chats_overview(
        self, session: str, limit: int = 50, timeout: float | None = None
    ) -> list[dict]:
        if self.chats_error:
            raise self.chats_error
        return self.chats

    async def get_messages(
        self, session: str, chat_id: str, limit: int = 50, timeout: float | None = None
    ) -> list[dict]:
        if self.messages_error:
            raise self.messages_error
        return self.messages

    async def aclose(self) -> None:  # pragma: no cover
        pass


@pytest.fixture
def fake_waha() -> FakeWaha:
    return FakeWaha()


class FakeGoogleCalendarProvider:
    """Stub de `CalendarProvider` (ver calendar_providers/base.py) para os testes de sync."""

    key = "google"

    def __init__(self) -> None:
        self.configured = True
        self.account_email: str | None = "fake@example.com"
        self.calendars: list[RemoteCalendar] = []
        # external_calendar_id -> eventos que a PRÓXIMA chamada de list_events devolve
        self.events_by_calendar: dict[str, list[RemoteEvent]] = {}
        self.next_sync_token_by_calendar: dict[str, str | None] = {}
        # calendários cuja próxima chamada deve simular um syncToken expirado (410)
        self.invalidate_sync_token_for: set[str] = set()
        self.list_events_calls: list[dict] = []
        self.exchange_code_calls: list[str] = []
        self.refresh_calls: list[OAuthTokens] = []
        self.list_calendars_error: Exception | None = None
        self.list_events_error: Exception | None = None
        self.create_event_error: Exception | None = None
        self.update_event_error: Exception | None = None
        self.delete_event_error: Exception | None = None
        self.created_events: list[dict] = []
        self.updated_events: list[dict] = []
        self.deleted_events: list[str] = []
        self._next_external_id = 1

    def is_configured(self) -> bool:
        return self.configured

    def get_authorize_url(self, state: str) -> str:
        return f"https://accounts.google.test/authorize?state={state}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        self.exchange_code_calls.append(code)
        return OAuthTokens(
            access_token="fake-access-token",
            refresh_token="fake-refresh-token",
            expires_at=utcnow() + timedelta(hours=1),
            scope="https://www.googleapis.com/auth/calendar.readonly",
        )

    async def refresh(self, tokens: OAuthTokens) -> OAuthTokens:
        self.refresh_calls.append(tokens)
        return OAuthTokens(
            access_token="fake-access-token-refreshed",
            refresh_token=tokens.refresh_token,
            expires_at=utcnow() + timedelta(hours=1),
            scope=tokens.scope,
        )

    async def get_account_identifier(self, tokens: OAuthTokens) -> str | None:
        return self.account_email

    async def list_calendars(self, tokens: OAuthTokens) -> list[RemoteCalendar]:
        if self.list_calendars_error:
            raise self.list_calendars_error
        return self.calendars

    async def list_events(
        self,
        tokens: OAuthTokens,
        calendar: RemoteCalendar,
        *,
        sync_token: str | None = None,
        time_min=None,
        time_max=None,
    ) -> RemoteEventPage:
        self.list_events_calls.append(
            {"calendar": calendar.external_id, "sync_token": sync_token, "time_min": time_min, "time_max": time_max}
        )
        if self.list_events_error:
            raise self.list_events_error
        if calendar.external_id in self.invalidate_sync_token_for:
            self.invalidate_sync_token_for.discard(calendar.external_id)
            return RemoteEventPage(events=[], next_sync_token=None, sync_token_invalid=True)
        events = self.events_by_calendar.get(calendar.external_id, [])
        next_token = self.next_sync_token_by_calendar.get(calendar.external_id, "next-token")
        return RemoteEventPage(events=events, next_sync_token=next_token)

    async def create_event(self, tokens, calendar, *, title, description, start_utc, end_utc, timezone) -> str:
        if self.create_event_error:
            raise self.create_event_error
        self._next_external_id += 1
        external_id = f"fake-ext-{self._next_external_id}"
        self.created_events.append(
            {"calendar": calendar.external_id, "title": title, "start_utc": start_utc, "external_id": external_id}
        )
        return external_id

    async def update_event(self, tokens, calendar, external_id, *, title, description, start_utc, end_utc, timezone):
        if self.update_event_error:
            raise self.update_event_error
        self.updated_events.append(
            {"calendar": calendar.external_id, "external_id": external_id, "title": title, "start_utc": start_utc}
        )

    async def delete_event(self, tokens, calendar, external_id) -> None:
        if self.delete_event_error:
            raise self.delete_event_error
        self.deleted_events.append(external_id)


@pytest.fixture
def fake_google() -> FakeGoogleCalendarProvider:
    return FakeGoogleCalendarProvider()
