"""Cifra dos tokens OAuth (Fernet) — nunca guardamos token em texto puro.

A chave só é validada no primeiro uso, não na importação do módulo nem na
inicialização do `Settings`: assim, sem `TOKEN_ENCRYPTION_KEY` configurada, o
app sobe normalmente e só a tela de "Conectar Google" mostra o aviso de
configuração pendente, em vez do processo inteiro falhar ao iniciar.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


class CryptoNotConfigured(RuntimeError):
    """`TOKEN_ENCRYPTION_KEY` ausente ou inválida."""


class DecryptionFailed(RuntimeError):
    """A chave atual não consegue decifrar o valor salvo (chave trocada?)."""


def is_configured() -> bool:
    return bool(settings.token_encryption_key.strip())


@lru_cache
def _fernet() -> Fernet:
    key = settings.token_encryption_key.strip()
    if not key:
        raise CryptoNotConfigured(
            "TOKEN_ENCRYPTION_KEY não configurada. Gere uma com: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise CryptoNotConfigured(f"TOKEN_ENCRYPTION_KEY inválida: {exc}") from exc


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise DecryptionFailed("Não foi possível decifrar o token salvo (a chave mudou?).") from exc
