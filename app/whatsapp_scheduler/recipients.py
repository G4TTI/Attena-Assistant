"""Normalização do destinatário para o formato de chatId do WhatsApp/WAHA.

- `5511999998888@c.us`  -> contato individual
- `...-...@g.us`         -> grupo (repassado como veio)
"""

from __future__ import annotations

import re

import phonenumbers

_DIGITS = re.compile(r"\D")


class RecipientError(ValueError):
    """Destinatário inválido."""


def normalize_recipient(raw: str, default_region: str = "BR") -> str:
    value = (raw or "").strip()
    if not value:
        raise RecipientError("Destinatário vazio")

    # Já é um chatId / id de grupo / id do WhatsApp
    if value.endswith(("@c.us", "@g.us", "@s.whatsapp.net", "@lid", "@newsletter")):
        return value

    digits = _DIGITS.sub("", value)
    try:
        if value.startswith("+"):
            parsed = phonenumbers.parse(value, None)
        elif len(digits) >= 12:
            # provavelmente já internacional, só sem o "+"
            parsed = phonenumbers.parse("+" + digits, None)
        else:
            # número nacional -> assume a região padrão
            parsed = phonenumbers.parse(value, default_region)
    except phonenumbers.NumberParseException as exc:
        raise RecipientError(f"Não consegui interpretar o número: {raw!r} ({exc})") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise RecipientError(
            f"Número inválido: {raw!r}. Use o formato internacional, ex: +55 11 99999-8888."
        )

    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    return e164.lstrip("+") + "@c.us"
