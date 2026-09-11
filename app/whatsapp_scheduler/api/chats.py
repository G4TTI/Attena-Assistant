"""API REST de conversas do WhatsApp."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlmodel import Session

from ..chatsvc import get_history, list_chats, send_now
from ..db import get_session
from ..waha import WahaError

router = APIRouter(prefix="/api/chats", tags=["chats"])


def _waha(request: Request):
    return request.app.state.waha


@router.get("")
async def chats(request: Request, refresh: bool = Query(False)) -> list[dict]:
    try:
        return await list_chats(_waha(request), force=refresh)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/messages")
async def messages(
    request: Request,
    chat: str = Query(..., description="chatId, ex: 5511999998888@c.us"),
    refresh: bool = Query(False),
    db: Session = Depends(get_session),
) -> dict:
    hist = await get_history(db, _waha(request), chat, force=refresh)
    return {
        "chat": chat,
        "from_cache": hist.from_cache,
        "synced_at": hist.synced_at,
        "error": hist.error,
        "messages": hist.messages,
    }


@router.post("/send")
async def send(
    request: Request,
    chat: str = Body(..., embed=True),
    text: str = Body(..., embed=True),
    db: Session = Depends(get_session),
) -> dict:
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Mensagem vazia.")
    try:
        return await send_now(db, _waha(request), chat, text)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
