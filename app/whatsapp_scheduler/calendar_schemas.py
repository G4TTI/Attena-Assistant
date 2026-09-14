"""DTOs de leitura para calendários externos — mesma convenção de `schemas.py`
(`XRead.of(row)`). Nunca incluem token de acesso/atualização, nem cifrado."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .models import Calendar, CalendarConnection, Event


class ConnectionRead(BaseModel):
    id: str
    provider: str
    account_identifier: str
    status: str
    last_sync_at: datetime | None
    last_sync_error: str | None
    created_at: datetime

    @classmethod
    def of(cls, c: CalendarConnection) -> "ConnectionRead":
        return cls(
            id=c.id,
            provider=c.provider,
            account_identifier=c.account_identifier,
            status=str(c.status),
            last_sync_at=c.last_sync_at,
            last_sync_error=c.last_sync_error,
            created_at=c.created_at,
        )


class CalendarRead(BaseModel):
    id: str
    connection_id: str
    external_id: str
    name: str
    color: str | None
    enabled: bool

    @classmethod
    def of(cls, cal: Calendar) -> "CalendarRead":
        return cls(
            id=cal.id,
            connection_id=cal.connection_id,
            external_id=cal.external_id,
            name=cal.name,
            color=cal.color,
            enabled=cal.enabled,
        )


class AutomationRead(BaseModel):
    id: str
    event_id: str
    enabled: bool
    offset_amount: int
    offset_unit: str
    offset_direction: str
    recipients: list[str]
    messages: list[str]

    @classmethod
    def of(cls, item: dict) -> "AutomationRead":
        """`item` é uma entrada de `calendar_service.event_automations()` —
        `{"automation", "recipients", "messages", "enabled"}`."""
        automation = item["automation"]
        return cls(
            id=automation.id,
            event_id=automation.event_id,
            enabled=item["enabled"],
            offset_amount=automation.offset_amount,
            offset_unit=str(automation.offset_unit),
            offset_direction=str(automation.offset_direction),
            recipients=item["recipients"],
            messages=[row["message"].text for row in item["messages"]],
        )


class EventRead(BaseModel):
    id: str
    source: str
    calendar_id: str | None
    title: str
    description: str
    start_utc: datetime
    end_utc: datetime
    timezone: str
    all_day: bool
    status: str
    is_external: bool
    automations: list[AutomationRead] = []

    @classmethod
    def of(cls, e: Event, automations: list[AutomationRead] | None = None) -> "EventRead":
        return cls(
            id=e.id,
            source=str(e.source),
            calendar_id=e.calendar_id,
            title=e.title,
            description=e.description,
            start_utc=e.start_utc,
            end_utc=e.end_utc,
            timezone=e.timezone,
            all_day=e.all_day,
            status=str(e.status),
            is_external=e.source != "internal",
            automations=automations or [],
        )
