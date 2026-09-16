"""Fonte de tempo única do app.

Todos os horários gravados no banco são *naive* em UTC. Centralizar o "agora"
aqui permite congelar o relógio nos testes com um único monkeypatch, e também
corrigir o desvio do relógio do sistema (o relógio da VM/container Docker
Desktop pode ficar minutos ou horas errado, sobretudo depois de suspender/
retomar a máquina host) aplicando o offset calculado por `time_sync.py`
contra um horário de referência da internet. Sem essa correção, não é só o
relógio exibido na tela que fica errado — TODO agendamento dispararia no
horário real errado.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

_offset = timedelta(0)


def utcnow() -> datetime:
    """Agora, em UTC, sem tzinfo (naive) — já corrigido pelo offset de
    sincronização com a internet, se houver (ver `time_sync.sync_once`)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + _offset


def set_offset(offset: timedelta) -> None:
    global _offset
    _offset = offset


def get_offset() -> timedelta:
    return _offset
