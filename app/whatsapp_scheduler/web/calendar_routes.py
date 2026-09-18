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

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, col, select

from .. import auth, calendar_service, whatsapp_service
from ..config import settings
from ..db import get_session
from ..models import Automation, AutomationMessage, AutomationSchedule, Calendar, Event, EventSyncStatus, Schedule, User
from ..recurrence import utc_to_local
from ..service import ValidationError
from ..waha import WahaClient, WahaError
from .routes import templates

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


def _current_year_month(year: int | None, month: int | None) -> tuple[int, int]:
    today = utc_to_local(calendar_service.utcnow(), settings.default_timezone).date()
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
    tz = event.timezone or settings.default_timezone
    info = automation_info.get(event.id)
    return {
        "event": event,
        "start_local": utc_to_local(event.start_utc, tz),
        "is_external": event.source != "internal",
        "calendar_key": event.calendar_id or "internal",
        "automation_count": info["count"] if info else 0,
    }


def _grid_ctx(db: Session, user_id: str, year: int, month: int, *, oob: bool = False) -> dict:
    weeks = calendar_service.month_grid(db, user_id, year, month)
    all_event_ids = [e.id for week in weeks for day in week for e in day["events"]]
    automation_info = _automation_summary_map(db, all_event_ids)
    grid = [
        [{**day, "chips": [_event_chip(e, automation_info) for e in day["events"]]} for day in week]
        for week in weeks
    ]
    prev_year, prev_month = _shift_month(year, month, -1)
    next_year, next_month = _shift_month(year, month, 1)
    today = utc_to_local(calendar_service.utcnow(), settings.default_timezone).date()
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


def _load_event(db: Session, event_id: str, user_id: str) -> Event:
    event = db.get(Event, event_id)
    if event is None or event.user_id != user_id:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    return event


def _event_detail_ctx(db: Session, event: Event, user_id: str, *, year: int, month: int) -> dict:
    tz = event.timezone or settings.default_timezone
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


def _parse_interval(offset_interval: str) -> tuple[int, str]:
    """"2 horas" chega do form como um valor só, tipo '2:hours' — o serviço
    (create_event_automation) continua recebendo amount/unit separados."""
    try:
        amount_str, unit = offset_interval.split(":", 1)
        return int(amount_str), unit
    except (ValueError, AttributeError) as exc:
        raise ValidationError(f"Intervalo inválido: {offset_interval!r}") from exc


async def _contacts_ctx(request: Request, waha_session: str) -> dict:
    try:
        contacts = await calendar_service.list_contacts(_waha(request), waha_session)
        return {"contacts": contacts, "contacts_error": None}
    except WahaError as exc:
        return {"contacts": [], "contacts_error": str(exc)}


def _automation_modal_ctx(
    db: Session, event: Event, *, user_id: str, year: int, month: int, automation_id: str | None = None
) -> dict:
    tz = event.timezone or settings.default_timezone
    prefill = None
    selected_whatsapp_session_id = None
    if automation_id:
        automation = db.get(Automation, automation_id)
        if automation is None:
            raise HTTPException(status_code=404, detail="Automação não encontrada.")
        links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation_id)
        ).all()
        schedule_ids = [link.schedule_id for link in links]
        schedules = {
            s.id: s
            for s in (
                db.exec(select(Schedule).where(col(Schedule.id).in_(schedule_ids))).all() if schedule_ids else []
            )
        }
        recipients_seen: dict[str, str] = {}
        for link in links:
            sch = schedules.get(link.schedule_id)
            if sch is not None:
                recipients_seen.setdefault(link.recipient_chat_id, sch.recipient_input)
        messages = db.exec(
            select(AutomationMessage)
            .where(col(AutomationMessage.automation_id) == automation_id)
            .order_by(col(AutomationMessage.position))
        ).all()
        prefill = {
            "automation_id": automation.id,
            "recipient_chat_ids": list(recipients_seen.keys()),
            "recipient_labels": recipients_seen,
            "messages": [m.text for m in messages],
            "offset_amount": automation.offset_amount,
            "offset_unit": str(automation.offset_unit),
            "offset_direction": str(automation.offset_direction),
            "custom_time_local": automation.custom_time_local,
        }
        # Todas as mensagens/destinatários de uma automação sempre usam o
        # mesmo WhatsApp (ver create_event_automation) — basta olhar 1 schedule.
        any_schedule = next(iter(schedules.values()), None)
        if any_schedule is not None:
            existing = whatsapp_service.session_by_name(db, user_id, any_schedule.session)
            selected_whatsapp_session_id = existing.id if existing else None
    return {
        "event": event,
        "start_local": utc_to_local(event.start_utc, tz),
        "year": year,
        "month": month,
        "prefill": prefill,
        "whatsapp_sessions": whatsapp_service.list_sessions(db, user_id),
        "selected_whatsapp_session_id": selected_whatsapp_session_id,
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
    y, m = _current_year_month(year, month)
    return templates.TemplateResponse(
        "calendario.html", {**_ctx(request, current_user), **_grid_ctx(db, current_user.id, y, m)}
    )


@router.get("/ui/calendario/grid", response_class=HTMLResponse)
def ui_grid(
    request: Request,
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "_calendar_month_grid.html", {"request": request, **_grid_ctx(db, current_user.id, year, month)}
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
    tz = event.timezone or settings.default_timezone
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
            end_local=end_local, timezone_name=settings.default_timezone, target_calendar_id=target_calendar_id or None,
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
        "_calendar_month_grid.html", {"request": request, **_grid_ctx(db, current_user.id, year, month, oob=True)}
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
            end_local=end_local, timezone_name=event.timezone or settings.default_timezone,
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
        "_calendar_month_grid.html", {"request": request, **_grid_ctx(db, current_user.id, year, month, oob=True)}
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
        "_calendar_month_grid.html", {"request": request, **_grid_ctx(db, current_user.id, year, month, oob=True)}
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


async def _contacts_for(request: Request, db: Session, user_id: str, whatsapp_session_id: str | None) -> dict:
    session_name = _resolve_waha_session(db, user_id, whatsapp_session_id)
    if session_name is None:
        return {"contacts": [], "contacts_error": "Conecte um WhatsApp em /whatsapps para importar contatos."}
    return await _contacts_ctx(request, session_name)


@router.get("/ui/calendario/events/{event_id}/automation/new", response_class=HTMLResponse)
async def ui_automation_new(
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
        "_calendar_automation_modal.html",
        {
            "request": request, "form_error": None, **ctx,
            **await _contacts_for(request, db, current_user.id, ctx["selected_whatsapp_session_id"]),
        },
    )


@router.get("/ui/calendario/automations/{automation_id}/edit", response_class=HTMLResponse)
async def ui_automation_edit(
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
        "_calendar_automation_modal.html",
        {
            "request": request, "form_error": None, **ctx,
            **await _contacts_for(request, db, current_user.id, ctx["selected_whatsapp_session_id"]),
        },
    )


@router.post("/ui/calendario/events/{event_id}/automation", response_class=HTMLResponse)
async def ui_automation_create(
    request: Request,
    event_id: str,
    recipients: list[str] = Form([]),
    messages: list[str] = Form([]),
    offset_interval: str = Form(...),
    offset_direction: str = Form(...),
    custom_time: str = Form(""),
    whatsapp_session_id: str = Form(""),
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    event = _load_event(db, event_id, current_user.id)
    wa_session = whatsapp_service.get_session(db, whatsapp_session_id, current_user.id)
    try:
        if wa_session is None:
            raise ValidationError("Escolha por qual WhatsApp esta automação deve enviar.")
        offset_amount, offset_unit = _parse_interval(offset_interval)
        calendar_service.create_event_automation(
            db, event_id=event_id, user_id=current_user.id, waha_session=wa_session.session_name,
            recipients=recipients, messages=messages, offset_amount=offset_amount,
            offset_unit=offset_unit, offset_direction=offset_direction, custom_time_local=custom_time or None,
        )
    except ValidationError as exc:
        ctx = _automation_modal_ctx(db, event, user_id=current_user.id, year=year, month=month)
        return templates.TemplateResponse(
            "_calendar_automation_modal.html",
            {
                "request": request, "form_error": str(exc), **ctx,
                **await _contacts_for(request, db, current_user.id, whatsapp_session_id),
            },
        )
    return templates.TemplateResponse(
        "_calendar_month_grid.html", {"request": request, **_grid_ctx(db, current_user.id, year, month, oob=True)}
    )


@router.post("/ui/calendario/automations/{automation_id}", response_class=HTMLResponse)
async def ui_automation_update(
    request: Request,
    automation_id: str,
    recipients: list[str] = Form([]),
    messages: list[str] = Form([]),
    offset_interval: str = Form(...),
    offset_direction: str = Form(...),
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
    try:
        if wa_session is None:
            raise ValidationError("Escolha por qual WhatsApp esta automação deve enviar.")
        offset_amount, offset_unit = _parse_interval(offset_interval)
        calendar_service.update_event_automation(
            db, automation_id, user_id=current_user.id, waha_session=wa_session.session_name,
            recipients=recipients, messages=messages, offset_amount=offset_amount,
            offset_unit=offset_unit, offset_direction=offset_direction, custom_time_local=custom_time or None,
        )
    except ValidationError as exc:
        ctx = _automation_modal_ctx(db, event, user_id=current_user.id, year=year, month=month, automation_id=automation_id)
        return templates.TemplateResponse(
            "_calendar_automation_modal.html",
            {
                "request": request, "form_error": str(exc), **ctx,
                **await _contacts_for(request, db, current_user.id, whatsapp_session_id),
            },
        )
    return templates.TemplateResponse(
        "_calendar_month_grid.html", {"request": request, **_grid_ctx(db, current_user.id, year, month, oob=True)}
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
        "_calendar_month_grid.html", {"request": request, **_grid_ctx(db, current_user.id, year, month, oob=True)}
    )
