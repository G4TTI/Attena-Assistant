from datetime import datetime

import pytest

from whatsapp_scheduler.recurrence import (
    RecurrenceError,
    local_to_utc,
    next_run_utc,
    normalize_recurrence,
    utc_to_local,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0 9 * * 1-5", "0 9 * * 1-5"),
        ("daily 09:00", "0 9 * * *"),
        ("daily 7:05", "5 7 * * *"),
        ("weekly mon 08:30", "30 8 * * 1"),
        ("weekly domingo 22:00", "0 22 * * 0"),
        ("monthly 1 12:00", "0 12 1 * *"),
        ("hourly", "0 * * * *"),
    ],
)
def test_normalize_recurrence(value, expected):
    assert normalize_recurrence(value) == expected


@pytest.mark.parametrize("value", ["daily", "weekly xx 09:00", "monthly 40 09:00", "banana", "daily 25:00"])
def test_normalize_recurrence_invalid(value):
    with pytest.raises(RecurrenceError):
        normalize_recurrence(value)


def test_timezone_roundtrip():
    local = datetime(2026, 3, 15, 9, 0)
    utc = local_to_utc(local, "America/Sao_Paulo")
    assert utc == datetime(2026, 3, 15, 12, 0)  # UTC-3, sem horário de verão
    assert utc_to_local(utc, "America/Sao_Paulo") == local


def test_next_run_utc_respects_timezone():
    # 2026-03-15 06:00Z == 03:00 em São Paulo. Próximo "09:00 diário" -> mesmo dia 12:00Z.
    after = datetime(2026, 3, 15, 6, 0)
    nxt = next_run_utc("0 9 * * *", "America/Sao_Paulo", after)
    assert nxt == datetime(2026, 3, 15, 12, 0)


def test_next_run_utc_rolls_to_next_day():
    after = datetime(2026, 3, 15, 15, 0)  # 12:00 local, já passou das 09:00
    nxt = next_run_utc("0 9 * * *", "America/Sao_Paulo", after)
    assert nxt == datetime(2026, 3, 16, 12, 0)
