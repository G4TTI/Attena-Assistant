"""Fixtures compartilhadas. Precisa configurar o ambiente ANTES de importar o app."""

from __future__ import annotations

import os
import tempfile
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

import pytest  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

import whatsapp_scheduler.models  # noqa: E402,F401  (registra as tabelas)
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
