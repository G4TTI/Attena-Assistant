"""API REST de conversas do WhatsApp — sempre de uma conexão (`WhatsAppSession`)
do usuário autenticado, nunca a de outro."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlmodel import Session

from .. import app_settings, auth, whatsapp_service
from ..chatsvc import get_history, list_chats, send_now
from ..db import get_session
from ..models import User, WhatsAppSession
from ..waha import WahaError

router = APIRouter(prefix="/api/whatsapp-sessions/{session_id}/chats", tags=["chats"])


def _waha(request: Request):
    return request.app.state.waha


def _owned(db: Session, session_id: str, current_user: User) -> WhatsAppSession:
    session = whatsapp_service.get_session(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="WhatsApp não encontrado.")
    return session


@router.get("")
async def chats(
    session_id: str,
    request: Request,
    refresh: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> list[dict]:
    wa_session = _owned(db, session_id, current_user)
    try:
        return await list_chats(
            _waha(request), wa_session.session_name, app_settings.user_timezone(current_user), force=refresh
        )
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/messages")
async def messages(
    session_id: str,
    request: Request,
    chat: str = Query(..., description="chatId, ex: 5511999998888@c.us"),
    refresh: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> dict:
    wa_session = _owned(db, session_id, current_user)
    hist = await get_history(
        db, _waha(request), current_user.id, wa_session.session_name, chat,
        app_settings.user_timezone(current_user), force=refresh,
    )
    return {
        "chat": chat,
        "from_cache": hist.from_cache,
        "synced_at": hist.synced_at,
        "error": hist.error,
        "messages": hist.messages,
    }


@router.post("/send")
async def send(
    session_id: str,
    request: Request,
    chat: str = Body(..., embed=True),
    text: str = Body(..., embed=True),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> dict:
    wa_session = _owned(db, session_id, current_user)
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Mensagem vazia.")
    try:
        return await send_now(db, _waha(request), current_user.id, wa_session.session_name, chat, text)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
