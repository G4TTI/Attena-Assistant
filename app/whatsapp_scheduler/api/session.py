"""API REST da sessão WAHA (status + QR de pareamento) — sempre a sessão do
usuário autenticado, nunca a de outro."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from .. import auth
from ..models import User
from ..waha import WahaClient, WahaError

router = APIRouter(prefix="/api/session", tags=["session"])


def _waha(request: Request) -> WahaClient:
    return request.app.state.waha


@router.get("")
async def session_status(request: Request, current_user: User = Depends(auth.require_user_api)) -> dict:
    try:
        return await _waha(request).get_session_status(current_user.waha_session)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/qr")
async def session_qr(request: Request, current_user: User = Depends(auth.require_user_api)) -> Response:
    try:
        content, content_type = await _waha(request).get_qr(current_user.waha_session)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "no-store"})


@router.post("/start", status_code=202)
async def session_start(request: Request, current_user: User = Depends(auth.require_user_api)) -> dict:
    try:
        # restart_session cobre tanto "nunca foi iniciada" quanto "travada em
        # FAILED depois que o WhatsApp desconectou" — um simples start não
        # recupera uma sessão já existente em estado ruim.
        return await _waha(request).restart_session(current_user.waha_session)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
