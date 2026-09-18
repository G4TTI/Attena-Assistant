"""UI web da página Dashboard: resumo operacional (eventos, disparos,
status do WhatsApp/Google Agenda, atividade recente). Só leitura + ações
que já existem em outras páginas (reconectar sessão, sincronizar
calendário) — a lógica de negócio mora em `dashboard_service.py` e nos
serviços já existentes (`calendar_service`, `Schedule`/`Dispatch`). Tudo
sempre filtrado pelo usuário autenticado (Parte 33 — números do Dashboard
não podem misturar contas)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from .. import auth, calendar_service, dashboard_service, whatsapp_service
from ..config import settings
from ..db import get_session
from ..models import Event, User
from ..recurrence import utc_to_local
from .routes import templates

router = APIRouter(tags=["ui-dashboard"])

templates.env.filters["reltime"] = dashboard_service.relative_label

# strftime('%B') depende de locale (ver mesma observação em calendar_routes.py).
_MONTHS_PT_LOWER = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _format_date_long_pt(d: date) -> str:
    return f"{d.day} de {_MONTHS_PT_LOWER[d.month - 1]} de {d.year}"


def _greeting_name(whatsapp_rows: list[dict]) -> str | None:
    """Primeiro nome do perfil da primeira conexão WhatsApp conectada
    (session.me.pushName) — dado real da sessão WAHA, não um nome fixo."""
    for row in whatsapp_rows:
        info = row.get("status")
        if not isinstance(info, dict):
            continue
        me = info.get("me")
        push_name = me.get("pushName") if isinstance(me, dict) else None
        if isinstance(push_name, str) and push_name.strip():
            return push_name.strip().split(" ")[0]
    return None


def _event_row(event: Event) -> dict:
    tz = event.timezone or settings.default_timezone
    local = utc_to_local(event.start_utc, tz)
    return {"event": event, "local": local, "year": local.year, "month": local.month}


async def _summary_ctx(request: Request, db: Session, current_user: User) -> dict:
    """Tudo que é dinâmico no Dashboard — cards, listas e os cards de status
    (WhatsApp/Google Agenda). Usado tanto no primeiro load quanto no poll de
    30s (`/ui/dashboard/summary`), pra status refletir o estado atual sem
    precisar de um mecanismo de push separado."""
    user_id = current_user.id
    today = dashboard_service.today_local_date()
    today_events = dashboard_service.today_events(db, user_id, today=today)
    scheduled = dashboard_service.scheduled_dispatches(db, user_id)
    sent_today = dashboard_service.sent_count_on(db, user_id, today)
    sent_yesterday = dashboard_service.sent_count_on(db, user_id, today - timedelta(days=1))
    failed_today = dashboard_service.failed_count_on(db, user_id, today)
    next_dispatch = scheduled[0] if scheduled else None
    next_upcoming = dashboard_service.upcoming_events(db, user_id, limit=1)

    sent_change_pct = None
    if sent_yesterday > 0:
        sent_change_pct = round((sent_today - sent_yesterday) / sent_yesterday * 100)

    return {
        "today_events_count": len(today_events),
        "today_events_upcoming_count": dashboard_service.upcoming_today_count(today_events),
        "scheduled_count": len(scheduled),
        "next_dispatch_local": (
            utc_to_local(next_dispatch.scheduled_at_utc, settings.default_timezone) if next_dispatch else None
        ),
        "sent_today_count": sent_today,
        "sent_change_pct": sent_change_pct,
        "failed_today_count": failed_today,
        "upcoming_events": [_event_row(e) for e in dashboard_service.upcoming_events(db, user_id, limit=5)],
        "upcoming_dispatches": dashboard_service.upcoming_dispatch_rows(db, user_id, limit=5),
        "recent_activity": dashboard_service.recent_activity(db, user_id, limit=6),
        "today_date": today.isoformat(),
        "cal_year": today.year,
        "cal_month": today.month,
        "next_event_for_automation": _event_row(next_upcoming[0]) if next_upcoming else None,
        "connection": dashboard_service.primary_calendar_connection(db, user_id),
        "whatsapp_rows": await whatsapp_service.status_rows(
            request.app.state.waha, whatsapp_service.list_sessions(db, user_id)
        ),
    }


@router.get("/", response_class=HTMLResponse)
async def page_dashboard(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    today = dashboard_service.today_local_date()
    summary = await _summary_ctx(request, db, current_user)
    ctx = {
        "request": request,
        "nav": "dashboard",
        "current_user": current_user,
        "today_label": _format_date_long_pt(today),
        "greeting_name": _greeting_name(summary.get("whatsapp_rows", [])),
        **summary,
    }
    return templates.TemplateResponse("dashboard.html", ctx)


@router.get("/ui/dashboard/summary", response_class=HTMLResponse)
async def ui_dashboard_summary(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    return templates.TemplateResponse(
        "_dashboard_summary.html", {"request": request, **(await _summary_ctx(request, db, current_user))}
    )


@router.post("/ui/dashboard/calendar-card/sync", response_class=HTMLResponse)
async def ui_dashboard_calendar_sync(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    connection = dashboard_service.primary_calendar_connection(db, current_user.id)
    if connection is not None:
        await calendar_service.sync_now(db, connection.id, current_user.id)
    return templates.TemplateResponse(
        "_dashboard_calendar_card.html",
        {"request": request, "connection": dashboard_service.primary_calendar_connection(db, current_user.id)},
    )
