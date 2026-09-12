"""UI web (Jinja2 + htmx, sem build step)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, select

from ..chatsvc import get_history, list_chats, send_now
from ..config import settings
from ..db import get_session
from ..models import Dispatch, Schedule
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


# --------------------------------------------------------------------------- #
# Contextos compartilhados
# --------------------------------------------------------------------------- #
async def _session_ctx(request: Request) -> dict:
    waha = request.app.state.waha
    try:
        info = await waha.get_session_status(settings.waha_session)
        return {"session": info, "session_error": None}
    except WahaError as exc:
        return {"session": None, "session_error": str(exc)}


def _base_ctx(request: Request, nav: str) -> dict:
    return {"request": request, "nav": nav, "waha_session": settings.waha_session}


def _rows(db: Session) -> list[dict]:
    schedules = db.exec(select(Schedule).order_by(col(Schedule.created_at).desc())).all()
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
                "next_dispatch": pending[0] if pending else None,
                "last_dispatch": dispatches[0] if dispatches else None,
                "history": dispatches[:6],
            }
        )
    return out


def _table_ctx(request: Request, db: Session) -> dict:
    return {"request": request, "rows": _rows(db), "default_timezone": settings.default_timezone}


# --------------------------------------------------------------------------- #
# Páginas
# --------------------------------------------------------------------------- #
@router.get("/", response_class=HTMLResponse)
async def page_schedules(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    ctx = {
        **_base_ctx(request, "agendamentos"),
        **_table_ctx(request, db),
        "error": request.query_params.get("error"),
        "ok": request.query_params.get("ok"),
    }
    return templates.TemplateResponse("schedules.html", ctx)


@router.get("/conversas", response_class=HTMLResponse)
async def page_chats(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "conversas.html", {**_base_ctx(request, "conversas"), "default_timezone": settings.default_timezone}
    )


@router.get("/sessao", response_class=HTMLResponse)
async def page_session(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "sessao.html", {**_base_ctx(request, "sessao"), **(await _session_ctx(request))}
    )


# --------------------------------------------------------------------------- #
# Parciais (htmx)
# --------------------------------------------------------------------------- #
@router.get("/ui/sidebar-status", response_class=HTMLResponse)
async def ui_sidebar_status(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "_sidebar_status.html", {"request": request, **(await _session_ctx(request))}
    )


@router.get("/ui/session", response_class=HTMLResponse)
async def ui_session(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "_session.html",
        {"request": request, "waha_session": settings.waha_session, **(await _session_ctx(request))},
    )


@router.post("/ui/session/start", response_class=HTMLResponse)
async def ui_session_start(request: Request) -> HTMLResponse:
    start_error = None
    try:
        await request.app.state.waha.restart_session(settings.waha_session)
    except WahaError as exc:
        start_error = str(exc)
    return templates.TemplateResponse(
        "_session.html",
        {
            "request": request,
            "waha_session": settings.waha_session,
            "start_error": start_error,
            **(await _session_ctx(request)),
        },
    )


@router.get("/ui/schedules", response_class=HTMLResponse)
async def ui_schedules(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    return templates.TemplateResponse("_table.html", _table_ctx(request, db))


@router.post("/ui/schedules")
async def ui_create(
    request: Request,
    db: Session = Depends(get_session),
    recipient: str = Form(...),
    text: str = Form(...),
    send_at: str = Form(...),
    timezone: str = Form(""),
    recurrence: str = Form(""),
    max_attempts: int = Form(3),
) -> RedirectResponse:
    try:
        parsed = datetime.fromisoformat(send_at)
    except ValueError:
        return RedirectResponse(url="/?error=" + quote("Data/hora inválida."), status_code=303)
    try:
        create_schedule(
            db,
            recipient=recipient,
            text=text,
            send_at=parsed,
            timezone=timezone or None,
            recurrence=recurrence or None,
            max_attempts=max_attempts,
        )
    except ValidationError as exc:
        return RedirectResponse(url="/?error=" + quote(str(exc)), status_code=303)
    return RedirectResponse(url="/?ok=" + quote("Agendamento criado."), status_code=303)


@router.post("/ui/schedules/{schedule_id}/cancel", response_class=HTMLResponse)
async def ui_cancel(request: Request, schedule_id: str, db: Session = Depends(get_session)) -> HTMLResponse:
    cancel_schedule(db, schedule_id)
    return templates.TemplateResponse("_table.html", _table_ctx(request, db))


@router.post("/ui/schedules/{schedule_id}/run-now", response_class=HTMLResponse)
async def ui_run_now(request: Request, schedule_id: str, db: Session = Depends(get_session)) -> HTMLResponse:
    run_now(db, schedule_id)
    return templates.TemplateResponse("_table.html", _table_ctx(request, db))


# ---- Conversas -------------------------------------------------------------- #
async def _chats_ctx(request: Request, *, force: bool = False) -> dict:
    try:
        chats = await list_chats(request.app.state.waha, force=force)
        return {"request": request, "chats": chats, "chats_error": None}
    except WahaError as exc:
        return {"request": request, "chats": [], "chats_error": str(exc)}


def _find_chat(chats: list[dict], chat_id: str) -> dict:
    for c in chats:
        if c["id"] == chat_id:
            return c
    return {"id": chat_id, "name": chat_id.split("@")[0], "picture": None, "is_group": chat_id.endswith("@g.us")}


@router.get("/ui/chats", response_class=HTMLResponse)
async def ui_chats(request: Request, refresh: bool = Query(False)) -> HTMLResponse:
    return templates.TemplateResponse("_chat_list.html", await _chats_ctx(request, force=refresh))


@router.get("/ui/chats/view", response_class=HTMLResponse)
async def ui_chat_view(
    request: Request,
    chat: str = Query(...),
    ok: str | None = Query(None),
) -> HTMLResponse:
    chats = (await _chats_ctx(request))["chats"]
    return templates.TemplateResponse(
        "_chat_view.html",
        {
            "request": request,
            "chat_id": chat,
            "chat": _find_chat(chats, chat),
            "default_timezone": settings.default_timezone,
            "ok": ok,
        },
    )


@router.get("/ui/chats/messages", response_class=HTMLResponse)
async def ui_chat_messages(
    request: Request,
    chat: str = Query(...),
    refresh: bool = Query(False),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    hist = await get_history(db, request.app.state.waha, chat, force=refresh)
    return templates.TemplateResponse(
        "_chat_messages.html",
        {"request": request, "chat_id": chat, "hist": hist, "synced_local": _sync_label(hist.synced_at)},
    )


@router.post("/ui/chats/send", response_class=HTMLResponse)
async def ui_chat_send(
    request: Request,
    chat: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    text = text.strip()
    ok = None
    if not text:
        ok = "erro:Mensagem vazia."
    else:
        try:
            await send_now(db, request.app.state.waha, chat, text)
            ok = "Mensagem enviada."
        except WahaError as exc:
            ok = f"erro:{exc}"
    return await ui_chat_view(request, chat=chat, ok=ok)


@router.post("/ui/chats/schedule", response_class=HTMLResponse)
async def ui_chat_schedule(
    request: Request,
    chat: str = Form(...),
    text: str = Form(...),
    send_at: str = Form(...),
    recurrence: str = Form(""),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    ok = None
    try:
        parsed = datetime.fromisoformat(send_at)
        create_schedule(
            db,
            recipient=chat,
            text=text,
            send_at=parsed,
            recurrence=recurrence or None,
        )
        ok = "Agendamento criado."
    except ValueError:
        ok = "erro:Data/hora inválida."
    except ValidationError as exc:
        ok = f"erro:{exc}"
    return await ui_chat_view(request, chat=chat, ok=ok)


def _sync_label(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return utc_to_local(dt, settings.default_timezone).strftime("%d/%m %H:%M:%S")
