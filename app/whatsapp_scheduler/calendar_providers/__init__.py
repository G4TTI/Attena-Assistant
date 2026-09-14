"""Registro de provedores de calendário por chave (`Calendar.provider`/`CalendarConnection.provider`).

Único lugar que precisa mudar para plugar Outlook/Apple no futuro: implemente
`CalendarProvider` (ver `base.py`) e registre aqui.
"""

from __future__ import annotations

from functools import lru_cache

from .base import CalendarProvider
from .google import GoogleCalendarProvider

__all__ = ["CalendarProvider", "get_provider", "available_providers"]


@lru_cache
def _registry() -> dict[str, CalendarProvider]:
    return {"google": GoogleCalendarProvider()}


def get_provider(key: str) -> CalendarProvider:
    provider = _registry().get(key)
    if provider is None:
        raise KeyError(f"Provedor de calendário desconhecido: {key!r}")
    return provider


def available_providers() -> dict[str, CalendarProvider]:
    return dict(_registry())
