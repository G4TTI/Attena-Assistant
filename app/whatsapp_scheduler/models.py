"""Tabelas: `schedules` (a regra) e `dispatches` (cada ocorrência a enviar)."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from .clock import utcnow


def _uuid() -> str:
    return str(uuid4())


class DispatchStatus(str, enum.Enum):
    pending = "pending"        # aguardando o horário / próxima tentativa
    processing = "processing"  # sendo enviada agora (lock do poller)
    sent = "sent"              # confirmada pelo WAHA
    failed = "failed"          # esgotou as tentativas
    canceled = "canceled"      # schedule cancelado antes do disparo
    skipped = "skipped"        # atrasada além de MAX_OVERDUE_MINUTES

    def __str__(self) -> str:  # facilita uso em templates
        return self.value


TERMINAL_STATUSES = {
    DispatchStatus.sent,
    DispatchStatus.failed,
    DispatchStatus.canceled,
    DispatchStatus.skipped,
}
OPEN_STATUSES = {DispatchStatus.pending, DispatchStatus.processing}


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"

    id: str = Field(default_factory=_uuid, primary_key=True)
    session: str = "default"
    recipient_input: str
    chat_id: str = Field(index=True)
    text: str
    timezone: str
    # Horário informado pelo usuário, naive, interpretado em `timezone`.
    first_run_local: datetime
    # None = disparo único. Caso contrário, expressão cron de 5 campos.
    recurrence: str | None = None
    enabled: bool = Field(default=True, index=True)
    max_attempts: int = 3
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Dispatch(SQLModel, table=True):
    __tablename__ = "dispatches"

    id: str = Field(default_factory=_uuid, primary_key=True)
    schedule_id: str = Field(foreign_key="schedules.id", index=True)
    scheduled_at_utc: datetime = Field(index=True)
    status: DispatchStatus = Field(default=DispatchStatus.pending, index=True)
    attempts: int = 0
    last_error: str | None = None
    waha_message_id: str | None = None
    sent_at_utc: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CachedMessage(SQLModel, table=True):
    """Cache local do histórico de conversas (o WEBJS é lento para buscar)."""

    __tablename__ = "cached_messages"

    message_id: str = Field(primary_key=True)
    chat_id: str = Field(index=True)
    ts: int = Field(default=0, index=True)  # epoch em segundos
    from_me: bool = False
    body: str = ""
    msg_type: str = "chat"
    has_media: bool = False
    ack_name: str | None = None
    synced_at: datetime = Field(default_factory=utcnow)
