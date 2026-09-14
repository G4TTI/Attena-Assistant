"""Ponto de entrada: FastAPI + poller de agendamento no ciclo de vida do app."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from . import app_settings, calendar_service
from .api import calendar as calendar_api
from .api import chats as chats_api
from .api import schedules as schedules_api
from .api import session as session_api
from .calendar_sync import CalendarSyncService
from .config import settings
from .db import get_engine, init_db
from .scheduler import SchedulerService
from .waha import WahaClient
from .web import routes as web_routes
from .web import calendar_routes, settings_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("whatsapp_scheduler")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Migração + carga de configurações runtime: precisam terminar antes de
    # qualquer requisição ou tick de fundo rodar, pra ninguém ver o banco
    # pela metade (ex.: automações antigas ainda não convertidas).
    with Session(get_engine()) as db:
        calendar_service.migrate_legacy_automations(db)
        app_settings.load_from_db(db)
    waha = WahaClient(settings.waha_base_url, settings.waha_api_key, settings.request_timeout)
    scheduler = SchedulerService(waha)
    calendar_sync = CalendarSyncService()
    app.state.waha = waha
    app.state.scheduler = scheduler
    app.state.calendar_sync = calendar_sync
    await scheduler.start()
    await calendar_sync.start()
    logger.info("app pronto — WAHA em %s, sessão '%s'", settings.waha_base_url, settings.waha_session)
    try:
        yield
    finally:
        await calendar_sync.stop()
        await scheduler.stop()
        await waha.aclose()


app = FastAPI(title="Attena Assistant", version="1.1.0-alpha", lifespan=lifespan)
app.include_router(schedules_api.router)
app.include_router(session_api.router)
app.include_router(chats_api.router)
app.include_router(calendar_api.router)
app.include_router(web_routes.router)
app.include_router(calendar_routes.router)
app.include_router(settings_routes.router)


@app.get("/healthz", tags=["ops"])
def healthz() -> dict:
    return {"status": "ok"}
