"""UI web da página Configurações: "Calendários conectados" (Google Agenda) e
"Preferências" (fuso horário global)."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlmodel import Session

from .. import app_settings, calendar_service
from ..calendar_providers.base import CalendarProviderError
from ..clock import utcnow
from ..config import settings
from ..db import get_session
from ..recurrence import utc_to_local
from ..service import ValidationError
from .routes import _session_ctx, templates

router = APIRouter(tags=["ui-configuracoes"])

_STATE_COOKIE = "google_oauth_state"

# Fusos comuns pro seletor de Preferências — qualquer outro pode ser digitado
# no campo de texto livre ao lado (validado contra ZoneInfo no servidor).
COMMON_TIMEZONES = [
    ("America/Sao_Paulo", "(GMT-03:00) São Paulo — America/Sao_Paulo"),
    ("America/Manaus", "(GMT-04:00) Manaus — America/Manaus"),
    ("America/Rio_Branco", "(GMT-05:00) Rio Branco — America/Rio_Branco"),
    ("America/New_York", "(GMT-05:00) Nova York — America/New_York"),
    ("America/Los_Angeles", "(GMT-08:00) Los Angeles — America/Los_Angeles"),
    ("Europe/Lisbon", "(GMT+00:00) Lisboa — Europe/Lisbon"),
    ("Europe/London", "(GMT+00:00) Londres — Europe/London"),
    ("UTC", "(GMT+00:00) UTC"),
    ("Asia/Tokyo", "(GMT+09:00) Tóquio — Asia/Tokyo"),
]


def _ctx(request: Request, **extra: object) -> dict:
    return {"request": request, "nav": "configuracoes", "waha_session": settings.waha_session, **extra}


def _connections_ctx(db: Session) -> dict:
    connections = []
    for connection in calendar_service.list_connections(db):
        connections.append(
            {
                "connection": connection,
                "calendars": calendar_service.list_calendars(db, connection.id),
                "has_write_scope": calendar_service.connection_has_write_scope(connection),
            }
        )
    return {
        "connections": connections,
        "missing_config": calendar_service.missing_config(),
        "default_timezone": settings.default_timezone,
    }


def _preferences_ctx(*, pref_ok: str | None = None, pref_error: str | None = None) -> dict:
    now_local = utc_to_local(utcnow(), settings.default_timezone)
    return {
        "current_timezone": settings.default_timezone,
        "common_timezones": COMMON_TIMEZONES,
        "now_local": now_local,
        "pref_ok": pref_ok,
        "pref_error": pref_error,
    }


@router.get("/configuracoes", response_class=HTMLResponse)
async def page_configuracoes(
    request: Request,
    ok: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "configuracoes.html",
        {
            **_ctx(request), "ok": ok, "error": error, **_connections_ctx(db),
            **_preferences_ctx(), **(await _session_ctx(request)),
        },
    )


@router.get("/ui/configuracoes/connections", response_class=HTMLResponse)
def ui_connections(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    return templates.TemplateResponse("_connections.html", {"request": request, **_connections_ctx(db)})


@router.post("/configuracoes/preferencias/timezone", response_class=HTMLResponse)
def ui_set_timezone(
    request: Request,
    timezone_name: str = Form(""),
    custom_timezone: str = Form(""),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    tz_name = (custom_timezone or timezone_name).strip()
    try:
        app_settings.set_timezone(db, tz_name)
    except ValidationError as exc:
        return templates.TemplateResponse(
            "_preferences.html", {"request": request, **_preferences_ctx(pref_error=str(exc))}
        )
    return templates.TemplateResponse(
        "_preferences.html",
        {"request": request, **_preferences_ctx(pref_ok=f"Fuso horário atualizado para {tz_name}.")},
    )


@router.get("/ui/configuracoes/relogio", response_class=PlainTextResponse)
def ui_clock() -> str:
    return utc_to_local(utcnow(), settings.default_timezone).strftime("%d/%m/%Y — %H:%M:%S")


@router.post("/configuracoes/google/connect")
def connect_google() -> RedirectResponse:
    try:
        authorize_url, state = calendar_service.start_connect("google")
    except calendar_service.NotConfiguredError as exc:
        return RedirectResponse(url="/configuracoes?error=" + quote(str(exc)), status_code=303)
    resp = RedirectResponse(url=authorize_url, status_code=302)
    resp.set_cookie(_STATE_COOKIE, state, max_age=600, httponly=True, samesite="lax")
    return resp


@router.get("/calendario/oauth/callback")
async def google_oauth_callback(
    request: Request,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_session),
) -> RedirectResponse:
    if error:
        return RedirectResponse(url="/configuracoes?error=" + quote(f"Google recusou: {error}"), status_code=303)

    expected_state = request.cookies.get(_STATE_COOKIE)
    if not state or not expected_state or state != expected_state:
        return RedirectResponse(
            url="/configuracoes?error=" + quote("Estado OAuth inválido (state). Tente conectar de novo."),
            status_code=303,
        )
    if not code:
        return RedirectResponse(url="/configuracoes?error=" + quote("Código OAuth ausente."), status_code=303)

    try:
        connection = await calendar_service.finish_connect(db, provider_key="google", code=code)
    except (calendar_service.NotConfiguredError, CalendarProviderError) as exc:
        resp = RedirectResponse(url="/configuracoes?error=" + quote(str(exc)), status_code=303)
        resp.delete_cookie(_STATE_COOKIE)
        return resp

    resp = RedirectResponse(
        url="/configuracoes?ok=" + quote(f"Conta conectada: {connection.account_identifier}."), status_code=303
    )
    resp.delete_cookie(_STATE_COOKIE)
    return resp


@router.post("/ui/configuracoes/calendars/{calendar_id}/toggle", response_class=HTMLResponse)
def ui_toggle_calendar(
    request: Request,
    calendar_id: str,
    enabled: bool = Query(...),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    calendar_service.set_calendar_enabled(db, calendar_id, enabled)
    return templates.TemplateResponse("_connections.html", {"request": request, **_connections_ctx(db)})


@router.post("/ui/configuracoes/connections/{connection_id}/sync", response_class=HTMLResponse)
async def ui_sync_now(request: Request, connection_id: str, db: Session = Depends(get_session)) -> HTMLResponse:
    await calendar_service.sync_now(db, connection_id)
    return templates.TemplateResponse("_connections.html", {"request": request, **_connections_ctx(db)})


@router.post("/ui/configuracoes/connections/{connection_id}/disconnect", response_class=HTMLResponse)
def ui_disconnect(request: Request, connection_id: str, db: Session = Depends(get_session)) -> HTMLResponse:
    calendar_service.disconnect(db, connection_id)
    return templates.TemplateResponse("_connections.html", {"request": request, **_connections_ctx(db)})
