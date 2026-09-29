"""Códigos estáveis de falha de envio + mensagens de erro SANITIZADAS.

`Dispatch.last_error` é visto pelo dono da mensagem e (só o código + este texto)
pelo admin na visão de saúde operacional. Por isso nunca guarda o corpo de uma
resposta do WAHA (pode ecoar o chatId ou o texto enviado), telefone, token ou
qualquer outro dado da conversa.
"""

from __future__ import annotations

from .log_sanitizer import redact
from .waha import WahaError

WAHA_UNREACHABLE = "waha_unreachable"
WAHA_REJECTED = "waha_rejected"
WAHA_SERVER_ERROR = "waha_server_error"
SESSION_NOT_READY = "session_not_ready"
OVERDUE = "overdue"
CANCELED = "canceled"
ACCOUNT_SUSPENDED = "account_suspended"
CONTENT_UNAVAILABLE = "content_unavailable"
DECRYPTION_FAILED = "decryption_failed"
DEPENDENCY_ABORTED = "dependency_aborted"
STUCK_RECOVERED = "stuck_recovered"
SCHEDULE_REMOVED = "schedule_removed"
UNKNOWN = "unknown"

LABELS = {
    WAHA_UNREACHABLE: "WAHA fora do ar",
    WAHA_REJECTED: "WAHA recusou",
    WAHA_SERVER_ERROR: "Erro interno do WAHA",
    SESSION_NOT_READY: "WhatsApp desconectado",
    OVERDUE: "Atrasada demais",
    CANCELED: "Cancelada",
    ACCOUNT_SUSPENDED: "Conta suspensa",
    CONTENT_UNAVAILABLE: "Conteúdo indisponível",
    DECRYPTION_FAILED: "Falha ao decifrar",
    DEPENDENCY_ABORTED: "Mensagem anterior falhou",
    STUCK_RECOVERED: "Recuperada após reinício",
    SCHEDULE_REMOVED: "Agendamento removido",
    UNKNOWN: "Erro desconhecido",
}

_MAX_LENGTH = 300


def sanitize(text: str | None) -> str | None:
    if text is None:
        return None
    return redact(str(text))[:_MAX_LENGTH]


def classify_waha_error(exc: Exception) -> tuple[str, str]:
    """(código, mensagem segura) de uma falha ao enviar pelo WAHA."""
    status = getattr(exc, "status_code", None)
    if not isinstance(exc, WahaError):
        return UNKNOWN, "Erro inesperado ao enviar."
    if status is None:
        return WAHA_UNREACHABLE, "Não foi possível falar com o WAHA (conexão ou tempo esgotado)."
    if status >= 500:
        return WAHA_SERVER_ERROR, f"O WAHA respondeu com erro interno (HTTP {status})."
    return WAHA_REJECTED, f"O WAHA recusou o envio (HTTP {status}). Verifique o número/chat e a conexão."
