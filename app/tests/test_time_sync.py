from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
import respx

from whatsapp_scheduler import clock, time_sync


def test_clock_utcnow_applies_offset():
    before = clock.utcnow()
    clock.set_offset(timedelta(seconds=100))
    after = clock.utcnow()
    assert (after - before).total_seconds() == pytest.approx(100, abs=1)


def test_clock_utcnow_defaults_to_no_offset():
    assert clock.get_offset() == timedelta(0)


@respx.mock
async def test_sync_once_computes_and_applies_offset():
    # Servidor "diz" que são 100s no futuro em relação ao relógio local.
    fake_server_time = datetime.now(timezone.utc) + timedelta(seconds=100)
    respx.head("https://www.google.com/generate_204").mock(
        return_value=httpx.Response(204, headers={"Date": format_datetime(fake_server_time, usegmt=True)})
    )

    offset = await time_sync.sync_once()

    assert offset is not None
    assert offset.total_seconds() == pytest.approx(100, abs=2)
    assert clock.get_offset() == offset
    assert time_sync.last_synced_at is not None
    assert time_sync.last_sync_error is None


@respx.mock
async def test_sync_once_returns_none_and_keeps_old_offset_on_network_failure():
    clock.set_offset(timedelta(seconds=42))  # offset de uma sincronização anterior bem-sucedida
    respx.head("https://www.google.com/generate_204").mock(side_effect=httpx.ConnectError("boom"))

    offset = await time_sync.sync_once()

    assert offset is None
    assert clock.get_offset() == timedelta(seconds=42)  # não mexeu no offset anterior
    assert time_sync.last_sync_error is not None


@respx.mock
async def test_sync_once_returns_none_when_response_has_no_date_header():
    respx.head("https://www.google.com/generate_204").mock(return_value=httpx.Response(204))

    offset = await time_sync.sync_once()

    assert offset is None
    assert time_sync.last_sync_error is not None


@respx.mock
async def test_clock_sync_service_syncs_immediately_on_start_and_stops_cleanly():
    fake_server_time = datetime.now(timezone.utc) + timedelta(seconds=30)
    respx.head("https://www.google.com/generate_204").mock(
        return_value=httpx.Response(204, headers={"Date": format_datetime(fake_server_time, usegmt=True)})
    )

    service = time_sync.ClockSyncService()
    await service.start()
    try:
        assert clock.get_offset().total_seconds() == pytest.approx(30, abs=2)
    finally:
        await service.stop()
