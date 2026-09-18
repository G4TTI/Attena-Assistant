"""Ponto de entrada: FastAPI + poller de agendamento no ciclo de vida do app."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from . import app_settings, auth, calendar_service, onboarding_service, whatsapp_service
from .api import calendar as calendar_api
from .api import chats as chats_api
from .api import schedules as schedules_api
from .api import session as session_api
from .auth import NotAuthenticated
from .calendar_sync import CalendarSyncService
from .config import settings
from .db import get_engine, init_db
from .scheduler import SchedulerService
from .time_sync import ClockSyncService
from .waha import WahaClient
from .web import routes as web_routes
from .web import auth_routes, calendar_routes, dashboard_routes, onboarding_routes, settings_routes, whatsapp_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("whatsapp_scheduler")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    clock_sync = ClockSyncService()
    # Sincroniza o relógio com a internet ANTES de tudo o mais — o relógio do
    # sistema (VM/container) pode estar errado por horas (sobretudo depois de
    # suspender/retomar a máquina host), e isso afetaria toda decisão de
    # agendamento, não só o relógio exibido na tela.
    await clock_sync.start()
    # Migração + carga de configurações runtime: precisam terminar antes de
    # qualquer requisição ou tick de fundo rodar, pra ninguém ver o banco
    # pela metade (ex.: automações antigas ainda não convertidas).
    with Session(get_engine()) as db:
        calendar_service.migrate_legacy_automations(db)
        whatsapp_service.migrate_legacy_sessions(db)
        onboarding_service.migrate_legacy_users(db)
        app_settings.load_from_db(db)
    waha = WahaClient(settings.waha_base_url, settings.waha_api_key, settings.request_timeout)
    scheduler = SchedulerService(waha)
    calendar_sync = CalendarSyncService()
    app.state.waha = waha
    app.state.scheduler = scheduler
    app.state.calendar_sync = calendar_sync
    app.state.clock_sync = clock_sync
    await scheduler.start()
    await calendar_sync.start()
    logger.info("app pronto — WAHA em %s, sessão '%s'", settings.waha_base_url, settings.waha_session)
    try:
        yield
    finally:
        await calendar_sync.stop()
        await scheduler.stop()
        await clock_sync.stop()
        await waha.aclose()


app = FastAPI(title="Attena Assistant", version="1.3.0", lifespan=lifespan)
app.include_router(auth_routes.router)
app.include_router(schedules_api.router)
app.include_router(session_api.router)
app.include_router(chats_api.router)
app.include_router(calendar_api.router)
app.include_router(web_routes.router)
app.include_router(calendar_routes.router)
app.include_router(settings_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(whatsapp_routes.router)
app.include_router(onboarding_routes.router)


@app.exception_handler(NotAuthenticated)
async def _not_authenticated_handler(request: Request, exc: NotAuthenticated):
    from urllib.parse import quote

    return RedirectResponse(url="/login?next=" + quote(exc.next_path), status_code=303)


# CSP liberada só para o que a app de fato usa hoje: htmx via CDN, estilo/script
# inline (sem build step, ver base.html — apertar pra nonce fica pra uma
# próxima etapa), imagens/QR em data: URI, e nada de terceiros além disso.
# `form-action` também é aplicado pelo navegador ao destino FINAL de um
# redirect (não só à URL do `action` do form) — o formulário "Conectar Google
# Agenda" faz POST em /configuracoes/google/connect, que responde com um
# redirect 302 pra accounts.google.com; com só 'self' aqui, o navegador
# bloqueia esse redirect silenciosamente (sem erro visível, só no console) e
# o botão parece não fazer nada. Precisa liberar o domínio de destino do
# fluxo OAuth explicitamente.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://unpkg.com 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self' https://accounts.google.com"
)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = _CSP
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.get("/healthz", tags=["ops"])
def healthz() -> dict:
    return {"status": "ok"}


# Rotas que continuam acessíveis mesmo com onboarding pendente: páginas
# públicas de autenticação, o próprio onboarding, saúde do processo, e toda
# rota "de máquina" (API REST + parciais htmx) — essas nunca devem devolver
# um redirect HTML no lugar da resposta que o cliente espera (Parte 25: o
# onboarding orienta, nunca bloqueia o uso do app).
_ONBOARDING_EXEMPT_PREFIXES = (
    "/login", "/cadastro", "/esqueci-senha", "/redefinir-senha", "/verificar-email",
    "/logout", "/onboarding", "/healthz", "/api/", "/ui/",
)


def _needs_onboarding(request: Request) -> bool:
    with Session(get_engine()) as db:
        user = auth.get_current_user_optional(request, db)
        return user is not None and user.onboarding_completed_at is None


@app.middleware("http")
async def _onboarding_gate(request: Request, call_next):
    path = request.url.path
    if request.method == "GET" and not path.startswith(_ONBOARDING_EXEMPT_PREFIXES):
        # Consulta de banco síncrona: numa thread, pra não parar o event loop
        # a cada navegação de página.
        if await asyncio.to_thread(_needs_onboarding, request):
            return RedirectResponse(url="/onboarding", status_code=303)
    return await call_next(request)
