"""Fixtures compartilhadas. Precisa configurar o ambiente ANTES de importar o app."""

from __future__ import annotations

import base64
import os
import tempfile
from datetime import timedelta
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="wascheduler-test-"))
os.environ.setdefault("DB_PATH", str(_TMP / "test.db"))
os.environ.setdefault("WAHA_BASE_URL", "http://waha.test")
os.environ.setdefault("WAHA_API_KEY", "test-key")
os.environ.setdefault("WAHA_SESSION", "default")
os.environ.setdefault("DEFAULT_TIMEZONE", "America/Sao_Paulo")
os.environ.setdefault("MAX_OVERDUE_MINUTES", "120")
os.environ.setdefault("SEND_JITTER_SECONDS", "0")
os.environ.setdefault("TICK_SECONDS", "3600")  # o loop não dispara sozinho durante os testes
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8090/calendario/oauth/callback")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "8bxweqvwKGVGSYYLOSnwiZWC6TbNYabjfPe-6QBio10=")
os.environ.setdefault("CALENDAR_SYNC_SECONDS", "3600")  # idem: não dispara sozinho durante os testes
os.environ.setdefault("CLOCK_SYNC_SECONDS", "3600")  # idem: não dispara sozinho durante os testes
os.environ.setdefault("PRIVACY_CLEANUP_SECONDS", "3600")  # idem
# Chaves de dados de TESTE, aleatórias a cada execução — nenhuma chave fica no código.
os.environ.setdefault("DATA_ENCRYPTION_KEYS", "1:" + base64.b64encode(os.urandom(32)).decode())
os.environ.setdefault("DATA_HASH_KEY", base64.b64encode(os.urandom(32)).decode())

import pytest  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

import whatsapp_scheduler.models  # noqa: E402,F401  (registra as tabelas)
from whatsapp_scheduler.calendar_providers.base import (  # noqa: E402
    OAuthTokens,
    RemoteCalendar,
    RemoteEvent,
    RemoteEventPage,
)
from whatsapp_scheduler.clock import utcnow  # noqa: E402
from whatsapp_scheduler.db import get_engine  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """`ratelimit._attempts` é estado de módulo global (dict em memória, ver
    ratelimit.py) — sem isso, os vários testes que passam por `/cadastro`
    (via `register_and_login`) dentro do MESMO processo pytest acabariam
    batendo no limite de tentativas (5 por 300s, mesma chave de IP) bem antes
    da janela expirar de verdade, derrubando testes que não têm nada a ver
    com rate limit."""
    from whatsapp_scheduler import ratelimit

    ratelimit._attempts.clear()
    yield
    ratelimit._attempts.clear()


@pytest.fixture(autouse=True)
def _reset_clock_offset():
    """`clock._offset` é estado de módulo global (ver time_sync.py) — sem
    isso, um teste que sincroniza o relógio vazaria o offset pros testes
    seguintes que leem `clock.utcnow()` diretamente (os que usam o fixture
    `frozen_clock` não seriam afetados, já que ele substitui `utcnow` inteira,
    mas os que não usam ficariam com "agora" errado de forma silenciosa)."""
    from whatsapp_scheduler import clock

    clock.set_offset(timedelta(0))
    yield
    clock.set_offset(timedelta(0))


@pytest.fixture(autouse=True)
def _reset_chat_cache():
    """`chatsvc._chat_cache` é estado de módulo global, chaveado por
    `session_name` — e `_fresh_db` faz o "primeiro usuário cadastrado" (que
    ganha `session_name = settings.waha_session`, sempre o mesmo valor fixo
    de teste) se repetir a cada teste, então sem isso o cache de chats de um
    teste vazaria pro próximo que usa o mesmo `session_name`."""
    from whatsapp_scheduler import chatsvc

    chatsvc._chat_cache.clear()
    chatsvc._history_cache.clear()
    yield
    chatsvc._chat_cache.clear()
    chatsvc._history_cache.clear()


@pytest.fixture
def db():
    with Session(get_engine()) as session:
        yield session


@pytest.fixture
def test_user():
    """`User` real criado direto no banco (sem passar por HTTP) — para os
    testes unitários que chamam funções de serviço diretamente e só
    precisam de um dono válido pra satisfazer a FK (`PRAGMA foreign_keys=ON`).
    Objeto ORM puro (sem `Relationship()` neste projeto), então `.id` e
    `.waha_session` continuam legíveis depois que a sessão fecha — mesmo
    padrão do fixture `db` acima."""
    from whatsapp_scheduler.auth import hash_password
    from whatsapp_scheduler.models import User

    with Session(get_engine()) as session:
        user = User(name="Tester", email="tester@example.com", password_hash=hash_password("testpass123"))
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def register_and_login(
    client,
    *,
    name: str = "Tester",
    email: str = "tester@example.com",
    password: str = "testpass123",
    skip_onboarding: bool = True,
):
    """Cadastra e loga um usuário de teste no `TestClient` passado (o
    cookie de sessão fica no jar do client, então requests seguintes já
    saem autenticadas). Retorna o `User` criado.

    `skip_onboarding=True` (padrão) marca o onboarding como concluído direto
    no banco — a maioria dos testes existentes pressupõe acesso direto às
    páginas depois de logar, e sem isso o gate de onboarding (v1.3,
    `main._onboarding_gate`) redirecionaria toda página pra `/onboarding`.
    Testes que exercitam o próprio onboarding devem passar `False`.
    """
    from sqlmodel import select as _select

    from whatsapp_scheduler.clock import utcnow
    from whatsapp_scheduler.models import User

    resp = client.post(
        "/cadastro",
        data={"name": name, "email": email, "password": password, "password_confirm": password},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with Session(get_engine()) as session:
        user = session.exec(_select(User).where(User.email == email)).first()
        assert user is not None
        if skip_onboarding:
            user.onboarding_completed_at = utcnow()
            session.add(user)
            session.commit()
            session.refresh(user)
        return user


def whatsapp_session_id(client) -> str:
    """Id da primeira conexão WhatsApp do usuário logado no `client` — criada
    automaticamente no cadastro (`register_and_login` -> `register_user` ->
    `whatsapp_service.ensure_first_session`)."""
    sessions = client.get("/api/whatsapp-sessions").json()
    assert sessions, "usuário de teste sem WhatsAppSession"
    return sessions[0]["id"]


class FakeWaha:
    """Stub do WahaClient para os testes do scheduler."""

    def __init__(self, status: str = "WORKING") -> None:
        self.status = status
        self.sent: list[dict] = []
        self.send_error: Exception | None = None
        self.status_error: Exception | None = None
        self.chats: list[dict] = []
        self.messages: list[dict] = []
        self.chats_error: Exception | None = None
        self.messages_error: Exception | None = None
        self.restart_error: Exception | None = None
        self.restart_calls = 0
        # False = comportamento de usuário novo: a sessão só existe no banco do app.
        self.session_exists = True
        self.created: list[str] = []
        self.last_id: str | None = None
        self.logged_out: list[str] = []
        self.deleted: list[str] = []
        self.listed: list[str] = []

    async def get_session_status(self, session: str) -> dict:
        if self.status_error:
            raise self.status_error
        if not self.session_exists:
            from whatsapp_scheduler.waha import WahaError

            raise WahaError(
                'WAHA respondeu 404 em GET /api/sessions/x: {"message":"Session not found"}', status_code=404
            )
        return {"name": session, "status": self.status}

    async def create_session(self, session: str) -> dict:
        self.session_exists = True
        self.created.append(session)
        self.status = "STARTING"
        return {"name": session, "status": "STARTING"}

    async def ensure_session(self, session: str) -> dict:
        try:
            return await self.get_session_status(session)
        except Exception as exc:  # noqa: BLE001 - só o 404 vira criação, como no cliente real
            if getattr(exc, "status_code", None) != 404:
                raise
            return await self.create_session(session)

    async def send_text(self, session: str, chat_id: str, text: str) -> dict:
        if self.send_error:
            raise self.send_error
        self.sent.append({"session": session, "chatId": chat_id, "text": text})
        self.last_id = f"true_{chat_id}_{len(self.sent)}"
        return {"id": self.last_id}

    async def get_qr(self, session: str) -> tuple[bytes, str]:
        return b"PNGDATA", "image/png"

    async def start_session(self, session: str) -> dict:
        return {"name": session, "status": "STARTING"}

    async def restart_session(self, session: str) -> dict:
        self.restart_calls += 1
        if self.restart_error:
            raise self.restart_error
        self.status = "STARTING"
        return {"name": session, "status": "STARTING"}

    async def get_chats_overview(
        self, session: str, limit: int = 50, timeout: float | None = None
    ) -> list[dict]:
        if self.chats_error:
            raise self.chats_error
        return self.chats

    async def get_messages(
        self, session: str, chat_id: str, limit: int = 50, timeout: float | None = None
    ) -> list[dict]:
        if self.messages_error:
            raise self.messages_error
        return self.messages

    async def logout_session(self, session: str) -> None:
        self.logged_out.append(session)

    async def delete_session(self, session: str) -> None:
        self.deleted.append(session)

    async def list_sessions(self) -> list[dict]:
        return [{"name": name, "status": self.status, "me": {"id": "5511999990000@c.us", "pushName": "Dono"}} for name in self.listed]

    async def aclose(self) -> None:  # pragma: no cover
        pass


@pytest.fixture
def fake_waha() -> FakeWaha:
    return FakeWaha()


class FakeGoogleCalendarProvider:
    """Stub de `CalendarProvider` (ver calendar_providers/base.py) para os testes de sync."""

    key = "google"

    def __init__(self) -> None:
        self.configured = True
        self.account_email: str | None = "fake@example.com"
        self.calendars: list[RemoteCalendar] = []
        # external_calendar_id -> eventos que a PRÓXIMA chamada de list_events devolve
        self.events_by_calendar: dict[str, list[RemoteEvent]] = {}
        self.next_sync_token_by_calendar: dict[str, str | None] = {}
        # calendários cuja próxima chamada deve simular um syncToken expirado (410)
        self.invalidate_sync_token_for: set[str] = set()
        self.list_events_calls: list[dict] = []
        self.exchange_code_calls: list[str] = []
        self.refresh_calls: list[OAuthTokens] = []
        self.list_calendars_error: Exception | None = None
        self.list_events_error: Exception | None = None
        self.create_event_error: Exception | None = None
        self.update_event_error: Exception | None = None
        self.delete_event_error: Exception | None = None
        self.created_events: list[dict] = []
        self.updated_events: list[dict] = []
        self.deleted_events: list[str] = []
        self._next_external_id = 1

    def is_configured(self) -> bool:
        return self.configured

    def get_authorize_url(self, state: str) -> str:
        return f"https://accounts.google.test/authorize?state={state}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        self.exchange_code_calls.append(code)
        return OAuthTokens(
            access_token="fake-access-token",
            refresh_token="fake-refresh-token",
            expires_at=utcnow() + timedelta(hours=1),
            scope="https://www.googleapis.com/auth/calendar.readonly",
        )

    async def refresh(self, tokens: OAuthTokens) -> OAuthTokens:
        self.refresh_calls.append(tokens)
        return OAuthTokens(
            access_token="fake-access-token-refreshed",
            refresh_token=tokens.refresh_token,
            expires_at=utcnow() + timedelta(hours=1),
            scope=tokens.scope,
        )

    async def get_account_identifier(self, tokens: OAuthTokens) -> str | None:
        return self.account_email

    async def list_calendars(self, tokens: OAuthTokens) -> list[RemoteCalendar]:
        if self.list_calendars_error:
            raise self.list_calendars_error
        return self.calendars

    async def list_events(
        self,
        tokens: OAuthTokens,
        calendar: RemoteCalendar,
        *,
        sync_token: str | None = None,
        time_min=None,
        time_max=None,
    ) -> RemoteEventPage:
        self.list_events_calls.append(
            {"calendar": calendar.external_id, "sync_token": sync_token, "time_min": time_min, "time_max": time_max}
        )
        if self.list_events_error:
            raise self.list_events_error
        if calendar.external_id in self.invalidate_sync_token_for:
            self.invalidate_sync_token_for.discard(calendar.external_id)
            return RemoteEventPage(events=[], next_sync_token=None, sync_token_invalid=True)
        events = self.events_by_calendar.get(calendar.external_id, [])
        next_token = self.next_sync_token_by_calendar.get(calendar.external_id, "next-token")
        return RemoteEventPage(events=events, next_sync_token=next_token)

    async def create_event(self, tokens, calendar, *, title, description, start_utc, end_utc, timezone) -> str:
        if self.create_event_error:
            raise self.create_event_error
        self._next_external_id += 1
        external_id = f"fake-ext-{self._next_external_id}"
        self.created_events.append(
            {"calendar": calendar.external_id, "title": title, "start_utc": start_utc, "external_id": external_id}
        )
        return external_id

    async def update_event(self, tokens, calendar, external_id, *, title, description, start_utc, end_utc, timezone):
        if self.update_event_error:
            raise self.update_event_error
        self.updated_events.append(
            {"calendar": calendar.external_id, "external_id": external_id, "title": title, "start_utc": start_utc}
        )

    async def delete_event(self, tokens, calendar, external_id) -> None:
        if self.delete_event_error:
            raise self.delete_event_error
        self.deleted_events.append(external_id)


@pytest.fixture
def fake_google() -> FakeGoogleCalendarProvider:
    return FakeGoogleCalendarProvider()


def db_locations_containing(needle: str) -> list[str]:
    """Varre TODAS as colunas de texto de TODAS as tabelas (SQL cru, sem ORM) e
    devolve "tabela.coluna" onde `needle` aparece — base dos testes de
    privacidade ("o banco sozinho não revela X")."""
    from sqlalchemy import text

    found: list[str] = []
    with get_engine().connect() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))]
        for table in tables:
            for column in [r[1] for r in conn.execute(text(f'PRAGMA table_info("{table}")'))]:
                hit = conn.execute(
                    text(f'SELECT 1 FROM "{table}" WHERE CAST("{column}" AS TEXT) LIKE :n LIMIT 1'), {"n": f"%{needle}%"}
                ).first()
                if hit:
                    found.append(f"{table}.{column}")
    return found


# --------------------------------------------------------------------------- #
# v1.4: conteúdo e destinatário ficam cifrados no banco. Nos testes, ler/criar
# sempre por estes atalhos (o mesmo caminho da aplicação: privacy.py).
# --------------------------------------------------------------------------- #
def text_of(obj) -> str | None:
    from whatsapp_scheduler import privacy
    from whatsapp_scheduler.models import AutomationMessage

    if isinstance(obj, AutomationMessage):
        return privacy.automation_message(obj)
    return privacy.schedule_message(obj)


def chat_of(obj) -> str | None:
    from whatsapp_scheduler import privacy
    from whatsapp_scheduler.models import ScheduleGroup

    if isinstance(obj, ScheduleGroup):
        info = privacy.group_recipient(obj)
        return info.chat_id if info else None
    return privacy.schedule_recipient(obj)


def name_of(group) -> str | None:
    from whatsapp_scheduler import privacy

    info = privacy.group_recipient(group)
    return info.name if info else None


def make_schedule(*, text: str, chat_id: str, recipient_input: str | None = None, **kwargs):
    """`Schedule` como o app grava (cifrado). `recipient_input` é aceito só por compatibilidade."""
    from whatsapp_scheduler import privacy
    from whatsapp_scheduler.models import Schedule

    schedule = Schedule(**kwargs)
    privacy.seal_schedule_message(schedule, text)
    privacy.seal_schedule_recipient(schedule, chat_id)
    return schedule


def make_automation_message(*, text: str, **kwargs):
    from whatsapp_scheduler import privacy
    from whatsapp_scheduler.models import AutomationMessage

    message = AutomationMessage(**kwargs)
    privacy.seal_automation_message(message, text)
    return message


def recipient_hash_for(user_id: str, chat_id: str) -> str:
    from whatsapp_scheduler import privacy

    return privacy.recipient_hash(user_id, chat_id)
