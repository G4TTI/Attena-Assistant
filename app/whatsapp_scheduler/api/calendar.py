"""API REST de calendários externos (conexões, calendários, eventos, automações)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlmodel import Session

from .. import calendar_service
from ..calendar_schemas import AutomationRead, CalendarRead, ConnectionRead, EventRead
from ..db import get_session
from ..service import ValidationError

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/connections", response_model=list[ConnectionRead])
def list_connections(db: Session = Depends(get_session)) -> list[ConnectionRead]:
    return [ConnectionRead.of(c) for c in calendar_service.list_connections(db)]


@router.delete("/connections/{connection_id}")
def disconnect(connection_id: str, db: Session = Depends(get_session)) -> dict:
    if not calendar_service.disconnect(db, connection_id):
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    return {"status": "disconnected", "id": connection_id}


@router.post("/connections/{connection_id}/sync", response_model=ConnectionRead)
async def sync_now(connection_id: str, db: Session = Depends(get_session)) -> ConnectionRead:
    connection = await calendar_service.sync_now(db, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    return ConnectionRead.of(connection)


@router.get("/connections/{connection_id}/calendars", response_model=list[CalendarRead])
def list_calendars(connection_id: str, db: Session = Depends(get_session)) -> list[CalendarRead]:
    return [CalendarRead.of(c) for c in calendar_service.list_calendars(db, connection_id)]


@router.post("/calendars/{calendar_id}/toggle", response_model=CalendarRead)
def toggle_calendar(
    calendar_id: str, enabled: bool = Body(..., embed=True), db: Session = Depends(get_session)
) -> CalendarRead:
    calendar = calendar_service.set_calendar_enabled(db, calendar_id, enabled)
    if calendar is None:
        raise HTTPException(status_code=404, detail="Calendário não encontrado.")
    return CalendarRead.of(calendar)


@router.get("/events", response_model=list[EventRead])
def list_events(days: int | None = None, db: Session = Depends(get_session)) -> list[EventRead]:
    out = []
    for event in calendar_service.agenda(db, days=days):
        automations = [AutomationRead.of(item) for item in calendar_service.event_automations(db, event.id)]
        out.append(EventRead.of(event, automations))
    return out


@router.post("/events/{event_id}/automations", response_model=AutomationRead, status_code=201)
def create_automation(
    event_id: str,
    recipients: list[str] = Body(...),
    messages: list[str] = Body(...),
    offset_amount: int = Body(...),
    offset_unit: str = Body(...),
    offset_direction: str = Body(...),
    timezone_name: str | None = Body(None),
    db: Session = Depends(get_session),
) -> AutomationRead:
    try:
        automation = calendar_service.create_event_automation(
            db,
            event_id=event_id,
            recipients=recipients,
            messages=messages,
            offset_amount=offset_amount,
            offset_unit=offset_unit,
            offset_direction=offset_direction,
            timezone_name=timezone_name,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    for item in calendar_service.event_automations(db, event_id):
        if item["automation"].id == automation.id:
            return AutomationRead.of(item)
    raise HTTPException(status_code=500, detail="Automação criada mas não encontrada logo em seguida.")


@router.delete("/automations/{automation_id}")
def delete_automation(automation_id: str, db: Session = Depends(get_session)) -> dict:
    if not calendar_service.remove_event_automation(db, automation_id):
        raise HTTPException(status_code=404, detail="Automação não encontrada.")
    return {"status": "canceled", "id": automation_id}
