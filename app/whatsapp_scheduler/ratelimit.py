"""Rate limiting simples em memória (janela fixa) para rotas de autenticação.

Sem Redis: o processo já roda single-worker (ver `Dockerfile`/`main.py`),
então um dict em memória é suficiente — mesma limitação que `chatsvc._chat_cache`
já tem hoje (reseta a cada restart, não escala a múltiplos processos). Se um
dia o app rodar com múltiplos workers/réplicas, isto precisa virar um
backend compartilhado (Redis, ou uma tabela no banco).
"""

from __future__ import annotations

import time

from .config import settings

# chave -> lista de timestamps (monotonic) das tentativas dentro da janela atual.
_attempts: dict[str, list[float]] = {}


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds


def check_rate_limit(
    key: str,
    *,
    max_attempts: int | None = None,
    window_seconds: int | None = None,
) -> None:
    """Levanta `RateLimitExceeded` se `key` já bateu o limite na janela atual.
    Não conta a chamada em si como tentativa — quem chama decide (normalmente
    só depois de uma tentativa que valha a pena contar, ex.: um POST de login)."""
    max_attempts = max_attempts if max_attempts is not None else settings.rate_limit_max_attempts
    window_seconds = window_seconds if window_seconds is not None else settings.rate_limit_window_seconds

    now = time.monotonic()
    window_start = now - window_seconds
    recent = [t for t in _attempts.get(key, []) if t >= window_start]
    _attempts[key] = recent
    if len(recent) >= max_attempts:
        retry_after = int(window_seconds - (now - recent[0]))
        raise RateLimitExceeded(retry_after_seconds=max(retry_after, 1))


def record_attempt(key: str) -> None:
    _attempts.setdefault(key, []).append(time.monotonic())
