"""Fonte de tempo única do app.

Todos os horários gravados no banco são *naive* em UTC. Centralizar o "agora"
aqui permite congelar o relógio nos testes com um único monkeypatch.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Agora, em UTC, sem tzinfo (naive)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
