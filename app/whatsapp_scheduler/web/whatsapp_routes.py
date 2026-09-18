"""UI web da página WhatsApps: um usuário pode conectar várias sessões (v1.3,
item 9-14). O cliente WAHA em si (start/restart/QR/status) é sempre o mesmo
`WahaClient` já usado pela sessão única de antes — só passa a ser chamado uma
vez por conexão em vez de uma vez só."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session

from .. import auth, whatsapp_service
from ..db import get_session
from ..models import User
from ..waha import WahaClient, WahaError
from .routes import templates

router = APIRouter(tags=["ui-whatsapps"])


def _waha(request: Request) -> WahaClient:
    return request.app.state.waha


async def _list_ctx(request: Request, db: Session, current_user: User) -> dict:
    sessions = whatsapp_service.list_sessions(db, current_user.id)
    return {"request": request, "rows": await whatsapp_service.status_rows(_waha(request), sessions)}


@router.get("/whatsapps", response_class=HTMLResponse)
async def page_whatsapps(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    ctx = {"request": request, "nav": "whatsapps", "current_user": current_user, **(await _list_ctx(request, db, current_user))}
    return templates.TemplateResponse("whatsapps.html", ctx)


@router.get("/ui/whatsapps", response_class=HTMLResponse)
async def ui_whatsapps(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    return templates.TemplateResponse("_whatsapp_list.html", await _list_ctx(request, db, current_user))


@router.post("/whatsapps", response_class=HTMLResponse)
async def ui_whatsapp_create(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    session = whatsapp_service.create_session(db, current_user.id, name)
    try:
        await _waha(request).start_session(session.session_name)
    except WahaError:
        pass  # o card da lista já mostra o erro de status — não bloqueia a criação
    return templates.TemplateResponse("_whatsapp_list.html", await _list_ctx(request, db, current_user))


@router.post("/whatsapps/{session_id}/start", response_class=HTMLResponse)
async def ui_whatsapp_start(
    request: Request,
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    session = whatsapp_service.get_session(db, session_id, current_user.id)
    start_error = None
    if session is not None:
        try:
            await _waha(request).restart_session(session.session_name)
        except WahaError as exc:
            start_error = str(exc)
    ctx = await _list_ctx(request, db, current_user)
    if start_error:
        for row in ctx["rows"]:
            if row["session"].id == session_id:
                row["status_error"] = start_error
    return templates.TemplateResponse("_whatsapp_list.html", ctx)


@router.post("/whatsapps/{session_id}/rename", response_class=HTMLResponse)
async def ui_whatsapp_rename(
    request: Request,
    session_id: str,
    name: str = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    whatsapp_service.rename_session(db, session_id, current_user.id, name)
    return templates.TemplateResponse("_whatsapp_list.html", await _list_ctx(request, db, current_user))


@router.post("/whatsapps/{session_id}/disconnect", response_class=HTMLResponse)
async def ui_whatsapp_disconnect(
    request: Request,
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    whatsapp_service.disconnect_session(db, session_id, current_user.id)
    return templates.TemplateResponse("_whatsapp_list.html", await _list_ctx(request, db, current_user))


@router.get("/ui/whatsapps/{session_id}/qr")
async def ui_whatsapp_qr(
    request: Request,
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> Response:
    session = whatsapp_service.get_session(db, session_id, current_user.id)
    if session is None:
        return Response(status_code=404)
    try:
        content, content_type = await _waha(request).get_qr(session.session_name)
    except WahaError:
        return Response(status_code=502)
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "no-store"})
