"""Regras de TEMPO do agendamento — a única fonte de cálculo de horário.

Tudo o que decide "quando esta mensagem sai" passa por aqui: Conversas,
Agendamentos e o Calendário (automações) chamam as mesmas funções, e o preview
do formulário de automação também (a rota `/ui/calendario/.../automation-preview`
só formata o que estas funções devolvem). Nada aqui toca banco ou rede.

Convenções:
- Um horário digitado pelo usuário é sempre um horário de PAREDE (naive) no
  fuso do usuário (`User.timezone`). Ele só vira UTC em `to_utc`, uma vez.
- O banco guarda `first_run_local` (naive) + `timezone`; dispatches guardam UTC.
- Nunca somar/subtrair "3 horas" na mão: a conversão é sempre via ZoneInfo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from datetime import time as dt_time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .errors import ValidationError
from .recurrence import RecurrenceError, local_to_utc, parse_hhmm, utc_to_local

# Intervalo entre uma mensagem e a próxima de uma mesma sequência. Já era o
# valor usado pelas automações (`Automation.message_gap_seconds`); agora é o
# padrão de TODA sequência (Conversas/Agendamentos também).
DEFAULT_MESSAGE_GAP_SECONDS = 3
DEFAULT_MAX_ATTEMPTS = 3
MAX_MESSAGES_PER_SEQUENCE = 20
MAX_MESSAGE_LENGTH = 4096

UNIT_MINUTES: dict[str, int] = {"minutes": 1, "hours": 60, "days": 1440, "weeks": 10080}
# Teto do intervalo personalizado: 30 dias (as opções prontas vão até 1 semana).
MAX_CUSTOM_INTERVAL_MINUTES = 30 * 1440

# (valor do <option>, rótulo) — fonte única das opções do seletor "Intervalo".
INTERVAL_PRESETS: list[tuple[str, str]] = [
    ("5:minutes", "5 minutos"), ("10:minutes", "10 minutos"), ("15:minutes", "15 minutos"),
    ("30:minutes", "30 minutos"), ("1:hours", "1 hora"), ("2:hours", "2 horas"), ("3:hours", "3 horas"),
    ("6:hours", "6 horas"), ("12:hours", "12 horas"), ("1:days", "1 dia"), ("2:days", "2 dias"),
    ("3:days", "3 dias"), ("1:weeks", "1 semana"),
]
CUSTOM_INTERVAL_VALUE = "custom"
DEFAULT_INTERVAL_VALUE = "2:hours"

DIRECTION_LABELS = {
    "before": "Antes do evento",
    "at": "No momento do evento",
    "after": "Depois do evento",
    "custom": "Horário fixo no dia do evento",
}
VALID_DIRECTIONS = tuple(DIRECTION_LABELS)

_INTERVAL_RE = re.compile(r"^(\d{1,3}):(\d{2})$")

# Faixa de datas aceita num agendamento — fora dela a conversão de fuso estoura (OverflowError) e viraria erro 500.
MIN_YEAR, MAX_YEAR = 2000, 3000


# --------------------------------------------------------------------------- #
# Fuso horário
# --------------------------------------------------------------------------- #
def validate_timezone(tz_name: str) -> str:
    tz_name = (tz_name or "").strip()
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"Timezone inválida: {tz_name!r}") from exc
    return tz_name


def to_utc(local_naive: datetime, tz_name: str) -> datetime:
    """Horário de parede no fuso `tz_name` -> UTC naive."""
    return local_to_utc(local_naive, tz_name)


def to_local(utc_naive: datetime, tz_name: str) -> datetime:
    """UTC naive -> horário de parede naive no fuso `tz_name`."""
    return utc_to_local(utc_naive, tz_name)


def resolve_local(send_at: datetime, tz_name: str) -> datetime:
    """Normaliza o "quando" recebido: com offset (ISO com Z/+03:00) é convertido
    pro fuso `tz_name`; sem offset já é o horário de parede do usuário."""
    if send_at.tzinfo is not None:
        return send_at.astimezone(ZoneInfo(tz_name)).replace(tzinfo=None)
    return send_at


_TZ_LABELS = {
    "America/Sao_Paulo": "São Paulo", "America/Manaus": "Manaus", "America/Rio_Branco": "Rio Branco",
    "America/Cuiaba": "Cuiabá", "America/Recife": "Recife", "America/Fortaleza": "Fortaleza",
    "America/Belem": "Belém", "America/Bahia": "Salvador", "America/Noronha": "Fernando de Noronha",
    "America/New_York": "Nova York", "America/Los_Angeles": "Los Angeles", "Europe/Lisbon": "Lisboa",
    "Europe/London": "Londres", "Asia/Tokyo": "Tóquio", "UTC": "UTC",
}


def tz_label(tz_name: str | None) -> str:
    """"America/Sao_Paulo" -> "São Paulo" (só pra exibição discreta)."""
    if not tz_name:
        return ""
    if tz_name in _TZ_LABELS:
        return _TZ_LABELS[tz_name]
    return tz_name.rsplit("/", 1)[-1].replace("_", " ")


def check_year(local: datetime) -> datetime:
    if not (MIN_YEAR <= local.year <= MAX_YEAR):
        raise ValidationError(f"Data fora do intervalo aceito ({MIN_YEAR} a {MAX_YEAR}).")
    return local


def parse_local_input(date_str: str | None, time_str: str | None) -> datetime:
    """`<input type=date>` ("2026-09-20") + `<input type=time>` ("18:00") ->
    horário de parede naive. Aceita segundos ("18:00:00")."""
    date_str, time_str = (date_str or "").strip(), (time_str or "").strip()
    if not date_str or not time_str:
        raise ValidationError("Informe a data e o horário do envio.")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return check_year(datetime.strptime(f"{date_str} {time_str}", fmt))
        except ValueError as exc:
            if isinstance(exc, ValidationError):
                raise
            continue
    raise ValidationError(f"Data/hora inválida: {date_str} {time_str}")


def suggest_start_local(now_utc: datetime, tz_name: str, *, minutes_ahead: int = 30) -> datetime:
    """Sugestão de horário para um formulário novo: agora + 30 min, arredondado
    pra cima em múltiplos de 5 min, no fuso do usuário. É só o valor inicial —
    depois que o usuário digita um horário, ele nunca é trocado por este."""
    local = to_local(now_utc, tz_name) + timedelta(minutes=minutes_ahead)
    local = local.replace(second=0, microsecond=0)
    return local + timedelta(minutes=(-local.minute) % 5)


def parse_send_at(send_at: str | None) -> datetime:
    """ISO 8601 ("2026-09-20T18:00" do antigo `datetime-local`, com ou sem offset)."""
    try:
        return datetime.fromisoformat((send_at or "").strip())
    except ValueError as exc:
        raise ValidationError("Data/hora inválida.") from exc


# --------------------------------------------------------------------------- #
# Sequência de mensagens
# --------------------------------------------------------------------------- #
def sequence_times_utc(start_utc: datetime, count: int, gap_seconds: int) -> list[datetime]:
    """Horário (UTC) de cada mensagem: a 1ª é EXATAMENTE `start_utc`; as
    seguintes só somam o intervalo entre mensagens. Nunca altera o início."""
    return [start_utc + timedelta(seconds=i * gap_seconds) for i in range(count)]


# --------------------------------------------------------------------------- #
# Intervalo relativo ao evento (antes/depois) — presets + personalizado HH:MM
# --------------------------------------------------------------------------- #
def parse_interval(text: str | None) -> int:
    """"1:45" -> 105 (minutos). Aceita H:MM, HH:MM e HHH:MM; minutos sempre com
    2 dígitos. Recusa vazio, negativo, minutos >= 60 e zero."""
    raw = (text or "").strip()
    if not raw:
        raise ValidationError("Informe o intervalo personalizado no formato HH:MM (ex.: 1:45).")
    if raw.startswith("-"):
        raise ValidationError("O intervalo não pode ser negativo.")
    m = _INTERVAL_RE.match(raw)
    if not m:
        raise ValidationError(f"Intervalo inválido: {raw!r}. Use o formato HH:MM, por exemplo 1:45.")
    hours, minutes = int(m.group(1)), int(m.group(2))
    if minutes > 59:
        raise ValidationError(f"Intervalo inválido: {raw!r}. Os minutos devem estar entre 00 e 59.")
    total = hours * 60 + minutes
    if total == 0:
        raise ValidationError("O intervalo precisa ser maior que 0:00 — para enviar na hora do evento, escolha “No momento do evento”.")
    if total > MAX_CUSTOM_INTERVAL_MINUTES:
        raise ValidationError(f"O intervalo máximo é {MAX_CUSTOM_INTERVAL_MINUTES // 60}:00 (30 dias).")
    return total


def format_interval(total_minutes: int) -> str:
    """105 -> "1:45" (forma canônica que fica guardada e volta no formulário)."""
    hours, minutes = divmod(int(total_minutes), 60)
    return f"{hours}:{minutes:02d}"


def describe_interval(total_minutes: int) -> str:
    """105 -> "1h45", 120 -> "2h", 15 -> "15min" (texto de resumo)."""
    hours, minutes = divmod(int(total_minutes), 60)
    if hours and minutes:
        return f"{hours}h{minutes:02d}"
    if hours:
        return f"{hours}h"
    return f"{minutes}min"


def offset_minutes(amount: int, unit: str) -> int:
    if unit not in UNIT_MINUTES:
        raise ValidationError(f"Unidade de tempo inválida: {unit!r}")
    return int(amount) * UNIT_MINUTES[unit]


def _offset_timedelta(amount: int, unit: str) -> timedelta:
    if unit not in UNIT_MINUTES:
        raise ValueError(f"Unidade de offset desconhecida: {unit!r}")
    return timedelta(minutes=int(amount) * UNIT_MINUTES[unit])


@dataclass(frozen=True)
class OffsetRule:
    """Regra de tempo relativa (ou fixa) de uma automação, já validada e normalizada."""

    direction: str  # before | at | after | custom (custom = horário fixo do dia)
    amount: int
    unit: str
    custom_interval: str | None = None  # "1:45" quando o usuário escolheu "Personalizado"
    custom_time_local: str | None = None  # "HH:MM" só em direction == custom

    @property
    def minutes(self) -> int:
        return offset_minutes(self.amount, self.unit)


def build_offset_rule(
    direction: str, interval_value: str | None, custom_interval: str | None = None, custom_time: str | None = None
) -> OffsetRule:
    """Converte o que o formulário manda ("before", "2:hours" | "custom" + "1:45")
    numa regra validada. É o ÚNICO lugar que interpreta o seletor de intervalo."""
    if direction not in VALID_DIRECTIONS:
        raise ValidationError(f"Regra de tempo inválida: {direction!r}")
    if direction == "custom":
        value = (custom_time or "").strip()
        if not value:
            raise ValidationError("Informe o horário do disparo personalizado.")
        try:
            parse_hhmm(value)
        except RecurrenceError as exc:
            raise ValidationError(str(exc)) from exc
        return OffsetRule("custom", 0, "minutes", custom_time_local=value)
    if direction == "at":
        return OffsetRule("at", 0, "minutes")

    interval_value = (interval_value or "").strip()
    if interval_value == CUSTOM_INTERVAL_VALUE:
        total = parse_interval(custom_interval)
        return OffsetRule(direction, total, "minutes", custom_interval=format_interval(total))
    try:
        amount_str, unit = interval_value.split(":", 1)
        amount = int(amount_str)
    except (ValueError, AttributeError) as exc:
        raise ValidationError(f"Intervalo inválido: {interval_value!r}") from exc
    if amount < 1 or unit not in UNIT_MINUTES:
        raise ValidationError(f"Intervalo inválido: {interval_value!r}")
    return OffsetRule(direction, amount, unit)


def interval_form_values(amount: int, unit: str, custom_interval: str | None) -> tuple[str, str]:
    """(valor do <select> "Intervalo", texto do campo "Personalizado") para
    pré-preencher a edição: uma automação com "Personalizado · 1:45" volta
    exatamente assim, sem perder o valor."""
    if custom_interval:
        return CUSTOM_INTERVAL_VALUE, custom_interval
    value = f"{amount}:{unit}"
    if any(value == preset for preset, _ in INTERVAL_PRESETS):
        return value, ""
    # Regra antiga/da API fora das opções prontas: mostra como Personalizado.
    return CUSTOM_INTERVAL_VALUE, format_interval(offset_minutes(amount, unit))


def _describe_amount(amount: int, unit: str) -> str:
    if unit == "days":
        return f"{amount} dia{'s' if amount != 1 else ''}"
    if unit == "weeks":
        return f"{amount} semana{'s' if amount != 1 else ''}"
    return describe_interval(offset_minutes(amount, unit))


def describe_rule(rule: OffsetRule) -> str:
    if rule.direction == "at":
        return "no momento do evento"
    if rule.direction == "custom":
        return f"às {rule.custom_time_local}"
    text = _describe_amount(rule.amount, rule.unit)
    return f"{text} antes" if rule.direction == "before" else f"{text} depois"


# --------------------------------------------------------------------------- #
# Horário de disparo a partir do evento
# --------------------------------------------------------------------------- #
def _custom_target_utc(event_start_utc: datetime, custom_time_local: str, event_timezone: str) -> datetime:
    """Horário FIXO do dia: pega a data local do evento (no fuso do próprio
    evento) e combina com o horário escolhido. Recalculado a cada edição do
    evento, então se ele mudar de dia o disparo acompanha, no mesmo horário."""
    hour, minute = parse_hhmm(custom_time_local)
    event_date = utc_to_local(event_start_utc, event_timezone).date()
    return local_to_utc(datetime.combine(event_date, dt_time(hour, minute)), event_timezone)


def target_utc_for_offset(
    event_start_utc: datetime,
    amount: int,
    unit: str,
    direction: str,
    *,
    custom_time_local: str | None = None,
    event_timezone: str = "UTC",
) -> datetime:
    """Instante (UTC naive) do 1º disparo de uma automação. `before`/`after`
    são relativos ao INÍCIO do evento; `at` é o próprio início; `custom` é um
    horário fixo do dia do evento."""
    if direction == "custom":
        if not custom_time_local:
            raise ValueError("custom_time_local é obrigatório quando direction == 'custom'")
        return _custom_target_utc(event_start_utc, custom_time_local, event_timezone)
    delta = _offset_timedelta(amount, unit)
    if direction == "before":
        return event_start_utc - delta
    if direction == "after":
        return event_start_utc + delta
    return event_start_utc  # "at"


def target_utc_for_rule(event_start_utc: datetime, rule: OffsetRule, *, event_timezone: str = "UTC") -> datetime:
    return target_utc_for_offset(
        event_start_utc, rule.amount, rule.unit, rule.direction,
        custom_time_local=rule.custom_time_local, event_timezone=event_timezone,
    )


def target_utc_for_message(
    event_start_utc: datetime,
    amount: int,
    unit: str,
    direction: str,
    position: int,
    gap_seconds: int,
    *,
    custom_time_local: str | None = None,
    event_timezone: str = "UTC",
) -> datetime:
    """`target_utc_for_offset` + o intervalo acumulado até a mensagem `position`."""
    base = target_utc_for_offset(
        event_start_utc, amount, unit, direction, custom_time_local=custom_time_local, event_timezone=event_timezone
    )
    return base + timedelta(seconds=position * gap_seconds)


# --------------------------------------------------------------------------- #
# Formatação (sempre no fuso do usuário)
# --------------------------------------------------------------------------- #
def format_when(utc_naive: datetime | None, tz_name: str) -> str:
    """"20/09/2026 · 18:00"."""
    if utc_naive is None:
        return "—"
    return utc_to_local(utc_naive, tz_name).strftime("%d/%m/%Y · %H:%M")


def format_when_at(local_naive: datetime) -> str:
    """"20/09/2026 às 18:00" (recebe horário de parede)."""
    return local_naive.strftime("%d/%m/%Y às %H:%M")


def as_utc_aware(utc_naive: datetime) -> datetime:
    return utc_naive.replace(tzinfo=timezone.utc)
