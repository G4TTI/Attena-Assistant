from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from whatsapp_scheduler.calendar_providers.base import OAuthTokens, RemoteCalendar
from whatsapp_scheduler.calendar_providers.google import (
    API_BASE,
    AUTH_URL,
    TOKEN_URL,
    GoogleCalendarError,
    GoogleCalendarProvider,
)


@pytest.fixture
async def provider():
    p = GoogleCalendarProvider()
    yield p
    await p._client.aclose()


def test_authorize_url_has_expected_params(provider):
    url = provider.get_authorize_url("state-123")
    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == AUTH_URL
    qs = parse_qs(parsed.query)
    assert qs["response_type"] == ["code"]
    assert qs["client_id"] == ["test-client-id"]
    assert qs["redirect_uri"] == ["http://localhost:8090/calendario/oauth/callback"]
    assert qs["scope"] == [
        "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email"
    ]
    assert qs["access_type"] == ["offline"]
    assert qs["prompt"] == ["consent"]
    assert qs["state"] == ["state-123"]


@respx.mock
async def test_exchange_code_returns_tokens(provider):
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "acc1", "refresh_token": "ref1", "expires_in": 3600, "scope": "calendar.readonly"},
        )
    )
    tokens = await provider.exchange_code("the-code")
    assert tokens.access_token == "acc1"
    assert tokens.refresh_token == "ref1"
    assert tokens.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)


@respx.mock
async def test_refresh_preserves_refresh_token_when_response_omits_it(provider):
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "acc2", "expires_in": 3600}))
    old = OAuthTokens(access_token="old", refresh_token="keep-me", expires_at=datetime.now(timezone.utc))
    tokens = await provider.refresh(old)
    assert tokens.access_token == "acc2"
    assert tokens.refresh_token == "keep-me"


@respx.mock
async def test_refresh_raises_if_no_refresh_token_anywhere(provider):
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"access_token": "acc3", "expires_in": 3600}))
    old = OAuthTokens(access_token="old", refresh_token="", expires_at=datetime.now(timezone.utc))
    with pytest.raises(GoogleCalendarError):
        await provider.refresh(old)


@respx.mock
async def test_list_calendars_maps_fields(provider):
    respx.get(f"{API_BASE}/users/me/calendarList").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {"id": "primary", "summary": "Meu calendário", "timeZone": "America/Sao_Paulo", "primary": True},
                    {"id": "work@group.calendar.google.com", "summary": "Trabalho", "timeZone": "UTC"},
                ]
            },
        )
    )
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cals = await provider.list_calendars(tokens)
    assert [c.external_id for c in cals] == ["primary", "work@group.calendar.google.com"]
    assert cals[0].primary is True
    assert cals[1].time_zone == "UTC"


@respx.mock
async def test_bootstrap_sync_uses_time_bounds_no_sync_token(provider):
    route = respx.get(f"{API_BASE}/calendars/primary/events").mock(
        return_value=httpx.Response(200, json={"items": [], "nextSyncToken": "tok-1"})
    )
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cal = RemoteCalendar(external_id="primary", name="Meu calendário", time_zone="America/Sao_Paulo")
    page = await provider.list_events(
        tokens,
        cal,
        time_min=datetime(2026, 1, 1, tzinfo=timezone.utc),
        time_max=datetime(2026, 12, 31, tzinfo=timezone.utc),
    )
    assert page.next_sync_token == "tok-1"
    sent = dict(route.calls.last.request.url.params)
    assert "syncToken" not in sent
    assert sent["singleEvents"] == "true"
    assert sent["orderBy"] == "startTime"
    assert "timeMin" in sent and "timeMax" in sent


@respx.mock
async def test_incremental_sync_uses_only_sync_token(provider):
    route = respx.get(f"{API_BASE}/calendars/primary/events").mock(
        return_value=httpx.Response(200, json={"items": [], "nextSyncToken": "tok-2"})
    )
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cal = RemoteCalendar(external_id="primary", name="Meu calendário", time_zone="UTC")
    page = await provider.list_events(tokens, cal, sync_token="tok-1")
    assert page.next_sync_token == "tok-2"
    sent = dict(route.calls.last.request.url.params)
    assert sent["syncToken"] == "tok-1"
    assert "orderBy" not in sent
    assert "timeMin" not in sent
    assert "timeMax" not in sent


@respx.mock
async def test_expired_sync_token_returns_invalid_flag(provider):
    respx.get(f"{API_BASE}/calendars/primary/events").mock(return_value=httpx.Response(410))
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cal = RemoteCalendar(external_id="primary", name="Meu calendário", time_zone="UTC")
    page = await provider.list_events(tokens, cal, sync_token="stale-token")
    assert page.sync_token_invalid is True
    assert page.events == []


@respx.mock
async def test_pagination_follows_next_page_token(provider):
    route = respx.get(f"{API_BASE}/calendars/primary/events")
    ev = {
        "status": "confirmed",
        "start": {"dateTime": "2026-01-01T10:00:00Z"},
        "end": {"dateTime": "2026-01-01T11:00:00Z"},
    }
    route.side_effect = [
        httpx.Response(200, json={"items": [{**ev, "id": "e1"}], "nextPageToken": "p2"}),
        httpx.Response(200, json={"items": [{**ev, "id": "e2"}], "nextSyncToken": "final-token"}),
    ]
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cal = RemoteCalendar(external_id="primary", name="Meu calendário", time_zone="UTC")
    page = await provider.list_events(tokens, cal, time_min=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert [e.external_id for e in page.events] == ["e1", "e2"]
    assert page.next_sync_token == "final-token"


@respx.mock
async def test_event_mapping_all_day_and_cancelled(provider):
    respx.get(f"{API_BASE}/calendars/primary/events").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "timed-1",
                        "status": "confirmed",
                        "summary": "Consulta com Leonardo",
                        "start": {"dateTime": "2026-09-20T14:00:00-03:00", "timeZone": "America/Sao_Paulo"},
                        "end": {"dateTime": "2026-09-20T15:00:00-03:00", "timeZone": "America/Sao_Paulo"},
                        "updated": "2026-09-10T10:00:00Z",
                    },
                    {
                        "id": "allday-1",
                        "status": "confirmed",
                        "summary": "Feriado",
                        "start": {"date": "2026-09-21"},
                        "end": {"date": "2026-09-22"},
                    },
                    {"id": "cancelled-1", "status": "cancelled"},
                ],
                "nextSyncToken": "tok-3",
            },
        )
    )
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cal = RemoteCalendar(external_id="primary", name="Meu calendário", time_zone="America/Sao_Paulo")
    page = await provider.list_events(tokens, cal, sync_token="tok-2")

    timed = next(e for e in page.events if e.external_id == "timed-1")
    assert timed.start_utc == datetime(2026, 9, 20, 17, 0)  # 14:00 -03:00 -> 17:00 UTC
    assert timed.cancelled is False

    allday = next(e for e in page.events if e.external_id == "allday-1")
    assert allday.all_day is True
    assert allday.start_utc is not None  # ancorado na timezone do calendário

    cancelled = next(e for e in page.events if e.external_id == "cancelled-1")
    assert cancelled.cancelled is True
    assert cancelled.start_utc is None
    assert cancelled.end_utc is None


@respx.mock
async def test_create_event_posts_body_and_returns_external_id(provider):
    route = respx.post(f"{API_BASE}/calendars/primary/events").mock(
        return_value=httpx.Response(200, json={"id": "new-ext-id"})
    )
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cal = RemoteCalendar(external_id="primary", name="Meu calendário", time_zone="America/Sao_Paulo")
    external_id = await provider.create_event(
        tokens, cal, title="Consulta", description="desc",
        start_utc=datetime(2026, 9, 20, 17, 0), end_utc=datetime(2026, 9, 20, 18, 0),
        timezone="America/Sao_Paulo",
    )
    assert external_id == "new-ext-id"
    sent_body = route.calls.last.request.content
    assert b"Consulta" in sent_body


@respx.mock
async def test_update_event_patches_existing_id_never_creates(provider):
    route = respx.patch(f"{API_BASE}/calendars/primary/events/ext-1").mock(
        return_value=httpx.Response(200, json={"id": "ext-1"})
    )
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cal = RemoteCalendar(external_id="primary", name="Meu calendário", time_zone="America/Sao_Paulo")
    await provider.update_event(
        tokens, cal, "ext-1", title="Novo título", description="", start_utc=datetime(2026, 9, 20, 18, 0),
        end_utc=datetime(2026, 9, 20, 19, 0), timezone="America/Sao_Paulo",
    )
    assert route.calls.call_count == 1


@respx.mock
async def test_delete_event_treats_404_as_already_gone(provider):
    respx.delete(f"{API_BASE}/calendars/primary/events/ext-1").mock(return_value=httpx.Response(404))
    tokens = OAuthTokens(access_token="acc", refresh_token="ref", expires_at=datetime.now(timezone.utc))
    cal = RemoteCalendar(external_id="primary", name="Meu calendário", time_zone="America/Sao_Paulo")
    await provider.delete_event(tokens, cal, "ext-1")  # não deve levantar
