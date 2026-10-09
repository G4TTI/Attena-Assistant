"""API REST das conexões WhatsApp do usuário autenticado (v1.3: N por usuário,
nunca a de outro — todo id é validado contra o dono antes de qualquer chamada
ao WAHA)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session

from .. import auth, whatsapp_service
from ..db import get_session
from ..models import User, WhatsAppSession
from ..waha import WahaClient, WahaError

router = APIRouter(prefix="/api/whatsapp-sessions", tags=["whatsapp-sessions"])


class WhatsAppSessionCreate(BaseModel):
    name: str


class WhatsAppSessionRename(BaseModel):
    name: str


def _waha(request: Request) -> WahaClient:
    return request.app.state.waha


def _owned(db: Session, session_id: str, current_user: User) -> WhatsAppSession:
    session = whatsapp_service.get_session(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="WhatsApp não encontrado.")
    return session


@router.get("")
def list_sessions(
    db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_api)
) -> list[dict]:
    return [
        {"id": s.id, "name": s.name, "session_name": s.session_name}
        for s in whatsapp_service.list_sessions(db, current_user.id)
    ]


@router.post("", status_code=201)
def create_session(
    payload: WhatsAppSessionCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> dict:
    session = whatsapp_service.create_session(db, current_user.id, payload.name)
    return {"id": session.id, "name": session.name, "session_name": session.session_name}


@router.get("/{session_id}")
async def session_status(
    session_id: str,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> dict:
    session = _owned(db, session_id, current_user)
    try:
        return await _waha(request).get_session_status(session.session_name)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{session_id}/qr")
async def session_qr(
    session_id: str,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> Response:
    session = _owned(db, session_id, current_user)
    try:
        content, content_type = await _waha(request).get_qr(session.session_name)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "no-store"})


@router.post("/{session_id}/start", status_code=202)
async def session_start(
    session_id: str,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> dict:
    session = _owned(db, session_id, current_user)
    try:
        # restart_session cobre tanto "nunca foi iniciada" quanto "travada em
        # FAILED depois que o WhatsApp desconectou" — um simples start não
        # recupera uma sessão já existente em estado ruim.
        return await _waha(request).restart_session(session.session_name)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{session_id}/rename")
def rename_session(
    session_id: str,
    payload: WhatsAppSessionRename,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_api),
) -> dict:
    session = whatsapp_service.rename_session(db, session_id, current_user.id, payload.name)
    if session is None:
        raise HTTPException(status_code=404, detail="WhatsApp não encontrado.")
    return {"id": session.id, "name": session.name, "session_name": session.session_name}


@router.delete("/{session_id}")
def disconnect_session(
    session_id: str, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_api)
) -> dict:
    if not whatsapp_service.disconnect_session(db, session_id, current_user.id):
        raise HTTPException(status_code=404, detail="WhatsApp não encontrado.")
    return {"status": "disconnected", "id": session_id}
