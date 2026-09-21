"""API REST de calendários externos (conexões, calendários, eventos, automações) —
sempre filtrada pelo dono autenticado."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from .. import app_settings, auth, calendar_service, timing, whatsapp_service
from ..calendar_schemas import AutomationRead, CalendarRead, ConnectionRead, EventRead
from ..db import get_session
from ..models import User
from ..service import ValidationError
from sqlmodel import Session

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/connections", response_model=list[ConnectionRead])
def list_connections(
    db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_api)
) -> list[ConnectionRead]:
    return [ConnectionRead.of(c) for c in calendar_service.list_connections(db, current_user.id)]


@router.delete("/connections/{connection_id}")
def disconnect(
    connection_id: str, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_api)
) -> dict:
    if not calendar_service.disconnect(db, connection_id, current_user.id):
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    return {"status": "disconnected", "id": connection_id}


@router.post("/connections/{connection_id}/sync", response_model=ConnectionRead)
async def sync_now(
    connection_id: str, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_api)
) -> ConnectionRead:
    connection = await calendar_service.sync_now(db, connection_id, current_user.id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    return ConnectionRead.of(connection)


@router.get("/connections/{connection_id}/calendars", response_model=list[CalendarRead])
def list_calendars(
    connection_id: str, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_api)
) -> list[CalendarRead]:
    return [CalendarRead.of(c) for c in calendar_service.list_calendars(db, connection_id, current_user.id)]


@router.post("/calendars/{calendar_id}/toggle", response_model=CalendarRead)
def toggle_calendar(
    calendar_id: str,
    enabled: bool = Body(..., embed=True),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> CalendarRead:
    calendar = calendar_service.set_calendar_enabled(db, calendar_id, enabled, current_user.id)
    if calendar is None:
        raise HTTPException(status_code=404, detail="Calendário não encontrado.")
    return CalendarRead.of(calendar)


@router.get("/events", response_model=list[EventRead])
def list_events(
    days: int | None = None, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_api)
) -> list[EventRead]:
    out = []
    for event in calendar_service.agenda(db, current_user.id, days=days):
        automations = [
            AutomationRead.of(item) for item in calendar_service.event_automations(db, event.id, current_user.id)
        ]
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
    whatsapp_session_id: str = Body(...),
    custom_interval: str | None = Body(None),
    timezone_name: str | None = Body(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> AutomationRead:
    wa_session = whatsapp_service.get_session(db, whatsapp_session_id, current_user.id)
    if wa_session is None:
        raise HTTPException(status_code=422, detail="WhatsApp inválido ou de outro usuário.")
    try:
        # `custom_interval` ("1:45") = Intervalo "Personalizado": vira minutos
        # pela mesma regra do formulário (`timing.build_offset_rule`).
        if custom_interval:
            rule = timing.build_offset_rule(offset_direction, timing.CUSTOM_INTERVAL_VALUE, custom_interval)
            offset_amount, offset_unit = rule.amount, rule.unit
        automation = calendar_service.create_event_automation(
            db,
            event_id=event_id,
            user_id=current_user.id,
            waha_session=wa_session.session_name,
            recipients=recipients,
            messages=messages,
            offset_amount=offset_amount,
            offset_unit=offset_unit,
            offset_direction=offset_direction,
            custom_interval=custom_interval,
            # Sempre o fuso do usuário (o mesmo de todas as telas), salvo pedido explícito.
            timezone_name=timezone_name or app_settings.user_timezone(current_user),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    for item in calendar_service.event_automations(db, event_id, current_user.id):
        if item["automation"].id == automation.id:
            return AutomationRead.of(item)
    raise HTTPException(status_code=500, detail="Automação criada mas não encontrada logo em seguida.")


@router.delete("/automations/{automation_id}")
def delete_automation(
    automation_id: str, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_api)
) -> dict:
    if not calendar_service.remove_event_automation(db, automation_id, current_user.id):
        raise HTTPException(status_code=404, detail="Automação não encontrada.")
    return {"status": "canceled", "id": automation_id}
