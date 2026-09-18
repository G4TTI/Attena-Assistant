"""UI web da página Configurações: "Minha conta" (perfil/segurança), "Calendários
conectados" (Google Agenda) e "Preferências" (fuso horário do próprio usuário —
ver `app_settings.user_timezone`, Parte 35)."""

from __future__ import annotations

from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlmodel import Session

from .. import app_settings, auth, auth_service, calendar_service, time_sync, whatsapp_service
from ..calendar_providers.base import CalendarProviderError
from ..clock import utcnow
from ..db import get_session
from ..models import User
from ..recurrence import utc_to_local
from ..service import ValidationError
from .routes import templates

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


def _ctx(request: Request, current_user: User, **extra: object) -> dict:
    return {
        "request": request,
        "nav": "configuracoes",
        "current_user": current_user,
        **extra,
    }


async def _whatsapp_ctx(request: Request, db: Session, user_id: str) -> dict:
    sessions = whatsapp_service.list_sessions(db, user_id)
    return {"rows": await whatsapp_service.status_rows(request.app.state.waha, sessions)}


def _connections_ctx(db: Session, user_id: str, tz_name: str) -> dict:
    connections = []
    for connection in calendar_service.list_connections(db, user_id):
        connections.append(
            {
                "connection": connection,
                "calendars": calendar_service.list_calendars(db, connection.id, user_id),
                "has_write_scope": calendar_service.connection_has_write_scope(connection),
            }
        )
    return {
        "connections": connections,
        "missing_config": calendar_service.missing_config(),
        "default_timezone": tz_name,
    }


def _preferences_ctx(current_user: User, *, pref_ok: str | None = None, pref_error: str | None = None) -> dict:
    tz_name = app_settings.user_timezone(current_user)
    now_local = utc_to_local(utcnow(), tz_name)
    clock_synced_at_local = utc_to_local(time_sync.last_synced_at, tz_name) if time_sync.last_synced_at else None
    return {
        "current_timezone": tz_name,
        "common_timezones": COMMON_TIMEZONES,
        "now_local": now_local,
        "clock_synced_at_local": clock_synced_at_local,
        "clock_sync_error": time_sync.last_sync_error,
        "pref_ok": pref_ok,
        "pref_error": pref_error,
    }


@router.get("/configuracoes", response_class=HTMLResponse)
async def page_configuracoes(
    request: Request,
    ok: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    tz_name = app_settings.user_timezone(current_user)
    return templates.TemplateResponse(
        "configuracoes.html",
        {
            **_ctx(request, current_user), "ok": ok, "error": error, **_connections_ctx(db, current_user.id, tz_name),
            **_preferences_ctx(current_user), **(await _whatsapp_ctx(request, db, current_user.id)),
        },
    )


@router.get("/ui/configuracoes/connections", response_class=HTMLResponse)
def ui_connections(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    tz_name = app_settings.user_timezone(current_user)
    return templates.TemplateResponse(
        "_connections.html", {"request": request, **_connections_ctx(db, current_user.id, tz_name)}
    )


@router.post("/configuracoes/preferencias/timezone", response_class=HTMLResponse)
def ui_set_timezone(
    request: Request,
    timezone_name: str = Form(""),
    custom_timezone: str = Form(""),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    tz_name = (custom_timezone or timezone_name).strip()
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return templates.TemplateResponse(
            "_preferences.html",
            {"request": request, **_preferences_ctx(current_user, pref_error=f"Timezone inválida: {tz_name!r}")},
        )
    current_user.timezone = tz_name
    current_user.updated_at = utcnow()
    db.add(current_user)
    db.commit()
    return templates.TemplateResponse(
        "_preferences.html",
        {"request": request, **_preferences_ctx(current_user, pref_ok=f"Fuso horário atualizado para {tz_name}.")},
    )


@router.get("/ui/configuracoes/relogio", response_class=PlainTextResponse)
def ui_clock(current_user: User = Depends(auth.require_user_web)) -> str:
    return utc_to_local(utcnow(), app_settings.user_timezone(current_user)).strftime("%d/%m/%Y — %H:%M:%S")


@router.post("/configuracoes/google/connect")
def connect_google(current_user: User = Depends(auth.require_user_web)) -> RedirectResponse:
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
    current_user: User = Depends(auth.require_user_web),
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
        connection = await calendar_service.finish_connect(
            db, provider_key="google", code=code, user_id=current_user.id
        )
    except (calendar_service.NotConfiguredError, CalendarProviderError) as exc:
        resp = RedirectResponse(url="/configuracoes?error=" + quote(str(exc)), status_code=303)
        resp.delete_cookie(_STATE_COOKIE)
        return resp

    auth_service.log_event(
        db, auth_service.AuditEventType.google_connected, user_id=current_user.id, request=request
    )
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
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    calendar_service.set_calendar_enabled(db, calendar_id, enabled, current_user.id)
    return templates.TemplateResponse(
        "_connections.html",
        {"request": request, **_connections_ctx(db, current_user.id, app_settings.user_timezone(current_user))},
    )


@router.post("/ui/configuracoes/connections/{connection_id}/sync", response_class=HTMLResponse)
async def ui_sync_now(
    request: Request,
    connection_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    await calendar_service.sync_now(db, connection_id, current_user.id)
    return templates.TemplateResponse(
        "_connections.html",
        {"request": request, **_connections_ctx(db, current_user.id, app_settings.user_timezone(current_user))},
    )


@router.post("/ui/configuracoes/connections/{connection_id}/disconnect", response_class=HTMLResponse)
def ui_disconnect(
    request: Request,
    connection_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    if calendar_service.disconnect(db, connection_id, current_user.id):
        auth_service.log_event(
            db, auth_service.AuditEventType.google_disconnected, user_id=current_user.id, request=request
        )
    return templates.TemplateResponse(
        "_connections.html",
        {"request": request, **_connections_ctx(db, current_user.id, app_settings.user_timezone(current_user))},
    )


# --------------------------------------------------------------------------- #
# Minha conta: dados pessoais, senha, sessões
# --------------------------------------------------------------------------- #
@router.post("/configuracoes/conta/perfil", response_class=HTMLResponse)
def ui_update_profile(
    request: Request,
    name: str = Form(...),
    phone: str = Form(""),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> RedirectResponse:
    name = name.strip()
    if not name:
        return RedirectResponse(url="/configuracoes?error=" + quote("Informe seu nome."), status_code=303)
    current_user.name = name
    current_user.phone = phone.strip() or None
    current_user.updated_at = utcnow()
    db.add(current_user)
    db.commit()
    return RedirectResponse(url="/configuracoes?ok=" + quote("Dados atualizados."), status_code=303)


@router.post("/configuracoes/conta/senha", response_class=HTMLResponse)
def ui_change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> RedirectResponse:
    try:
        auth_service.change_password(
            db,
            current_user,
            current_password=current_password,
            new_password=new_password,
            new_password_confirm=new_password_confirm,
        )
    except ValidationError as exc:
        return RedirectResponse(url="/configuracoes?error=" + quote(str(exc)), status_code=303)
    return RedirectResponse(url="/configuracoes?ok=" + quote("Senha alterada."), status_code=303)


@router.post("/configuracoes/conta/sair-outros-dispositivos", response_class=HTMLResponse)
def ui_logout_other_sessions(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> RedirectResponse:
    current_session = auth.get_current_session(request, db)
    keep_id = current_session.id if current_session is not None else ""
    count = auth.revoke_other_sessions(db, current_user, keep_session_id=keep_id)
    return RedirectResponse(
        url="/configuracoes?ok=" + quote(f"{count} outra(s) sessão(ões) encerrada(s)."), status_code=303
    )
