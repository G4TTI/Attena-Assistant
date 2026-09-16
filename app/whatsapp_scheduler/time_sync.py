"""Sincroniza `clock.utcnow()` com um horário de referência da internet.

Usa o cabeçalho HTTP `Date` (todo servidor HTTPS devolve um, com precisão de
~1s) em vez de NTP/UDP — mais simples e mais provável de atravessar redes
restritivas (o app já faz chamadas HTTPS pro WAHA e pro Google, então essa
rota de rede já é conhecida como aberta). Nunca bloqueia nem derruba o app: se
a sincronização falhar, `clock` continua com o último offset conhecido (ou
0, no primeiro boot).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

from . import clock
from .config import settings

logger = logging.getLogger("whatsapp_scheduler.time_sync")

_REFERENCE_URL = "https://www.google.com/generate_204"

last_synced_at: datetime | None = None
last_sync_error: str | None = None


async def sync_once(client: httpx.AsyncClient | None = None) -> timedelta | None:
    """Consulta o cabeçalho `Date` de um servidor HTTPS confiável, calcula o
    desvio em relação ao relógio do sistema (descontando o tempo de viagem
    da requisição pela metade) e atualiza `clock`. Retorna o offset aplicado,
    ou `None` se a consulta falhar."""
    global last_synced_at, last_sync_error
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=10.0)
    try:
        before = datetime.now(timezone.utc)
        resp = await client.head(_REFERENCE_URL)
        after = datetime.now(timezone.utc)
        date_header = resp.headers.get("date")
        if not date_header:
            raise ValueError("resposta sem cabeçalho Date")
        server_time = parsedate_to_datetime(date_header)
        if server_time.tzinfo is None:
            server_time = server_time.replace(tzinfo=timezone.utc)
        request_midpoint = before + (after - before) / 2
        offset = server_time - request_midpoint
        clock.set_offset(offset)
        last_synced_at = clock.utcnow()
        last_sync_error = None
        logger.info("relógio sincronizado com a internet (desvio: %.1fs)", offset.total_seconds())
        return offset
    except Exception as exc:  # nunca deixa a sincronização derrubar o app
        last_sync_error = str(exc)
        logger.warning("falha ao sincronizar relógio com a internet: %s", exc)
        return None
    finally:
        if owns_client:
            await client.aclose()


class ClockSyncService:
    """Loop de background — mesmo formato do SchedulerService/CalendarSyncService."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        # Sincroniza já no boot, antes do scheduler/calendar_sync começarem a
        # rodar — evita que qualquer decisão de agendamento use um relógio
        # ainda não corrigido.
        await sync_once()
        self._task = asyncio.create_task(self._run(), name="clock-sync-loop")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=15)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        logger.info("sincronização de relógio iniciada (intervalo=%ss)", settings.clock_sync_seconds)
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=settings.clock_sync_seconds)
            except asyncio.TimeoutError:
                await sync_once()
        logger.info("sincronização de relógio parada")
