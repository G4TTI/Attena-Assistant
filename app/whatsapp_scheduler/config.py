"""Configuração via variáveis de ambiente (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty: variável vazia no compose (`${X:-}`) = usar o padrão daqui.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True)

    # Ambiente — controla flags sensíveis a produção (cookie `Secure`, HSTS).
    # "development" (padrão, ex.: localhost sem HTTPS) | "production".
    app_env: str = "development"

    # Autenticação
    session_cookie_name: str = "attena_session"
    # None = segue o ambiente (Secure só em produção). Force True quando o app
    # for servido só por HTTPS (ex.: atrás do Cloudflare) mesmo fora de produção.
    session_cookie_secure: bool | None = None
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

    # Conversas (histórico do WhatsApp) — só VISUAIS: nada disto é gravado no
    # banco. Os caches abaixo vivem apenas na memória do processo e expiram
    # sozinhos (ver chatsvc.py).
    chat_list_limit: int = 50
    chat_messages_limit: int = 50
    chat_list_cache_seconds: int = 20
    chat_messages_cache_seconds: int = 60
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

    # ------------------------------------------------------------------ #
    # Criptografia de dados de usuário em repouso (ver privacy.py e
    # docs/SECURITY_AND_PRIVACY.md). Sem estas chaves o app NÃO sobe.
    # ------------------------------------------------------------------ #
    # Chaves AES-256-GCM versionadas: "1:<base64 de 32 bytes>[,2:<...>]".
    # A versão ativa (a que cifra dados novos) é a maior, salvo
    # `data_encryption_active_version`. Versões antigas continuam só pra decifrar.
    data_encryption_keys: str = ""
    data_encryption_keys_file: str = ""  # alternativa: caminho de um arquivo (Docker secret)
    data_encryption_active_version: int | None = None
    # Chave HMAC-SHA256 (base64, 32 bytes) dos índices cegos (hash de telefone).
    # Separada da de cifra e de vida longa: trocá-la invalida as buscas por hash.
    data_hash_key: str = ""
    data_hash_key_file: str = ""

    # ------------------------------------------------------------------ #
    # Retenção (ver retention.py / privacy_cleanup)
    # ------------------------------------------------------------------ #
    privacy_cleanup_seconds: int = 3600
    # Por quanto tempo o HASH (nunca o número) do destinatário de uma mensagem
    # já encerrada continua existindo — permite ao usuário ver "3 canceladas"
    # na conversa. Depois disso vira NULL.
    recipient_hash_retention_days: int = 30
    # IP/user-agent de login e de sessões: só para segurança, prazo curto.
    login_ip_retention_days: int = 30
    login_audit_retention_days: int = 180
    session_record_retention_days: int = 30
    auth_token_retention_days: int = 7

    # WAHA: armazenamento de conversas do engine NOWEB (desligado por padrão —
    # com ele ligado o WAHA grava chats/contatos/mensagens em store.sqlite3).
    waha_noweb_store_enabled: bool = False

    # ------------------------------------------------------------------ #
    # Planos, cobrança e admin
    # ------------------------------------------------------------------ #
    # False = limites dos planos só aparecem na tela (não bloqueiam nada).
    enforce_plan_limits: bool = False
    # Gateway de pagamento. Vazio = nenhum configurado (o upgrade para em
    # "Pagamento ainda não configurado"; nada é marcado como pago).
    payment_provider: str = ""
    # E-mail da CONTA PRINCIPAL (owner). Reservado: o cadastro público recusa;
    # a conta só é criada/redefinida pelo CLI `setup-owner` no servidor.
    admin_owner_email: str = "admin@caiogatti.com"
    # Sessões mais velhas que isto precisam entrar de novo para abrir /admin.
    admin_session_max_age_hours: int = 12
    admin_rate_limit_requests: int = 300
    admin_rate_limit_window_seconds: int = 300
    # Origens extras aceitas em POST (além do próprio Host), separadas por vírgula.
    allowed_origins: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
