"""Configurações persistidas em runtime (hoje: só o fuso horário global).

`config.Settings` não é `frozen` — em vez de criar uma segunda fonte de
verdade (`get_timezone()`) que cada call site precisaria lembrar de chamar,
`load_from_db`/`set_timezone` mutam `settings.default_timezone` no lugar.
Todo call site que já lê `settings.default_timezone` (chatsvc, calendar_service,
calendar_routes, service.py, ...) continua igual, sem risco de algum ficar
esquecido lendo a fonte errada.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session

from .clock import utcnow
from .config import settings
from .models import AppSetting, User
from .service import ValidationError

_TIMEZONE_KEY = "default_timezone"


def user_timezone(user: User) -> str:
    """Fuso horário efetivo de UM usuário (v1.3 — Parte 35): `User.timezone`
    quando o usuário já escolheu o seu (cadastro/onboarding/Preferências);
    `settings.default_timezone` só serve de fallback pra conta que ainda não
    escolheu nenhum. Nunca usar `settings.default_timezone` sozinho num
    request autenticado — isso é o bug corrigido aqui: antes, mudar o fuso em
    Preferências mudava `settings.default_timezone` (mutável, global do
    processo) e afetava TODOS os usuários ao mesmo tempo."""
    return user.timezone or settings.default_timezone


def load_from_db(db: Session) -> None:
    row = db.get(AppSetting, _TIMEZONE_KEY)
    if row and row.value:
        settings.default_timezone = row.value


def set_timezone(db: Session, tz_name: str) -> None:
    tz_name = (tz_name or "").strip()
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"Timezone inválida: {tz_name!r}") from exc

    row = db.get(AppSetting, _TIMEZONE_KEY)
    if row is None:
        row = AppSetting(key=_TIMEZONE_KEY, value=tz_name)
    else:
        row.value = tz_name
        row.updated_at = utcnow()
    db.add(row)
    db.commit()

    settings.default_timezone = tz_name
