"""Recorrência: presets amigáveis + cron, e cálculo da próxima ocorrência.

Regra de fuso: o cálculo é feito em horário local (naive) do `timezone` do
schedule e só então convertido para UTC. Assim "todo dia às 09:00" continua
09:00 local mesmo que o fuso mude (o Brasil não tem mais horário de verão, mas
a lógica vale para qualquer fuso).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from croniter import croniter

_DOW = {
    "sun": 0, "sunday": 0, "dom": 0, "domingo": 0,
    "mon": 1, "monday": 1, "seg": 1, "segunda": 1,
    "tue": 2, "tuesday": 2, "ter": 2, "terca": 2, "terça": 2,
    "wed": 3, "wednesday": 3, "qua": 3, "quarta": 3,
    "thu": 4, "thursday": 4, "qui": 4, "quinta": 4,
    "fri": 5, "friday": 5, "sex": 5, "sexta": 5,
    "sat": 6, "saturday": 6, "sab": 6, "sábado": 6, "sabado": 6,
}

_TIME_RE = re.compile(r"^(?P<h>\d{1,2}):(?P<m>\d{2})$")


class RecurrenceError(ValueError):
    """Recorrência inválida."""


def parse_hhmm(token: str) -> tuple[int, int]:
    """"HH:MM" -> (hora, minuto), validado. Reaproveitado fora deste módulo
    (ex.: horário personalizado de automação em calendar_service.py)."""
    m = _TIME_RE.match(token)
    if not m:
        raise RecurrenceError(f"Horário inválido: {token!r} (use HH:MM)")
    h, mi = int(m["h"]), int(m["m"])
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        raise RecurrenceError(f"Horário fora do intervalo: {token!r}")
    return h, mi


def normalize_recurrence(value: str) -> str:
    """Converte presets em uma expressão cron de 5 campos. Cron entra e sai igual.

    Presets aceitos (case-insensitive):
      - "hourly"
      - "daily HH:MM"
      - "weekly <dia> HH:MM"       (dia: mon|seg|segunda|... )
      - "monthly <D> HH:MM"        (D: 1..31)
    """
    raw = value.strip()
    if croniter.is_valid(raw):
        return raw

    parts = raw.lower().split()
    if not parts:
        raise RecurrenceError("Recorrência vazia")

    kind = parts[0]
    if kind == "hourly" and len(parts) == 1:
        return "0 * * * *"

    if kind == "daily" and len(parts) == 2:
        h, mi = parse_hhmm(parts[1])
        return f"{mi} {h} * * *"

    if kind == "weekly" and len(parts) == 3:
        dow = _DOW.get(parts[1])
        if dow is None:
            raise RecurrenceError(f"Dia da semana inválido: {parts[1]!r}")
        h, mi = parse_hhmm(parts[2])
        return f"{mi} {h} * * {dow}"

    if kind == "monthly" and len(parts) == 3:
        try:
            day = int(parts[1])
        except ValueError as exc:
            raise RecurrenceError(f"Dia do mês inválido: {parts[1]!r}") from exc
        if not (1 <= day <= 31):
            raise RecurrenceError(f"Dia do mês fora do intervalo: {day}")
        h, mi = parse_hhmm(parts[2])
        return f"{mi} {h} {day} * *"

    raise RecurrenceError(
        f"Recorrência não reconhecida: {value!r}. "
        "Use cron (5 campos) ou um preset: 'daily 09:00', 'weekly mon 08:30', "
        "'monthly 1 12:00', 'hourly'."
    )


def local_to_utc(local_naive: datetime, tz_name: str) -> datetime:
    aware = local_naive.replace(tzinfo=ZoneInfo(tz_name))
    return aware.astimezone(timezone.utc).replace(tzinfo=None)


def utc_to_local(utc_naive: datetime, tz_name: str) -> datetime:
    aware = utc_naive.replace(tzinfo=timezone.utc)
    return aware.astimezone(ZoneInfo(tz_name)).replace(tzinfo=None)


def next_run_utc(cron_expr: str, tz_name: str, after_utc: datetime) -> datetime:
    """Próxima ocorrência do cron estritamente após `after_utc` (naive UTC)."""
    base_local = utc_to_local(after_utc, tz_name)
    itr = croniter(cron_expr, base_local)
    nxt_local: datetime = itr.get_next(datetime)
    return local_to_utc(nxt_local, tz_name)
