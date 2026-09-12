"""API REST da sessão WAHA (status + QR de pareamento)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..config import settings
from ..waha import WahaClient, WahaError

router = APIRouter(prefix="/api/session", tags=["session"])


def _waha(request: Request) -> WahaClient:
    return request.app.state.waha


@router.get("")
async def session_status(request: Request) -> dict:
    try:
        return await _waha(request).get_session_status(settings.waha_session)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/qr")
async def session_qr(request: Request) -> Response:
    try:
        content, content_type = await _waha(request).get_qr(settings.waha_session)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "no-store"})


@router.post("/start", status_code=202)
async def session_start(request: Request) -> dict:
    try:
        # restart_session cobre tanto "nunca foi iniciada" quanto "travada em
        # FAILED depois que o WhatsApp desconectou" — um simples start não
        # recupera uma sessão já existente em estado ruim.
        return await _waha(request).restart_session(settings.waha_session)
    except WahaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
