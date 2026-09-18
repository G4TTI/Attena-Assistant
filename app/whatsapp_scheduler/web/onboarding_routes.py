"""UI web do onboarding de primeiros passos (v1.3, itens 20-26): WhatsApp ->
Google Agenda -> fuso horário -> concluído. Nenhuma etapa bloqueia o uso do
app (`main._onboarding_gate` só redireciona páginas GET "de humano"; API e
parciais htmx continuam livres) e cada uma pode ser pulada."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from .. import auth, calendar_service, onboarding_service, whatsapp_service
from ..clock import utcnow
from ..db import get_session
from ..models import User
from ..waha import WahaClient, WahaError
from .routes import templates
from .settings_routes import COMMON_TIMEZONES

router = APIRouter(tags=["ui-onboarding"])


def _waha(request: Request) -> WahaClient:
    return request.app.state.waha


async def _ctx(request: Request, db: Session, current_user: User, step: int | None) -> dict:
    state = await onboarding_service.progress(db, _waha(request), current_user)
    return {
        "request": request,
        "current_user": current_user,
        "step": step or onboarding_service.first_incomplete_step(state),
        "common_timezones": COMMON_TIMEZONES,
        "missing_config_google": bool(calendar_service.missing_config()),
        **state,
    }


@router.get("/onboarding", response_class=HTMLResponse)
async def page_onboarding(
    request: Request,
    step: int | None = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    if current_user.onboarding_completed_at is not None:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("onboarding.html", await _ctx(request, db, current_user, step))


@router.get("/ui/onboarding/whatsapp", response_class=HTMLResponse)
async def ui_onboarding_whatsapp(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    return templates.TemplateResponse("_onboarding_whatsapp_step.html", await _ctx(request, db, current_user, 1))


@router.post("/onboarding/whatsapp/start", response_class=HTMLResponse)
async def ui_onboarding_whatsapp_start(
    request: Request,
    phone: str = Form(""),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    phone = phone.strip()
    if phone and phone != current_user.phone:
        current_user.phone = phone
        current_user.updated_at = utcnow()
        db.add(current_user)
        db.commit()

    primary = whatsapp_service.primary_session(db, current_user.id)
    if primary is not None:
        try:
            await _waha(request).restart_session(primary.session_name)
        except WahaError:
            pass
    return templates.TemplateResponse("_onboarding_whatsapp_step.html", await _ctx(request, db, current_user, 1))


@router.post("/onboarding/timezone", response_class=HTMLResponse)
async def ui_onboarding_timezone(
    request: Request,
    timezone_name: str = Form(""),
    custom_timezone: str = Form(""),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    tz_name = (custom_timezone or timezone_name).strip()
    error = None
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        error = f"Timezone inválida: {tz_name!r}"
    if error is None:
        current_user.timezone = tz_name
        current_user.updated_at = utcnow()
        db.add(current_user)
        db.commit()
        return templates.TemplateResponse("onboarding.html", await _ctx(request, db, current_user, 4))
    ctx = await _ctx(request, db, current_user, 3)
    ctx["tz_error"] = error
    return templates.TemplateResponse("onboarding.html", ctx)


@router.get("/onboarding/pular", response_class=HTMLResponse)
async def ui_onboarding_skip(
    request: Request,
    step: int = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    return templates.TemplateResponse("onboarding.html", await _ctx(request, db, current_user, step + 1))


@router.post("/onboarding/finish")
def ui_onboarding_finish(
    db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> RedirectResponse:
    onboarding_service.finish(db, current_user)
    return RedirectResponse(url="/", status_code=303)
