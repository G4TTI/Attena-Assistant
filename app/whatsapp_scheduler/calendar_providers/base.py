"""Interface comum de provedor de calendário.

O resto do app (`calendar_service.py`, `calendar_sync.py`) trabalha só
contra esta interface — nunca importa `google.py` diretamente. Adicionar
Outlook/Apple no futuro é implementar esta ABC e registrar em
`calendar_providers/__init__.py`; nenhum outro arquivo muda.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scope: str = ""


@dataclass
class RemoteCalendar:
    external_id: str
    name: str
    time_zone: str = "UTC"
    color: str | None = None
    primary: bool = False


@dataclass
class RemoteEvent:
    external_id: str
    title: str
    description: str
    # None quando `cancelled` é True: provedores (ex.: Google) não reenviam
    # horário de eventos cancelados/removidos, só o id e o status.
    start_utc: datetime | None
    end_utc: datetime | None
    timezone: str | None
    all_day: bool
    cancelled: bool
    recurring_event_id: str | None = None
    provider_updated_at: datetime | None = None


@dataclass
class RemoteEventPage:
    events: list[RemoteEvent]
    next_sync_token: str | None
    sync_token_invalid: bool = False  # True = provedor pediu resync completo (ex.: 410)


class CalendarProviderError(RuntimeError):
    """Erro genérico de comunicação com o provedor."""


class SyncTokenExpired(CalendarProviderError):
    """O cursor de sincronização incremental não é mais válido; refazer sync completo."""


class CalendarProvider(ABC):
    """Um provedor de calendário externo (Google, e futuramente Outlook/Apple)."""

    key: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Client id/secret (e o que mais for preciso) estão configurados?"""

    @abstractmethod
    def get_authorize_url(self, state: str) -> str:
        """URL para redirecionar o usuário iniciar o consentimento OAuth."""

    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthTokens:
        """Troca o `code` do callback OAuth pelos tokens de acesso."""

    @abstractmethod
    async def refresh(self, tokens: OAuthTokens) -> OAuthTokens:
        """Renova o access token usando o refresh token salvo."""

    async def get_account_identifier(self, tokens: OAuthTokens) -> str | None:
        """E-mail/identificador da conta conectada, só para exibição na UI.

        Não é abstrato: um provedor pode simplesmente não implementar (volta
        `None`) sem quebrar a interface.
        """
        return None

    @abstractmethod
    async def list_calendars(self, tokens: OAuthTokens) -> list[RemoteCalendar]:
        """Lista os calendários disponíveis na conta conectada."""

    @abstractmethod
    async def list_events(
        self,
        tokens: OAuthTokens,
        calendar: RemoteCalendar,
        *,
        sync_token: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> RemoteEventPage:
        """Lista eventos de um calendário — sync completo (time_min/time_max) ou incremental (sync_token)."""

    @abstractmethod
    async def create_event(
        self,
        tokens: OAuthTokens,
        calendar: RemoteCalendar,
        *,
        title: str,
        description: str,
        start_utc: datetime,
        end_utc: datetime,
        timezone: str,
    ) -> str:
        """Cria um evento no provedor. Retorna o `external_id` do evento criado."""

    @abstractmethod
    async def update_event(
        self,
        tokens: OAuthTokens,
        calendar: RemoteCalendar,
        external_id: str,
        *,
        title: str,
        description: str,
        start_utc: datetime,
        end_utc: datetime,
        timezone: str,
    ) -> None:
        """Atualiza (PATCH) um evento já existente no provedor pelo `external_id` — nunca cria um novo."""

    @abstractmethod
    async def delete_event(self, tokens: OAuthTokens, calendar: RemoteCalendar, external_id: str) -> None:
        """Exclui um evento no provedor pelo `external_id`."""
