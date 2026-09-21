"""Configuração via variáveis de ambiente (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Ambiente — controla flags sensíveis a produção (cookie `Secure`, HSTS).
    # "development" (padrão, ex.: localhost sem HTTPS) | "production".
    app_env: str = "development"

    # Autenticação
    session_cookie_name: str = "attena_session"
    session_ttl_days: int = 30
    password_reset_ttl_minutes: int = 30
    email_verification_ttl_hours: int = 48
    # Tentativas por janela para login/cadastro/esqueci-senha (ver ratelimit.py).
    rate_limit_max_attempts: int = 5
    rate_limit_window_seconds: int = 300
    # Header com o IP real do visitante quando o app roda atrás de proxy/túnel
    # (ex.: "CF-Connecting-IP" no Cloudflare). Vazio = usa o IP da conexão TCP.
    # Só habilite se o app NÃO for alcançável direto de fora — senão qualquer
    # um forja o header e burla o rate limit. Sem isto, todos os visitantes de
    # um túnel/Docker parecem o mesmo IP e dividem o mesmo limite de cadastro.
    client_ip_header: str = ""

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

    # Sincronização do relógio com a internet (corrige o desvio do relógio do
    # sistema — comum em VM/containers Docker Desktop depois de suspender/
    # retomar a máquina host — sem isso, TODO agendamento dispara no horário
    # errado, não só o relógio exibido na tela). Ver time_sync.py.
    clock_sync_seconds: int = 900

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

    # Calendários externos — Google Calendar (vazio = integração desligada)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8090/calendario/oauth/callback"
    # Chave Fernet para cifrar tokens OAuth em repouso. Gerar uma vez com:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # NÃO trocar depois de conectar uma conta — tokens já salvos ficam ilegíveis.
    token_encryption_key: str = ""
    calendar_sync_seconds: int = 300
    calendar_sync_window_past_days: int = 90
    calendar_sync_window_future_days: int = 365
    # Quantos dias a partir de hoje a tela de Calendário mostra por padrão
    # (independente de quanto é sincronizado/guardado).
    calendar_agenda_default_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
