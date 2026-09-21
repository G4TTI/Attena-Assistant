"""Regras de tempo (`timing.py`) — a única fonte de cálculo de horário do agendamento."""

from datetime import datetime, timedelta, timezone

import pytest

from whatsapp_scheduler import timing
from whatsapp_scheduler.errors import ValidationError

TZ = "America/Sao_Paulo"


# --------------------------------------------------------------------------- #
# Intervalo personalizado (HH:MM)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text, minutes",
    [("00:15", 15), ("00:30", 30), ("01:00", 60), ("01:45", 105), ("02:30", 150), ("10:00", 600), ("1:45", 105), (" 1:45 ", 105)],
)
def test_parse_interval_accepts_hhmm_and_friendly_forms(text, minutes):
    assert timing.parse_interval(text) == minutes


@pytest.mark.parametrize(
    "text",
    ["", "   ", "abc", "1:5", "1:60", "99:99", "-1:30", "1.45", "1h45", "1:45:00", ":30", "1:", "0:00", "00:00", "721:00"],
)
def test_parse_interval_rejects_invalid_values(text):
    with pytest.raises(ValidationError):
        timing.parse_interval(text)


def test_parse_interval_error_messages_are_clear():
    with pytest.raises(ValidationError, match="minutos"):
        timing.parse_interval("99:99")
    with pytest.raises(ValidationError, match="negativo"):
        timing.parse_interval("-0:30")
    with pytest.raises(ValidationError, match="maior que 0"):
        timing.parse_interval("0:00")
    with pytest.raises(ValidationError, match="HH:MM"):
        timing.parse_interval("banana")


def test_interval_is_normalized_to_one_canonical_form():
    assert timing.format_interval(timing.parse_interval("01:45")) == "1:45"
    assert timing.format_interval(105) == "1:45"
    assert timing.format_interval(600) == "10:00"
    assert timing.format_interval(15) == "0:15"
    assert timing.describe_interval(105) == "1h45"
    assert timing.describe_interval(120) == "2h"
    assert timing.describe_interval(15) == "15min"


# --------------------------------------------------------------------------- #
# Regra relativa ao evento: antes / depois / no momento (Testes 5 e 6)
# --------------------------------------------------------------------------- #
def _event_utc(hour_local: int = 20) -> datetime:
    # 20/09/2026 às 20:00 em São Paulo (UTC-3, sem horário de verão) = 23:00 UTC
    return timing.to_utc(datetime(2026, 9, 20, hour_local, 0), TZ)


def test_custom_interval_before_event_1h45_is_18_15():
    rule = timing.build_offset_rule("before", "custom", "1:45")
    assert (rule.direction, rule.amount, rule.unit, rule.custom_interval) == ("before", 105, "minutes", "1:45")
    target = timing.target_utc_for_rule(_event_utc(), rule, event_timezone=TZ)
    assert timing.to_local(target, TZ) == datetime(2026, 9, 20, 18, 15)


def test_custom_interval_after_event_1h45_is_21_45():
    rule = timing.build_offset_rule("after", "custom", "1:45")
    target = timing.target_utc_for_rule(_event_utc(), rule, event_timezone=TZ)
    assert timing.to_local(target, TZ) == datetime(2026, 9, 20, 21, 45)


def test_custom_interval_is_relative_never_a_wall_clock_time():
    """"1:45" NÃO é 01:45 da manhã: é uma distância do evento."""
    rule = timing.build_offset_rule("before", "custom", "1:45")
    target = timing.to_local(timing.target_utc_for_rule(_event_utc(), rule, event_timezone=TZ), TZ)
    assert target.hour != 1 and target.date() == datetime(2026, 9, 20).date()


def test_at_event_ignores_any_interval():
    rule = timing.build_offset_rule("at", "custom", "1:45")
    assert (rule.amount, rule.unit) == (0, "minutes")
    assert timing.target_utc_for_rule(_event_utc(), rule, event_timezone=TZ) == _event_utc()


def test_preset_intervals_still_work():
    rule = timing.build_offset_rule("before", "2:hours")
    assert (rule.amount, rule.unit, rule.custom_interval) == (2, "hours", None)
    assert timing.to_local(timing.target_utc_for_rule(_event_utc(), rule, event_timezone=TZ), TZ).hour == 18
    rule = timing.build_offset_rule("after", "1:weeks")
    assert timing.target_utc_for_rule(_event_utc(), rule, event_timezone=TZ) == _event_utc() + timedelta(weeks=1)


def test_custom_interval_crossing_midnight_keeps_the_right_date():
    event = timing.to_utc(datetime(2026, 9, 20, 0, 30), TZ)
    rule = timing.build_offset_rule("before", "custom", "1:45")
    assert timing.to_local(timing.target_utc_for_rule(event, rule, event_timezone=TZ), TZ) == datetime(2026, 9, 19, 22, 45)


def test_build_offset_rule_rejects_bad_input():
    with pytest.raises(ValidationError):
        timing.build_offset_rule("sometime", "2:hours")
    with pytest.raises(ValidationError):
        timing.build_offset_rule("before", "2:fortnights")
    with pytest.raises(ValidationError):
        timing.build_offset_rule("before", "0:hours")
    with pytest.raises(ValidationError):
        timing.build_offset_rule("before", "custom", "")
    with pytest.raises(ValidationError):
        timing.build_offset_rule("custom", None, custom_time="")
    with pytest.raises(ValidationError):
        timing.build_offset_rule("custom", None, custom_time="25:00")


def test_fixed_time_of_day_rule_is_still_supported():
    rule = timing.build_offset_rule("custom", None, custom_time="18:00")
    assert rule.custom_time_local == "18:00"
    target = timing.target_utc_for_rule(_event_utc(), rule, event_timezone=TZ)
    assert timing.to_local(target, TZ) == datetime(2026, 9, 20, 18, 0)


def test_rule_descriptions_for_the_summary():
    assert timing.describe_rule(timing.build_offset_rule("before", "custom", "1:45")) == "1h45 antes"
    assert timing.describe_rule(timing.build_offset_rule("after", "custom", "1:45")) == "1h45 depois"
    assert timing.describe_rule(timing.build_offset_rule("before", "2:hours")) == "2h antes"
    assert timing.describe_rule(timing.build_offset_rule("after", "1:days")) == "1 dia depois"
    assert timing.describe_rule(timing.build_offset_rule("at", None)) == "no momento do evento"


def test_edit_form_keeps_personalizado_value():
    """Teste 16: uma automação com "Personalizado · 1:45" volta exatamente assim."""
    assert timing.interval_form_values(105, "minutes", "1:45") == ("custom", "1:45")
    # Sem o texto guardado (regra antiga/da API) e fora das opções prontas -> Personalizado, sem perder o valor.
    assert timing.interval_form_values(45, "minutes", None) == ("custom", "0:45")
    # Preset continua preset.
    assert timing.interval_form_values(2, "hours", None) == ("2:hours", "")


# --------------------------------------------------------------------------- #
# Início da sequência + fuso
# --------------------------------------------------------------------------- #
def test_sequence_times_never_move_the_start():
    start = datetime(2026, 9, 20, 21, 0)
    times = timing.sequence_times_utc(start, 3, 3)
    assert times[0] == start
    assert [t - start for t in times] == [timedelta(0), timedelta(seconds=3), timedelta(seconds=6)]


def test_local_time_converts_through_zoneinfo_not_manual_offsets():
    assert timing.to_utc(datetime(2026, 9, 20, 18, 0), TZ) == datetime(2026, 9, 20, 21, 0)
    assert timing.to_local(datetime(2026, 9, 20, 21, 0), TZ) == datetime(2026, 9, 20, 18, 0)
    # Um fuso com horário de verão: o offset muda sozinho (nenhum "+3h" fixo em lugar nenhum).
    assert timing.to_utc(datetime(2026, 1, 15, 12, 0), "Europe/Lisbon") == datetime(2026, 1, 15, 12, 0)
    assert timing.to_utc(datetime(2026, 7, 15, 12, 0), "Europe/Lisbon") == datetime(2026, 7, 15, 11, 0)


def test_resolve_local_naive_is_kept_and_aware_is_converted():
    assert timing.resolve_local(datetime(2026, 9, 20, 18, 0), TZ) == datetime(2026, 9, 20, 18, 0)
    aware = datetime(2026, 9, 20, 21, 0, tzinfo=timezone.utc)
    assert timing.resolve_local(aware, TZ) == datetime(2026, 9, 20, 18, 0)


def test_parse_local_input_and_errors():
    assert timing.parse_local_input("2026-09-20", "18:00") == datetime(2026, 9, 20, 18, 0)
    assert timing.parse_local_input("2026-09-20", "18:00:30") == datetime(2026, 9, 20, 18, 0, 30)
    for bad in [("", "18:00"), ("2026-09-20", ""), ("20/09/2026", "18:00"), ("2026-13-40", "18:00"), ("2026-09-20", "25:00")]:
        with pytest.raises(ValidationError):
            timing.parse_local_input(*bad)


def test_suggested_start_is_in_the_future_rounded_to_5_minutes():
    now = datetime(2026, 9, 21, 14, 2, 30)  # 11:02 em São Paulo
    suggestion = timing.suggest_start_local(now, TZ)
    assert suggestion == datetime(2026, 9, 21, 11, 35)
    assert suggestion.minute % 5 == 0 and suggestion.second == 0


def test_timezone_label_is_friendly():
    assert timing.tz_label("America/Sao_Paulo") == "São Paulo"
    assert timing.tz_label("America/Argentina/Buenos_Aires") == "Buenos Aires"
    assert timing.tz_label(None) == ""
    with pytest.raises(ValidationError):
        timing.validate_timezone("Mars/Olympus")
