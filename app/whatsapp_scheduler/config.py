"""Configuração via variáveis de ambiente (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # WAHA
    waha_base_url: str = "http://localhost:3000"
    waha_api_key: str = ""
    waha_session: str = "default"
    request_timeout: float = 30.0

    # Loop de agendamento
    tick_seconds: int = 30
    max_overdue_minutes: int = 120
    default_timezone: str = "America/Sao_Paulo"
    send_jitter_seconds: float = 1.5
    dispatch_batch: int = 20
    stuck_processing_minutes: int = 10
    # Backoff entre tentativas de envio (segundos), por tentativa.
    backoff_seconds: list[int] = [60, 300, 900]

    # Conversas (histórico do WhatsApp)
    chat_list_limit: int = 50
    chat_messages_limit: int = 50
    chat_list_cache_seconds: int = 20
    chat_messages_cache_seconds: int = 90
    # A lista de chats deve responder rápido ou falhar rápido (sessão ruim).
    chat_list_timeout: float = 12.0
    # O engine WEBJS demora para trazer histórico; timeout dedicado.
    history_timeout: float = 120.0

    # Banco
    db_path: str = "./data/app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
