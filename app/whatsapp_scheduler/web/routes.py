"""UI web (Jinja2 + htmx, sem build step)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, select

from .. import app_settings, auth, whatsapp_service
from ..chatsvc import get_history, list_chats, send_now
from ..db import get_session
from ..models import Dispatch, Schedule, User
from ..recurrence import utc_to_local
from ..service import ValidationError, cancel_schedule, create_schedule, run_now
from ..waha import WahaError

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _localtime(dt: datetime | None, tz: str) -> str:
    if not isinstance(dt, datetime):
        return "—"
    return utc_to_local(dt, tz).strftime("%d/%m/%Y %H:%M")


templates.env.filters["localtime"] = _localtime


_STATUS_LABELS = {
    "pending": "pendente",
    "processing": "processando",
    "sent": "enviado",
    "failed": "falhou",
    "canceled": "cancelado",
    "skipped": "ignorado",
}


def _status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


templates.env.filters["status_label"] = _status_label


def _engine_label(session: dict | None) -> str:
    if not isinstance(session, dict):
        return "—"
    engine = session.get("engine")
    if isinstance(engine, dict):
        return str(engine.get("engine") or engine.get("name") or "—")
    if isinstance(engine, str) and engine:
        return engine
    return "—"


templates.env.filters["engine_label"] = _engine_label


# --------------------------------------------------------------------------- #
# Contextos compartilhados
# --------------------------------------------------------------------------- #
def _base_ctx(request: Request, nav: str, current_user: User) -> dict:
    return {"request": request, "nav": nav, "current_user": current_user}


def _rows(db: Session, user_id: str) -> list[dict]:
    schedules = db.exec(
        select(Schedule).where(col(Schedule.user_id) == user_id).order_by(col(Schedule.created_at).desc())
    ).all()
    wa_labels = whatsapp_service.labels_by_session_name(db, user_id)
    out: list[dict] = []
    for s in schedules:
        dispatches = list(
            db.exec(
                select(Dispatch)
                .where(col(Dispatch.schedule_id) == s.id)
                .order_by(col(Dispatch.scheduled_at_utc).desc())
            ).all()
        )
        pending = sorted(
            (d for d in dispatches if str(d.status) in ("pending", "processing")),
            key=lambda d: d.scheduled_at_utc,
        )
        out.append(
            {
                "s": s,
                "whatsapp_label": wa_labels.get(s.session, s.session),
                "next_dispatch": pending[0] if pending else None,
                "last_dispatch": dispatches[0] if dispatches else None,
                "history": dispatches[:6],
            }
        )
    return out


def _table_ctx(request: Request, db: Session, user_id: str, tz_name: str) -> dict:
    return {"request": request, "rows": _rows(db, user_id), "default_timezone": tz_name}


# --------------------------------------------------------------------------- #
# Páginas
# --------------------------------------------------------------------------- #
@router.get("/agendamentos", response_class=HTMLResponse)
async def page_schedules(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    ctx = {
        **_base_ctx(request, "agendamentos", current_user),
        **_table_ctx(request, db, current_user.id, app_settings.user_timezone(current_user)),
        "whatsapp_sessions": whatsapp_service.list_sessions(db, current_user.id),
        "error": request.query_params.get("error"),
        "ok": request.query_params.get("ok"),
    }
    return templates.TemplateResponse("schedules.html", ctx)


@router.get("/conversas", response_class=HTMLResponse)
async def page_chats(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    primary = whatsapp_service.primary_session(db, current_user.id)
    if primary is None:
        return templates.TemplateResponse(
            "conversas.html", {**_base_ctx(request, "conversas", current_user), "session_id": None, "whatsapp_sessions": []}
        )
    return RedirectResponse(url=f"/conversas/{primary.id}", status_code=303)


@router.get("/conversas/{session_id}", response_class=HTMLResponse)
async def page_chats_session(
    request: Request,
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    session = whatsapp_service.get_session(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="WhatsApp não encontrado.")
    return templates.TemplateResponse(
        "conversas.html",
        {
            **_base_ctx(request, "conversas", current_user),
            "session_id": session.id,
            "whatsapp_sessions": whatsapp_service.list_sessions(db, current_user.id),
            "default_timezone": app_settings.user_timezone(current_user),
        },
    )


# --------------------------------------------------------------------------- #
# Parciais (htmx)
# --------------------------------------------------------------------------- #
@router.get("/ui/sidebar-status", response_class=HTMLResponse)
async def ui_sidebar_status(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    sessions = whatsapp_service.list_sessions(db, current_user.id)
    overall = await whatsapp_service.overall_status(request.app.state.waha, sessions)
    return templates.TemplateResponse("_sidebar_status.html", {"request": request, "overall": overall})


@router.get("/ui/schedules", response_class=HTMLResponse)
async def ui_schedules(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    return templates.TemplateResponse(
        "_table.html", _table_ctx(request, db, current_user.id, app_settings.user_timezone(current_user))
    )


@router.post("/ui/schedules")
async def ui_create(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
    recipient: str = Form(...),
    text: str = Form(...),
    send_at: str = Form(...),
    whatsapp_session_id: str = Form(""),
    timezone: str = Form(""),
    recurrence: str = Form(""),
    max_attempts: int = Form(3),
) -> RedirectResponse:
    try:
        parsed = datetime.fromisoformat(send_at)
    except ValueError:
        return RedirectResponse(url="/agendamentos?error=" + quote("Data/hora inválida."), status_code=303)
    wa_session = (
        whatsapp_service.get_session(db, whatsapp_session_id, current_user.id)
        if whatsapp_session_id
        else whatsapp_service.primary_session(db, current_user.id)
    )
    if wa_session is None:
        return RedirectResponse(
            url="/agendamentos?error=" + quote("Conecte um WhatsApp antes de criar um agendamento."), status_code=303
        )
    try:
        create_schedule(
            db,
            user_id=current_user.id,
            session=wa_session.session_name,
            recipient=recipient,
            text=text,
            send_at=parsed,
            timezone=timezone or app_settings.user_timezone(current_user),
            recurrence=recurrence or None,
            max_attempts=max_attempts,
        )
    except ValidationError as exc:
        return RedirectResponse(url="/agendamentos?error=" + quote(str(exc)), status_code=303)
    return RedirectResponse(url="/agendamentos?ok=" + quote("Agendamento criado."), status_code=303)


@router.post("/ui/schedules/{schedule_id}/cancel", response_class=HTMLResponse)
async def ui_cancel(
    request: Request,
    schedule_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    cancel_schedule(db, schedule_id, user_id=current_user.id)
    return templates.TemplateResponse(
        "_table.html", _table_ctx(request, db, current_user.id, app_settings.user_timezone(current_user))
    )


@router.post("/ui/schedules/{schedule_id}/run-now", response_class=HTMLResponse)
async def ui_run_now(
    request: Request,
    schedule_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    run_now(db, schedule_id, user_id=current_user.id)
    return templates.TemplateResponse(
        "_table.html", _table_ctx(request, db, current_user.id, app_settings.user_timezone(current_user))
    )


# ---- Conversas -------------------------------------------------------------- #
def _owned_wa_session(db: Session, session_id: str, user_id: str):
    session = whatsapp_service.get_session(db, session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="WhatsApp não encontrado.")
    return session


async def _chats_ctx(request: Request, db: Session, current_user: User, session_id: str, *, force: bool = False) -> dict:
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    try:
        chats = await list_chats(
            request.app.state.waha, wa_session.session_name, app_settings.user_timezone(current_user), force=force
        )
        return {"request": request, "session_id": session_id, "chats": chats, "chats_error": None}
    except WahaError as exc:
        return {"request": request, "session_id": session_id, "chats": [], "chats_error": str(exc)}


def _find_chat(chats: list[dict], chat_id: str) -> dict:
    for c in chats:
        if c["id"] == chat_id:
            return c
    return {"id": chat_id, "name": chat_id.split("@")[0], "picture": None, "is_group": chat_id.endswith("@g.us")}


@router.get("/ui/chats/{session_id}", response_class=HTMLResponse)
async def ui_chats(
    request: Request,
    session_id: str,
    refresh: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    return templates.TemplateResponse("_chat_list.html", await _chats_ctx(request, db, current_user, session_id, force=refresh))


@router.get("/ui/chats/{session_id}/view", response_class=HTMLResponse)
async def ui_chat_view(
    request: Request,
    session_id: str,
    chat: str = Query(...),
    ok: str | None = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    chats = (await _chats_ctx(request, db, current_user, session_id))["chats"]
    return templates.TemplateResponse(
        "_chat_view.html",
        {
            "request": request,
            "session_id": session_id,
            "chat_id": chat,
            "chat": _find_chat(chats, chat),
            "default_timezone": app_settings.user_timezone(current_user),
            "ok": ok,
        },
    )


@router.get("/ui/chats/{session_id}/messages", response_class=HTMLResponse)
async def ui_chat_messages(
    request: Request,
    session_id: str,
    chat: str = Query(...),
    refresh: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    hist = await get_history(
        db, request.app.state.waha, current_user.id, wa_session.session_name, chat,
        app_settings.user_timezone(current_user), force=refresh,
    )
    return templates.TemplateResponse(
        "_chat_messages.html",
        {
            "request": request, "chat_id": chat, "hist": hist,
            "synced_local": _sync_label(hist.synced_at, app_settings.user_timezone(current_user)),
        },
    )


@router.post("/ui/chats/{session_id}/send", response_class=HTMLResponse)
async def ui_chat_send(
    request: Request,
    session_id: str,
    chat: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    text = text.strip()
    ok = None
    if not text:
        ok = "erro:Mensagem vazia."
    else:
        try:
            await send_now(db, request.app.state.waha, current_user.id, wa_session.session_name, chat, text)
            ok = "Mensagem enviada."
        except WahaError as exc:
            ok = f"erro:{exc}"
    return await ui_chat_view(request, session_id=session_id, chat=chat, ok=ok, db=db, current_user=current_user)


@router.post("/ui/chats/{session_id}/schedule", response_class=HTMLResponse)
async def ui_chat_schedule(
    request: Request,
    session_id: str,
    chat: str = Form(...),
    text: str = Form(...),
    send_at: str = Form(...),
    recurrence: str = Form(""),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    ok = None
    try:
        parsed = datetime.fromisoformat(send_at)
        create_schedule(
            db,
            user_id=current_user.id,
            session=wa_session.session_name,
            recipient=chat,
            text=text,
            send_at=parsed,
            timezone=app_settings.user_timezone(current_user),
            recurrence=recurrence or None,
        )
        ok = "Agendamento criado."
    except ValueError:
        ok = "erro:Data/hora inválida."
    except ValidationError as exc:
        ok = f"erro:{exc}"
    return await ui_chat_view(request, session_id=session_id, chat=chat, ok=ok, db=db, current_user=current_user)


def _sync_label(dt: datetime | None, tz_name: str) -> str:
    if dt is None:
        return ""
    return utc_to_local(dt, tz_name).strftime("%d/%m %H:%M:%S")
