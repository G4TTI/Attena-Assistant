"""UI web da página Calendário: grade mensal, modais de evento/automação.

Padrão de modal usado em toda essa página (ver `base.html` pro CSS/JS
genérico): abrir = `hx-get` alvo `#modal-root`; uma ação que muda dados
devolve só um `<div id="calendar-grid" hx-swap-oob="true">` — o htmx aplica
esse pedaço na grade (em qualquer lugar da página) e limpa o `#modal-root`
sozinho, porque não sobrou nada pro swap "normal" depois de tirar o trecho
OOB da resposta. Fecha o modal e atualiza a grade numa resposta só, sem
round-trip extra.

Todo evento/automação/calendário é sempre carregado já filtrado pelo dono
(`current_user`) — nunca por id cru — pra um usuário nunca conseguir ler ou
editar o recurso de outro só trocando o id na URL.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, col, select

from .. import app_settings, auth, calendar_service, timing, whatsapp_service
from ..db import get_session
from ..models import (
    Automation,
    AutomationMessage,
    AutomationSchedule,
    Calendar,
    Event,
    EventSyncStatus,
    Schedule,
    ScheduleGroup,
    User,
)
from ..recurrence import utc_to_local
from ..service import ValidationError
from ..waha import WahaClient, WahaError
from .routes import pair_recipients, templates

router = APIRouter(tags=["ui-calendario"])

# strftime('%A'/'%B') depende da locale do sistema (o container não tem
# pt_BR instalada) — mapear manualmente evita nomes de dia/mês em inglês.
_WEEKDAYS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _waha(request: Request) -> WahaClient:
    return request.app.state.waha


def _day_label(day: date) -> str:
    return f"{_WEEKDAYS_PT[day.weekday()]}, {day.strftime('%d/%m')}"


def _month_label(year: int, month: int) -> str:
    return f"{_MONTHS_PT[month - 1]} {year}"


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, idx % 12 + 1


def _ctx(request: Request, current_user: User, **extra: object) -> dict:
    return {"request": request, "nav": "calendario", **extra}


def _current_year_month(year: int | None, month: int | None, tz_name: str) -> tuple[int, int]:
    today = utc_to_local(calendar_service.utcnow(), tz_name).date()
    return year or today.year, month or today.month


def _filterable_calendars(db: Session, user_id: str) -> list[dict]:
    out = [{"key": "internal", "name": "Interno", "color": None}]
    for connection in calendar_service.list_connections(db, user_id):
        for cal in calendar_service.list_calendars(db, connection.id, user_id):
            if cal.enabled:
                out.append({"key": cal.id, "name": cal.name, "color": cal.color})
    return out


def _google_target_calendars(db: Session, user_id: str) -> list[Calendar]:
    """Calendários Google habilitados — opções do seletor "Calendário" ao
    criar um evento (além de "Calendário interno", sempre disponível)."""
    out: list[Calendar] = []
    for connection in calendar_service.list_connections(db, user_id):
        out.extend(cal for cal in calendar_service.list_calendars(db, connection.id, user_id) if cal.enabled)
    return out


def _automation_summary_map(db: Session, event_ids: list[str]) -> dict[str, dict]:
    """Uma consulta só pra saber quantas automações ATIVAS cada evento tem —
    evita N+1 na grade mensal (pode ter dezenas de eventos numa tela só).
    Conta `Automation`s distintas (não `Schedule`s) — uma automação com
    várias mensagens/destinatários não deve inflar o número no chip.
    `event_ids` já vem filtrado por dono (de `month_grid`), então não precisa
    de `user_id` aqui."""
    if not event_ids:
        return {}
    rows = db.exec(
        select(Automation.event_id, Automation.id, Schedule.enabled)
        .join(AutomationSchedule, col(AutomationSchedule.automation_id) == col(Automation.id))
        .join(Schedule, col(AutomationSchedule.schedule_id) == col(Schedule.id))
        .where(col(Automation.event_id).in_(event_ids))
    ).all()
    active_by_event: dict[str, set[str]] = {}
    for event_id, automation_id, enabled in rows:
        if enabled:
            active_by_event.setdefault(event_id, set()).add(automation_id)
    return {event_id: {"count": len(ids)} for event_id, ids in active_by_event.items()}


def _event_chip(event: Event, automation_info: dict[str, dict]) -> dict:
    info = automation_info.get(event.id)
    return {
        "event": event,
        "start_local": utc_to_local(event.start_utc, event.timezone),
        "is_external": event.source != "internal",
        "calendar_key": event.calendar_id or "internal",
        "automation_count": info["count"] if info else 0,
    }


def _grid_ctx(db: Session, user_id: str, year: int, month: int, tz_name: str, *, oob: bool = False) -> dict:
    weeks = calendar_service.month_grid(db, user_id, year, month, tz_name)
    all_event_ids = [e.id for week in weeks for day in week for e in day["events"]]
    automation_info = _automation_summary_map(db, all_event_ids)
    grid = [
        [{**day, "chips": [_event_chip(e, automation_info) for e in day["events"]]} for day in week]
        for week in weeks
    ]
    prev_year, prev_month = _shift_month(year, month, -1)
    next_year, next_month = _shift_month(year, month, 1)
    today = utc_to_local(calendar_service.utcnow(), tz_name).date()
    return {
        "weeks": grid,
        "year": year,
        "month": month,
        "month_label": _month_label(year, month),
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "today_year": today.year,
        "today_month": today.month,
        "today_date": today.isoformat(),
        "calendars_for_filter": _filterable_calendars(db, user_id),
        "has_connection": bool(calendar_service.list_connections(db, user_id)),
        "oob": oob,
    }


def _day_event_row(event: Event, automation_info: dict[str, dict]) -> dict:
    tz = event.timezone
    info = automation_info.get(event.id)
    return {
        "event": event,
        "start_local": utc_to_local(event.start_utc, tz),
        "end_local": utc_to_local(event.end_utc, tz),
        "is_external": event.source != "internal",
        "automation_count": info["count"] if info else 0,
    }


def _day_ctx(db: Session, user_id: str, day: date, tz_name: str) -> dict:
    events = calendar_service.day_events(db, user_id, day, tz_name)
    automation_info = _automation_summary_map(db, [e.id for e in events])
    rows = [_day_event_row(e, automation_info) for e in events]
    by_hour: dict[int, list[dict]] = {}
    for row in rows:
        by_hour.setdefault(row["start_local"].hour, []).append(row)
    today = utc_to_local(calendar_service.utcnow(), tz_name).date()
    return {
        "day": day,
        "day_label": _day_label(day),
        "is_today": day == today,
        "today_date": today.isoformat(),
        "prev_date": (day - timedelta(days=1)).isoformat(),
        "next_date": (day + timedelta(days=1)).isoformat(),
        "hours": range(24),
        "by_hour": by_hour,
    }


def _parse_date_str(date_str: str | None, default: date) -> date:
    if not date_str:
        return default
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return default


def _load_event(db: Session, event_id: str, user_id: str) -> Event:
    event = db.get(Event, event_id)
    if event is None or event.user_id != user_id:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    return event


def _event_detail_ctx(db: Session, event: Event, user_id: str, *, year: int, month: int) -> dict:
    tz = event.timezone
    # "is_linked" só marca eventos INTERNOS empurrados pro Google (a
    # funcionalidade nova) — um evento nativamente vindo do Google já mostra
    # o badge "Google Agenda" acima; repetir "sincronizado" ali seria redundante.
    is_linked = event.source == "internal" and bool(event.calendar_id and event.external_id)
    return {
        "event": event,
        "start_local": utc_to_local(event.start_utc, tz),
        "end_local": utc_to_local(event.end_utc, tz),
        "is_external": event.source != "internal",
        "is_linked": is_linked,
        "sync_status": db.get(EventSyncStatus, event.id) if is_linked else None,
        "linked_calendar": db.get(Calendar, event.calendar_id) if is_linked else None,
        "automations": calendar_service.event_automations(db, event.id, user_id),
        "year": year,
        "month": month,
    }


def _parse_local_dt(date_str: str, time_str: str) -> datetime:
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValidationError(f"Data/hora inválida: {date_str} {time_str}") from exc


async def _contacts_ctx(request: Request, waha_session: str) -> dict:
    try:
        contacts = await calendar_service.list_contacts(_waha(request), waha_session)
        return {"contacts": contacts, "contacts_error": None}
    except WahaError as exc:
        return {"contacts": [], "contacts_error": str(exc)}


def _prefill_from_automation(db: Session, automation: Automation) -> tuple[dict, str | None]:
    """Valores do formulário de EDIÇÃO a partir do que está gravado (+ o id do
    WhatsApp usado, pra pré-selecionar). Nada é reinterpretado: "Personalizado ·
    1:45" volta exatamente assim."""
    links = db.exec(select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation.id)).all()
    schedule_ids = [link.schedule_id for link in links]
    schedules = {
        s.id: s
        for s in (db.exec(select(Schedule).where(col(Schedule.id).in_(schedule_ids))).all() if schedule_ids else [])
    }
    group_ids = {s.group_id for s in schedules.values() if s.group_id}
    groups = (
        {g.id: g for g in db.exec(select(ScheduleGroup).where(col(ScheduleGroup.id).in_(group_ids))).all()}
        if group_ids
        else {}
    )
    recipients: dict[str, dict] = {}
    for link in links:
        sch = schedules.get(link.schedule_id)
        if sch is not None and link.recipient_chat_id not in recipients:
            group = groups.get(sch.group_id or "")
            label = (group.recipient_name if group and group.recipient_name else "") or ""
            recipients[link.recipient_chat_id] = {"value": link.recipient_chat_id, "label": label}
    messages = db.exec(
        select(AutomationMessage)
        .where(col(AutomationMessage.automation_id) == automation.id)
        .order_by(col(AutomationMessage.position))
    ).all()
    interval_value, custom_interval = timing.interval_form_values(
        automation.offset_amount, str(automation.offset_unit), automation.custom_interval
    )
    prefill = {
        "recipients": list(recipients.values()),
        "messages": [m.text for m in messages],
        "rule": {
            "direction": str(automation.offset_direction),
            "interval_value": interval_value,
            "custom_interval": custom_interval,
            "custom_time": automation.custom_time_local or "",
        },
    }
    # Todas as mensagens/destinatários de uma automação sempre usam o mesmo
    # WhatsApp (ver create_event_automation) — basta olhar 1 schedule.
    any_schedule = next(iter(schedules.values()), None)
    return prefill, (any_schedule.session if any_schedule else None)


def _automation_modal_ctx(
    db: Session,
    event: Event,
    *,
    user_id: str,
    year: int,
    month: int,
    automation_id: str | None = None,
    form_values: dict | None = None,
) -> dict:
    """`form_values`: o que o usuário tinha digitado quando a validação falhou —
    o modal volta com tudo preenchido em vez de zerar o formulário."""
    tz = event.timezone
    prefill = None
    selected_whatsapp_session_id = None
    if form_values is not None:
        prefill = form_values["prefill"]
        selected_whatsapp_session_id = form_values.get("whatsapp_session_id") or None
    elif automation_id:
        automation = db.get(Automation, automation_id)
        if automation is None:
            raise HTTPException(status_code=404, detail="Automação não encontrada.")
        prefill, session_name = _prefill_from_automation(db, automation)
        if session_name:
            existing = whatsapp_service.session_by_name(db, user_id, session_name)
            selected_whatsapp_session_id = existing.id if existing else None
    return {
        "event": event,
        "start_local": utc_to_local(event.start_utc, tz),
        "year": year,
        "month": month,
        "automation_id": automation_id,
        "prefill": prefill,
        "whatsapp_sessions": whatsapp_service.list_sessions(db, user_id),
        "selected_whatsapp_session_id": selected_whatsapp_session_id,
        "interval_presets": timing.INTERVAL_PRESETS,
        "default_interval_value": timing.DEFAULT_INTERVAL_VALUE,
    }


def _submitted_form_values(
    recipients: list[str], recipient_names: list[str], messages: list[str], whatsapp_session_id: str,
    offset_direction: str, offset_interval: str, custom_interval: str, custom_time: str,
) -> dict:
    return {
        "whatsapp_session_id": whatsapp_session_id,
        "prefill": {
            "recipients": pair_recipients(recipients, recipient_names),
            "messages": messages or [""],
            "rule": {
                "direction": offset_direction if offset_direction in timing.VALID_DIRECTIONS else "before",
                "interval_value": offset_interval or timing.DEFAULT_INTERVAL_VALUE,
                "custom_interval": custom_interval,
                "custom_time": custom_time,
            },
        },
    }


# --------------------------------------------------------------------------- #
# Página + grade
# --------------------------------------------------------------------------- #
@router.get("/calendario", response_class=HTMLResponse)
def page_calendario(
    request: Request,
    year: int | None = Query(None),
    month: int | None = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    tz_name = app_settings.user_timezone(current_user)
    y, m = _current_year_month(year, month, tz_name)
    return templates.TemplateResponse(
        "calendario.html", {**_ctx(request, current_user), **_grid_ctx(db, current_user.id, y, m, tz_name)}
    )


@router.get("/ui/calendario/grid", response_class=HTMLResponse)
def ui_grid(
    request: Request,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    tz_name = app_settings.user_timezone(current_user)
    return templates.TemplateResponse(
        "_calendar_month_grid.html", {"request": request, **_grid_ctx(db, current_user.id, year, month, tz_name)}
    )


# --------------------------------------------------------------------------- #
# Visão diária — o que o botão "Hoje" abre (v1.3, itens 27-31)
# --------------------------------------------------------------------------- #
@router.get("/calendario/dia", response_class=HTMLResponse)
def page_calendario_dia(
    request: Request,
    date_str: str | None = Query(None, alias="date"),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    tz_name = app_settings.user_timezone(current_user)
    today = utc_to_local(calendar_service.utcnow(), tz_name).date()
    day = _parse_date_str(date_str, today)
    return templates.TemplateResponse(
        "calendario_dia.html", {**_ctx(request, current_user), **_day_ctx(db, current_user.id, day, tz_name)}
    )


@router.get("/ui/calendario/dia", response_class=HTMLResponse)
def ui_calendario_dia(
    request: Request,
    date_str: str = Query(..., alias="date"),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    tz_name = app_settings.user_timezone(current_user)
    today = utc_to_local(calendar_service.utcnow(), tz_name).date()
    day = _parse_date_str(date_str, today)
    return templates.TemplateResponse(
        "_calendar_day_view.html", {"request": request, **_day_ctx(db, current_user.id, day, tz_name)}
    )


# --------------------------------------------------------------------------- #
# Evento: criar / ver / editar / excluir
# --------------------------------------------------------------------------- #
@router.get("/ui/calendario/events/new", response_class=HTMLResponse)
def ui_event_new(
    request: Request,
    date_str: str = Query("", alias="date"),
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "_calendar_event_modal.html",
        {
            "request": request,
            "mode": "create",
            "event": None,
            "date_value": date_str,
            "start_value": "09:00",
            "end_value": "10:00",
            "title_value": "",
            "description_value": "",
            "target_calendar_value": "",
            "google_calendars": _google_target_calendars(db, current_user.id),
            "linked_calendar": None,
            "year": year,
            "month": month,
            "form_error": None,
        },
    )


@router.get("/ui/calendario/events/{event_id}", response_class=HTMLResponse)
def ui_event_detail(
    request: Request,
    event_id: str,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    event = _load_event(db, event_id, current_user.id)
    return templates.TemplateResponse(
        "_calendar_event_detail_modal.html",
        {"request": request, **_event_detail_ctx(db, event, current_user.id, year=year, month=month)},
    )


@router.get("/ui/calendario/events/{event_id}/edit", response_class=HTMLResponse)
def ui_event_edit(
    request: Request,
    event_id: str,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    event = _load_event(db, event_id, current_user.id)
    if event.source != "internal":
        raise HTTPException(status_code=403, detail="Eventos do Google Agenda não podem ser editados aqui.")
    tz = event.timezone
    start_local = utc_to_local(event.start_utc, tz)
    end_local = utc_to_local(event.end_utc, tz)
    return templates.TemplateResponse(
        "_calendar_event_modal.html",
        {
            "request": request,
            "mode": "edit",
            "event": event,
            "date_value": start_local.strftime("%Y-%m-%d"),
            "start_value": start_local.strftime("%H:%M"),
            "end_value": end_local.strftime("%H:%M"),
            "title_value": event.title,
            "description_value": event.description,
            "target_calendar_value": event.calendar_id or "",
            "google_calendars": [],
            "linked_calendar": db.get(Calendar, event.calendar_id) if event.calendar_id else None,
            "year": year,
            "month": month,
            "form_error": None,
        },
    )


@router.get("/ui/calendario/events/{event_id}/delete-confirm", response_class=HTMLResponse)
def ui_event_delete_confirm(
    request: Request,
    event_id: str,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    event = _load_event(db, event_id, current_user.id)
    if event.source != "internal":
        raise HTTPException(status_code=403, detail="Eventos do Google Agenda não podem ser excluídos aqui.")
    is_linked = bool(event.calendar_id and event.external_id)
    return templates.TemplateResponse(
        "_calendar_confirm_delete.html",
        {
            "request": request,
            "event": event,
            "is_linked": is_linked,
            "linked_calendar": db.get(Calendar, event.calendar_id) if is_linked else None,
            "year": year,
            "month": month,
        },
    )


@router.post("/ui/calendario/events", response_class=HTMLResponse)
async def ui_event_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    date_str: str = Form(..., alias="date"),
    start_time: str = Form(...),
    end_time: str = Form(...),
    target_calendar_id: str = Form(""),
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    try:
        start_local = _parse_local_dt(date_str, start_time)
        end_local = _parse_local_dt(date_str, end_time)
        await calendar_service.create_internal_event(
            db, user_id=current_user.id, title=title, description=description, start_local=start_local,
            end_local=end_local, timezone_name=app_settings.user_timezone(current_user),
            target_calendar_id=target_calendar_id or None,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            "_calendar_event_modal.html",
            {
                "request": request, "mode": "create", "event": None, "date_value": date_str,
                "start_value": start_time, "end_value": end_time, "title_value": title,
                "description_value": description, "target_calendar_value": target_calendar_id,
                "google_calendars": _google_target_calendars(db, current_user.id), "linked_calendar": None,
                "year": year, "month": month, "form_error": str(exc),
            },
        )
    return templates.TemplateResponse(
        "_calendar_month_grid.html",
        {"request": request, **_grid_ctx(db, current_user.id, year, month, app_settings.user_timezone(current_user), oob=True)},
    )


@router.post("/ui/calendario/events/{event_id}", response_class=HTMLResponse)
async def ui_event_update(
    request: Request,
    event_id: str,
    title: str = Form(...),
    description: str = Form(""),
    date_str: str = Form(..., alias="date"),
    start_time: str = Form(...),
    end_time: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    event = _load_event(db, event_id, current_user.id)
    try:
        start_local = _parse_local_dt(date_str, start_time)
        end_local = _parse_local_dt(date_str, end_time)
        await calendar_service.update_internal_event(
            db, event_id, user_id=current_user.id, title=title, description=description, start_local=start_local,
            end_local=end_local, timezone_name=event.timezone,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            "_calendar_event_modal.html",
            {
                "request": request, "mode": "edit", "event": event, "date_value": date_str,
                "start_value": start_time, "end_value": end_time, "title_value": title,
                "description_value": description, "target_calendar_value": event.calendar_id or "",
                "google_calendars": [], "linked_calendar": db.get(Calendar, event.calendar_id) if event.calendar_id else None,
                "year": year, "month": month, "form_error": str(exc),
            },
        )
    return templates.TemplateResponse(
        "_calendar_month_grid.html",
        {"request": request, **_grid_ctx(db, current_user.id, year, month, app_settings.user_timezone(current_user), oob=True)},
    )


@router.post("/ui/calendario/events/{event_id}/delete", response_class=HTMLResponse)
async def ui_event_delete(
    request: Request,
    event_id: str,
    year: int = Form(...),
    month: int = Form(...),
    also_delete_google: bool = Form(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    try:
        ok = await calendar_service.delete_internal_event(
            db, event_id, user_id=current_user.id, also_delete_google=also_delete_google
        )
    except ValidationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    return templates.TemplateResponse(
        "_calendar_month_grid.html",
        {"request": request, **_grid_ctx(db, current_user.id, year, month, app_settings.user_timezone(current_user), oob=True)},
    )


# --------------------------------------------------------------------------- #
# Automação: criar / editar / remover (modal flutuante)
# --------------------------------------------------------------------------- #
def _resolve_waha_session(db: Session, user_id: str, whatsapp_session_id: str | None) -> str | None:
    """Sessão explicitamente escolhida no seletor "Enviar através de"; sem
    escolha (GET inicial do modal), cai pra conexão mais antiga só como
    conveniência de pré-seleção (nunca lido de volta como fonte de verdade,
    ver `whatsapp_service.primary_session`)."""
    if whatsapp_session_id:
        session = whatsapp_service.get_session(db, whatsapp_session_id, user_id)
    else:
        session = whatsapp_service.primary_session(db, user_id)
    return session.session_name if session else None


@router.get("/ui/calendario/contacts", response_class=HTMLResponse)
async def ui_calendario_contacts(
    request: Request,
    whatsapp_session_id: str = Query(""),
    prefill_id: list[str] = Query([]),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    """Lista de contatos do popover de destinatário — carregada à parte do
    resto do modal (v1.3): é a única coisa no modal de automação que depende
    de uma chamada de rede ao WAHA, então abrir "Adicionar automação" nunca
    deveria esperar por ela. `_calendar_automation_modal.html` só dispara
    isto via `hx-trigger="load"` DEPOIS que o modal (instantâneo, só banco)
    já apareceu inteiro na tela."""
    session_name = _resolve_waha_session(db, current_user.id, whatsapp_session_id)
    if session_name is None:
        ctx = {"contacts": [], "contacts_error": "Conecte um WhatsApp em /configuracoes?tab=conexoes para importar contatos."}
    else:
        ctx = await _contacts_ctx(request, session_name)
    return templates.TemplateResponse(
        "_contact_options.html", {"request": request, "prefill_ids": prefill_id, **ctx}
    )


@router.get("/ui/calendario/events/{event_id}/similar-events", response_class=HTMLResponse)
def ui_calendario_similar_events(
    request: Request,
    event_id: str,
    repeat_choice: str = Query("nao"),
    search: int = Query(0),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    """"Repetir esta automação em eventos iguais?" do modal de automação, em
    dois passos — a varredura de `similar_events` (todos os eventos futuros
    do usuário na janela de sincronização) é cara e a maioria das pessoas
    nunca marca "Sim":

    - `repeat_choice != "sim"`: resposta vazia (limpa a caixa; sem consulta).
    - `repeat_choice == "sim"`, sem `search`: só a caixa, instantânea, já com
      a bolinha de carregamento — e ela mesma dispara o passo seguinte
      (`hx-trigger="load"`), então a caixa aparece ANTES da busca começar.
    - `search=1`: aí sim roda a busca e devolve a lista de datas.

    O seletor dispara esta rota em QUALQUER mudança, com `repeat_choice`
    vindo junto (htmx sempre manda o valor do elemento que disparou) — um
    caminho só, decidido no servidor, sem `onchange` no cliente brigando
    com o listener do htmx por ordem de eventos."""
    event = _load_event(db, event_id, current_user.id)
    if repeat_choice != "sim":
        return HTMLResponse("")
    if not search:
        return templates.TemplateResponse("_similar_events_box.html", {"request": request, "event": event})
    similar = calendar_service.similar_events(db, event, current_user.id)
    return templates.TemplateResponse(
        "_similar_events_checklist.html",
        {
            "request": request,
            "similar_events": [
                {"event": e, "start_local": utc_to_local(e.start_utc, e.timezone)} for e in similar
            ],
        },
    )


@router.get("/ui/calendario/events/{event_id}/automation/new", response_class=HTMLResponse)
def ui_automation_new(
    request: Request,
    event_id: str,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    event = _load_event(db, event_id, current_user.id)
    ctx = _automation_modal_ctx(db, event, user_id=current_user.id, year=year, month=month)
    return templates.TemplateResponse(
        "_calendar_automation_modal.html", {"request": request, "form_error": None, **ctx}
    )


@router.get("/ui/calendario/automations/{automation_id}/edit", response_class=HTMLResponse)
def ui_automation_edit(
    request: Request,
    automation_id: str,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise HTTPException(status_code=404, detail="Automação não encontrada.")
    event = _load_event(db, automation.event_id, current_user.id)
    ctx = _automation_modal_ctx(db, event, user_id=current_user.id, year=year, month=month, automation_id=automation_id)
    return templates.TemplateResponse(
        "_calendar_automation_modal.html", {"request": request, "form_error": None, **ctx}
    )


@router.get("/ui/calendario/events/{event_id}/automation-preview", response_class=HTMLResponse)
def ui_automation_preview(
    request: Request,
    event_id: str,
    offset_direction: str = Query("before"),
    offset_interval: str = Query(""),
    custom_interval: str = Query(""),
    custom_time: str = Query(""),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    """Horário calculado do disparo — pelo MESMO cálculo (`timing.py`) que grava o
    agendamento, então o que aparece aqui é exatamente o que vai ser salvo."""
    event = _load_event(db, event_id, current_user.id)
    user_tz = app_settings.user_timezone(current_user)
    ctx: dict = {"request": request, "error": None, "field_error": None}
    try:
        rule = timing.build_offset_rule(offset_direction, offset_interval, custom_interval, custom_time)
    except ValidationError as exc:
        in_custom_interval = offset_direction in ("before", "after") and offset_interval == timing.CUSTOM_INTERVAL_VALUE
        if in_custom_interval:
            # O erro aparece embaixo do campo (só depois que a pessoa começou a digitar);
            # o preview só avisa que falta o intervalo.
            ctx.update(error="informe o intervalo", field_error=str(exc) if custom_interval.strip() else None)
        else:
            ctx.update(error=str(exc))
        return templates.TemplateResponse("_calendar_automation_preview.html", ctx)
    event_tz = event.timezone or user_tz
    target_utc = timing.target_utc_for_rule(event.start_utc, rule, event_timezone=event_tz)
    target_local = utc_to_local(target_utc, event_tz)
    if rule.direction == "at":
        rule_line = f"{timing.DIRECTION_LABELS['at']} · {target_local.strftime('%H:%M')}"
    elif rule.direction == "custom":
        rule_line = f"Horário fixo · {timing.describe_rule(rule)}"
    else:
        rule_line = f"{timing.DIRECTION_LABELS[rule.direction]} · {timing.describe_rule(rule)} · {target_local.strftime('%H:%M')}"
    warning = None
    if rule.direction == "custom" and target_utc > event.start_utc:
        warning = "O horário personalizado está depois do horário do evento."
    elif target_utc < calendar_service.utcnow():
        warning = "Esse horário já passou."
    ctx.update(
        target_local=target_local,
        rule_line=rule_line,
        warning=warning,
        tz_note=f"fuso do evento: {timing.tz_label(event_tz)}" if event_tz != user_tz else None,
    )
    return templates.TemplateResponse("_calendar_automation_preview.html", ctx)


@router.post("/ui/calendario/events/{event_id}/automation", response_class=HTMLResponse)
async def ui_automation_create(
    request: Request,
    event_id: str,
    recipients: list[str] = Form([]),
    recipient_names: list[str] = Form([]),
    messages: list[str] = Form([]),
    offset_interval: str = Form(""),
    offset_direction: str = Form(...),
    custom_interval: str = Form(""),
    custom_time: str = Form(""),
    whatsapp_session_id: str = Form(""),
    apply_to_event_ids: list[str] = Form([]),
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    event = _load_event(db, event_id, current_user.id)
    wa_session = whatsapp_service.get_session(db, whatsapp_session_id, current_user.id)
    user_tz = app_settings.user_timezone(current_user)
    picked = pair_recipients(recipients, recipient_names)
    try:
        if wa_session is None:
            raise ValidationError("Escolha por qual WhatsApp esta automação deve enviar.")
        await whatsapp_service.require_session_ready(_waha(request), wa_session)
        rule = timing.build_offset_rule(offset_direction, offset_interval, custom_interval, custom_time)
        # Recalcula quem é "igual" a este evento no servidor — nunca confia
        # nos ids que o formulário mandou (poderiam ter sido adulterados pra
        # apontar pro evento de outro usuário).
        selected_ids = set(apply_to_event_ids)

        def _create_for_all_targets() -> None:
            # A varredura de "eventos iguais" só roda se o usuário marcou
            # algum (o padrão é "Não repetir") e, quando roda, também fica
            # aqui dentro da thread — não na coroutine.
            target_events = [event]
            if selected_ids:
                target_events += [
                    e for e in calendar_service.similar_events(db, event, current_user.id) if e.id in selected_ids
                ]
            # "Repetir esta automação" pode significar dezenas de eventos
            # (ex.: uma aula recorrente semanal já com um ano de ocorrências).
            # Cada create_event_automation faz vários commits no SQLite; feito
            # direto na coroutine, isso bloquearia o único event loop do
            # processo (nada mais responde — nem o poll da sidebar, nem outro
            # usuário) pelo tempo inteiro da soma de todos. `asyncio.to_thread`
            # tira esse trabalho síncrono do event loop, mesmo padrão que
            # `scheduler.materialize_due` já usa. O mesmo `db` (SQLite com
            # `check_same_thread=False`, ver db.py) é reaproveitado — chamado
            # de forma sequencial, nunca concorrente, então é seguro.
            for target in target_events:
                calendar_service.create_event_automation(
                    db, event_id=target.id, user_id=current_user.id, waha_session=wa_session.session_name,
                    recipients=[p["value"] for p in picked], recipient_names=[p["label"] for p in picked],
                    messages=messages, offset_amount=rule.amount, offset_unit=rule.unit,
                    offset_direction=rule.direction, custom_time_local=rule.custom_time_local,
                    custom_interval=rule.custom_interval, timezone_name=user_tz,
                )

        await asyncio.to_thread(_create_for_all_targets)
    except ValidationError as exc:
        form_values = _submitted_form_values(
            recipients, recipient_names, messages, whatsapp_session_id,
            offset_direction, offset_interval, custom_interval, custom_time,
        )
        ctx = _automation_modal_ctx(
            db, event, user_id=current_user.id, year=year, month=month, form_values=form_values
        )
        return templates.TemplateResponse(
            "_calendar_automation_modal.html", {"request": request, "form_error": str(exc), **ctx}
        )
    return templates.TemplateResponse(
        "_calendar_month_grid.html",
        {"request": request, **_grid_ctx(db, current_user.id, year, month, user_tz, oob=True)},
    )


@router.post("/ui/calendario/automations/{automation_id}", response_class=HTMLResponse)
async def ui_automation_update(
    request: Request,
    automation_id: str,
    recipients: list[str] = Form([]),
    recipient_names: list[str] = Form([]),
    messages: list[str] = Form([]),
    offset_interval: str = Form(""),
    offset_direction: str = Form(...),
    custom_interval: str = Form(""),
    custom_time: str = Form(""),
    whatsapp_session_id: str = Form(""),
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise HTTPException(status_code=404, detail="Automação não encontrada.")
    event = _load_event(db, automation.event_id, current_user.id)
    wa_session = whatsapp_service.get_session(db, whatsapp_session_id, current_user.id)
    user_tz = app_settings.user_timezone(current_user)
    picked = pair_recipients(recipients, recipient_names)
    try:
        if wa_session is None:
            raise ValidationError("Escolha por qual WhatsApp esta automação deve enviar.")
        await whatsapp_service.require_session_ready(_waha(request), wa_session)
        rule = timing.build_offset_rule(offset_direction, offset_interval, custom_interval, custom_time)
        await asyncio.to_thread(
            calendar_service.update_event_automation,
            db, automation_id, user_id=current_user.id, waha_session=wa_session.session_name,
            recipients=[p["value"] for p in picked], recipient_names=[p["label"] for p in picked],
            messages=messages, offset_amount=rule.amount, offset_unit=rule.unit,
            offset_direction=rule.direction, custom_time_local=rule.custom_time_local,
            custom_interval=rule.custom_interval, timezone_name=user_tz,
        )
    except ValidationError as exc:
        form_values = _submitted_form_values(
            recipients, recipient_names, messages, whatsapp_session_id,
            offset_direction, offset_interval, custom_interval, custom_time,
        )
        ctx = _automation_modal_ctx(
            db, event, user_id=current_user.id, year=year, month=month, automation_id=automation_id,
            form_values=form_values,
        )
        return templates.TemplateResponse(
            "_calendar_automation_modal.html", {"request": request, "form_error": str(exc), **ctx}
        )
    return templates.TemplateResponse(
        "_calendar_month_grid.html",
        {"request": request, **_grid_ctx(db, current_user.id, year, month, user_tz, oob=True)},
    )


@router.post("/ui/calendario/automations/{automation_id}/remove", response_class=HTMLResponse)
def ui_automation_remove(
    request: Request,
    automation_id: str,
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise HTTPException(status_code=404, detail="Automação não encontrada.")
    _load_event(db, automation.event_id, current_user.id)  # 404 se o evento pai não for do usuário
    calendar_service.remove_event_automation(db, automation_id, current_user.id)
    return templates.TemplateResponse(
        "_calendar_month_grid.html",
        {"request": request, **_grid_ctx(db, current_user.id, year, month, app_settings.user_timezone(current_user), oob=True)},
    )
