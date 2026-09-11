"""Ponto de entrada: FastAPI + poller de agendamento no ciclo de vida do app."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import chats as chats_api
from .api import schedules as schedules_api
from .api import session as session_api
from .config import settings
from .db import init_db
from .scheduler import SchedulerService
from .waha import WahaClient
from .web import routes as web_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("whatsapp_scheduler")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    waha = WahaClient(settings.waha_base_url, settings.waha_api_key, settings.request_timeout)
    scheduler = SchedulerService(waha)
    app.state.waha = waha
    app.state.scheduler = scheduler
    await scheduler.start()
    logger.info("app pronto — WAHA em %s, sessão '%s'", settings.waha_base_url, settings.waha_session)
    try:
        yield
    finally:
        await scheduler.stop()
        await waha.aclose()


app = FastAPI(title="WhatsApp Scheduler", version="0.1.0", lifespan=lifespan)
app.include_router(schedules_api.router)
app.include_router(session_api.router)
app.include_router(chats_api.router)
app.include_router(web_routes.router)


@app.get("/healthz", tags=["ops"])
def healthz() -> dict:
    return {"status": "ok"}
