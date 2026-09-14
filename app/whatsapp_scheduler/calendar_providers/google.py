"""Provedor Google Calendar: chama a API REST direto via httpx (sem SDK),
espelhando o mesmo padrão de `waha.py` (cliente HTTP fino + erro dedicado).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

import httpx

from ..config import settings
from .base import (
    CalendarProvider,
    CalendarProviderError,
    OAuthTokens,
    RemoteCalendar,
    RemoteEvent,
    RemoteEventPage,
    SyncTokenExpired,
)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://www.googleapis.com/calendar/v3"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
# calendar (leitura+escrita) é necessário desde o incremento 3 (criar/editar/
# excluir eventos internos vinculados a um calendário Google); userinfo.email
# só serve para rotular qual conta está conectada na UI. Contas conectadas
# antes desta mudança mantêm o token com o escopo antigo (calendar.readonly)
# para sempre — o Google não amplia escopo de um refresh token sozinho — por
# isso a UI de Configurações avisa quando `connection.scope` ainda não
# contém escopo de escrita e pede para reconectar.
SCOPE = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email"


class GoogleCalendarError(CalendarProviderError):
    """Erro de comunicação com a API do Google Calendar."""


class GoogleSyncTokenExpired(SyncTokenExpired):
    """Google respondeu 410: o `syncToken` não é mais válido, refazer sync completo."""


def _rfc3339(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_start_end(value: dict, calendar_tz: str) -> tuple[datetime, str, bool]:
    """Retorna (utc_naive, timezone_efetiva, all_day)."""
    if "date" in value:
        naive_local = datetime.strptime(value["date"], "%Y-%m-%d")
        aware = naive_local.replace(tzinfo=ZoneInfo(calendar_tz))
        return aware.astimezone(timezone.utc).replace(tzinfo=None), calendar_tz, True
    tz_name = value.get("timeZone") or calendar_tz
    dt = _parse_iso(value["dateTime"])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    return dt.astimezone(timezone.utc).replace(tzinfo=None), tz_name, False


def _to_remote_event(item: dict, calendar_tz: str) -> RemoteEvent:
    cancelled = item.get("status") == "cancelled"
    start_utc = end_utc = None
    tz_name: str | None = None
    all_day = False
    if not cancelled:
        start_utc, tz_name, all_day = _parse_start_end(item.get("start") or {}, calendar_tz)
        end_utc, _, _ = _parse_start_end(item.get("end") or {}, calendar_tz)

    provider_updated_at = None
    updated = item.get("updated")
    if updated:
        provider_updated_at = _parse_iso(updated).astimezone(timezone.utc).replace(tzinfo=None)

    return RemoteEvent(
        external_id=item["id"],
        title=item.get("summary") or "(sem título)",
        description=item.get("description") or "",
        start_utc=start_utc,
        end_utc=end_utc,
        timezone=tz_name,
        all_day=all_day,
        cancelled=cancelled,
        recurring_event_id=item.get("recurringEventId"),
        provider_updated_at=provider_updated_at,
    )


class GoogleCalendarClient:
    """Chamadas HTTP cruas: OAuth2 (accounts/oauth2.googleapis.com) + Calendar v3."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = await self._client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise GoogleCalendarError(f"Falha de conexão com o Google: {exc}") from exc
        if resp.status_code == 410:
            raise GoogleSyncTokenExpired("Google respondeu 410: syncToken expirado.")
        if resp.status_code >= 400:
            raise GoogleCalendarError(f"Google respondeu {resp.status_code} em {method} {url}: {resp.text[:500]}")
        return resp

    async def exchange_code(self, *, client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
        resp = await self._request(
            "POST",
            TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        return resp.json()

    async def refresh_token(self, *, client_id: str, client_secret: str, refresh_token: str) -> dict:
        resp = await self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        return resp.json()

    async def get_userinfo(self, access_token: str) -> dict:
        resp = await self._request(
            "GET",
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return resp.json()

    async def list_calendars(self, access_token: str) -> list[dict]:
        resp = await self._request(
            "GET",
            f"{API_BASE}/users/me/calendarList",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return list(resp.json().get("items") or [])

    async def list_events_page(
        self,
        access_token: str,
        calendar_external_id: str,
        *,
        page_token: str | None = None,
        sync_token: str | None = None,
        time_min: str | None = None,
        time_max: str | None = None,
    ) -> dict:
        params: dict[str, str] = {"singleEvents": "true", "maxResults": "250"}
        if sync_token:
            # syncToken não pode ser combinado com orderBy/timeMin/timeMax/etc.
            params["syncToken"] = sync_token
        else:
            params["orderBy"] = "startTime"
            if time_min:
                params["timeMin"] = time_min
            if time_max:
                params["timeMax"] = time_max
        if page_token:
            params["pageToken"] = page_token
        cal_path = quote(calendar_external_id, safe="")
        resp = await self._request(
            "GET",
            f"{API_BASE}/calendars/{cal_path}/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        return resp.json()

    async def insert_event(self, access_token: str, calendar_external_id: str, body: dict) -> dict:
        cal_path = quote(calendar_external_id, safe="")
        resp = await self._request(
            "POST",
            f"{API_BASE}/calendars/{cal_path}/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )
        return resp.json()

    async def patch_event(self, access_token: str, calendar_external_id: str, event_id: str, body: dict) -> dict:
        cal_path = quote(calendar_external_id, safe="")
        ev_path = quote(event_id, safe="")
        resp = await self._request(
            "PATCH",
            f"{API_BASE}/calendars/{cal_path}/events/{ev_path}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )
        return resp.json()

    async def delete_event(self, access_token: str, calendar_external_id: str, event_id: str) -> None:
        cal_path = quote(calendar_external_id, safe="")
        ev_path = quote(event_id, safe="")
        try:
            resp = await self._client.request(
                "DELETE",
                f"{API_BASE}/calendars/{cal_path}/events/{ev_path}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.HTTPError as exc:
            raise GoogleCalendarError(f"Falha de conexão com o Google: {exc}") from exc
        # 404/410/text-status "cancelled" (já removido do lado do Google) não é
        # erro pro chamador — o objetivo (evento não existir mais) já está atingido.
        if resp.status_code >= 400 and resp.status_code not in (404, 410):
            raise GoogleCalendarError(f"Google respondeu {resp.status_code} ao excluir evento: {resp.text[:500]}")


class GoogleCalendarProvider(CalendarProvider):
    key = "google"

    def __init__(self, client: GoogleCalendarClient | None = None) -> None:
        self._client = client or GoogleCalendarClient()

    def is_configured(self) -> bool:
        return bool(settings.google_client_id.strip() and settings.google_client_secret.strip())

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise GoogleCalendarError(
                "Google Calendar não configurado. Defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env."
            )

    def get_authorize_url(self, state: str) -> str:
        self._require_configured()
        params = {
            "response_type": "code",
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def _tokens_from_response(self, data: dict, *, fallback_refresh_token: str | None) -> OAuthTokens:
        access_token = data.get("access_token")
        if not access_token:
            raise GoogleCalendarError(f"Resposta do Google sem access_token: {data}")
        # Num refresh normal o Google não reenvia refresh_token — nunca sobrescrever com nulo.
        refresh_token = data.get("refresh_token") or fallback_refresh_token
        if not refresh_token:
            raise GoogleCalendarError(
                "Google não retornou refresh_token e nenhum estava salvo. Revogue o acesso em "
                "myaccount.google.com/permissions e conecte a conta de novo."
            )
        expires_in = int(data.get("expires_in") or 3600)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=expires_in)
        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=data.get("scope", SCOPE),
        )

    async def exchange_code(self, code: str) -> OAuthTokens:
        self._require_configured()
        data = await self._client.exchange_code(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            redirect_uri=settings.google_oauth_redirect_uri,
            code=code,
        )
        return self._tokens_from_response(data, fallback_refresh_token=None)

    async def refresh(self, tokens: OAuthTokens) -> OAuthTokens:
        self._require_configured()
        data = await self._client.refresh_token(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            refresh_token=tokens.refresh_token,
        )
        return self._tokens_from_response(data, fallback_refresh_token=tokens.refresh_token)

    async def get_account_identifier(self, tokens: OAuthTokens) -> str | None:
        try:
            info = await self._client.get_userinfo(tokens.access_token)
        except GoogleCalendarError:
            return None
        email = info.get("email")
        return str(email) if email else None

    async def list_calendars(self, tokens: OAuthTokens) -> list[RemoteCalendar]:
        items = await self._client.list_calendars(tokens.access_token)
        return [
            RemoteCalendar(
                external_id=item["id"],
                name=item.get("summary") or item["id"],
                time_zone=item.get("timeZone") or "UTC",
                color=item.get("backgroundColor"),
                primary=bool(item.get("primary")),
            )
            for item in items
        ]

    async def list_events(
        self,
        tokens: OAuthTokens,
        calendar: RemoteCalendar,
        *,
        sync_token: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> RemoteEventPage:
        events: list[RemoteEvent] = []
        page_token: str | None = None
        next_sync_token: str | None = None
        time_min_s = _rfc3339(time_min) if time_min else None
        time_max_s = _rfc3339(time_max) if time_max else None
        try:
            while True:
                page = await self._client.list_events_page(
                    tokens.access_token,
                    calendar.external_id,
                    page_token=page_token,
                    sync_token=sync_token,
                    time_min=time_min_s,
                    time_max=time_max_s,
                )
                for item in page.get("items") or []:
                    events.append(_to_remote_event(item, calendar.time_zone))
                next_sync_token = page.get("nextSyncToken") or next_sync_token
                page_token = page.get("nextPageToken")
                if not page_token:
                    break
        except GoogleSyncTokenExpired:
            return RemoteEventPage(events=[], next_sync_token=None, sync_token_invalid=True)
        return RemoteEventPage(events=events, next_sync_token=next_sync_token)

    @staticmethod
    def _event_body(*, title: str, description: str, start_utc: datetime, end_utc: datetime, timezone: str) -> dict:
        return {
            "summary": title,
            "description": description,
            "start": {"dateTime": _rfc3339(start_utc), "timeZone": timezone},
            "end": {"dateTime": _rfc3339(end_utc), "timeZone": timezone},
        }

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
        body = self._event_body(
            title=title, description=description, start_utc=start_utc, end_utc=end_utc, timezone=timezone
        )
        created = await self._client.insert_event(tokens.access_token, calendar.external_id, body)
        external_id = created.get("id")
        if not external_id:
            raise GoogleCalendarError(f"Google não retornou id do evento criado: {created}")
        return str(external_id)

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
        body = self._event_body(
            title=title, description=description, start_utc=start_utc, end_utc=end_utc, timezone=timezone
        )
        await self._client.patch_event(tokens.access_token, calendar.external_id, external_id, body)

    async def delete_event(self, tokens: OAuthTokens, calendar: RemoteCalendar, external_id: str) -> None:
        await self._client.delete_event(tokens.access_token, calendar.external_id, external_id)
