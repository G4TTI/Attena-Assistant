"""DTOs da API REST."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .models import Dispatch, Schedule


class ScheduleCreate(BaseModel):
    recipient: str = Field(..., description="Telefone (+55 11 99999-8888) ou chatId (...@c.us / ...@g.us)")
    text: str = Field(..., min_length=1, max_length=4096)
    send_at: datetime = Field(..., description="Data/hora do 1º envio. ISO 8601; sem offset = interpretado na timezone abaixo.")
    timezone: str | None = Field(None, description="IANA, ex: America/Sao_Paulo. Default do servidor se omitido.")
    recurrence: str | None = Field(None, description="cron de 5 campos ou preset: 'daily 09:00', 'weekly mon 08:30', 'monthly 1 12:00', 'hourly'")
    session: str | None = Field(None, description="Sessão WAHA. Default do servidor se omitido.")
    max_attempts: int = Field(3, ge=1, le=10)


class DispatchRead(BaseModel):
    id: str
    schedule_id: str
    scheduled_at_utc: datetime
    status: str
    attempts: int
    last_error: str | None
    waha_message_id: str | None
    sent_at_utc: datetime | None

    @classmethod
    def of(cls, d: Dispatch) -> "DispatchRead":
        return cls(
            id=d.id,
            schedule_id=d.schedule_id,
            scheduled_at_utc=d.scheduled_at_utc,
            status=str(d.status),
            attempts=d.attempts,
            last_error=d.last_error,
            waha_message_id=d.waha_message_id,
            sent_at_utc=d.sent_at_utc,
        )


class ScheduleRead(BaseModel):
    id: str
    session: str
    recipient_input: str
    chat_id: str
    text: str
    timezone: str
    first_run_local: datetime
    recurrence: str | None
    enabled: bool
    max_attempts: int
    created_at: datetime
    group_id: str | None = None
    position: int = 0
    next_dispatch: DispatchRead | None = None
    dispatches: list[DispatchRead] = []

    @classmethod
    def of(cls, s: Schedule, dispatches: list[Dispatch] | None = None) -> "ScheduleRead":
        dispatches = dispatches or []
        pending = [d for d in dispatches if str(d.status) in ("pending", "processing")]
        pending.sort(key=lambda d: d.scheduled_at_utc)
        return cls(
            id=s.id,
            session=s.session,
            recipient_input=s.recipient_input,
            chat_id=s.chat_id,
            text=s.text,
            timezone=s.timezone,
            first_run_local=s.first_run_local,
            recurrence=s.recurrence,
            enabled=s.enabled,
            max_attempts=s.max_attempts,
            created_at=s.created_at,
            group_id=s.group_id,
            position=s.position,
            next_dispatch=DispatchRead.of(pending[0]) if pending else None,
            dispatches=[DispatchRead.of(d) for d in sorted(dispatches, key=lambda d: d.scheduled_at_utc, reverse=True)],
        )


class SessionInfo(BaseModel):
    name: str | None = None
    status: str | None = None
    raw: dict | None = None
