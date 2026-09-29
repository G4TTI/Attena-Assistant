"""Sanitização central de logs (defesa em profundidade).

A regra principal continua sendo NÃO passar dado sensível para o logger — os
call sites registram só metadados (ids, contagens, status). Este filtro é a
rede de segurança para o que escapa: bibliotecas de terceiros (httpx, uvicorn),
mensagens de exceção que embutem a resposta de um serviço externo, tracebacks.

Instalado em TODOS os handlers (raiz + uvicorn) por `install()`, chamado no
import do `main.py`. Remove/mascara:
- ids de chat do WhatsApp (…@c.us, …@g.us, …@lid) e ids de mensagem do WAHA;
- números de telefone e CPF;
- e-mails;
- tokens: Authorization/Bearer, cookies, `access_token`/`refresh_token`/
  `password`/`code`/`state`/... em JSON, query string ou chave=valor;
- links de redefinição de senha / verificação de e-mail;
- QR Code (valor bruto "2@…" e imagens data:base64);
- no access log do uvicorn, a query string inteira (tem `?chat=`, `?code=`).
"""

from __future__ import annotations

import logging
import re

_REDACTED = "[redacted]"

# Ordem importa: ids do WhatsApp antes do padrão genérico de telefone.
_WA_ID = re.compile(r"[0-9A-Za-z._:-]*\d{5,}[0-9-]*@(?:c\.us|s\.whatsapp\.net|g\.us|lid|newsletter|broadcast)")
_WAHA_MSG_ID = re.compile(r"\b(?:true|false)_[^\s\"',;)]+")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
_SENSITIVE_KEYS = (
    r"access_token|refresh_token|id_token|client_secret|password|passwd|senha|new_password|current_password|"
    r"token|code|state|api[_-]?key|x-api-key|authorization|cookie|set-cookie|session_token|secret|cpf|"
    r"synctoken|pagetoken|sync_token|page_token|qr|body|text|message|chat|chatid|chat_id"
)
_KV = re.compile(
    rf"(?i)((?<![A-Za-z0-9_])[\"']?(?:{_SENSITIVE_KEYS})[\"']?\s*[:=]\s*)(\"(?:[^\"\\]|\\.)*\"|'[^']*'|[^\s,&;}}\]]+)"
)
_QUERY = re.compile(rf"(?i)([?&](?:{_SENSITIVE_KEYS})=)[^&\s\"'#]+")
_TOKEN_PATH = re.compile(r"(/(?:redefinir-senha|verificar-email)/)[^/\s?\"']+")
_DATA_URI = re.compile(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]+")
_QR_VALUE = re.compile(r"\b2@[A-Za-z0-9+/=,@._-]{16,}")
_EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CPF = re.compile(r"(?<![\w.-])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\w-])")
_PHONE_CANDIDATE = re.compile(r"(?<![\w.:/-])\+?\(?\d[\d\s().-]{7,}\d(?![\w-])")
_DATE_LIKE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _phone(match: re.Match) -> str:
    text = match.group(0)
    digits = sum(ch.isdigit() for ch in text)
    if _DATE_LIKE.match(text) or not 10 <= digits <= 15:
        return text
    return "[phone]"


def redact(text: str) -> str:
    """Versão de `text` segura para log."""
    if not text:
        return text
    text = _DATA_URI.sub("[data-uri]", text)
    text = _QR_VALUE.sub("[qr]", text)
    text = _BEARER.sub(r"\1 " + _REDACTED, text)
    text = _TOKEN_PATH.sub(r"\1" + _REDACTED, text)
    text = _QUERY.sub(r"\1" + _REDACTED, text)
    text = _KV.sub(r"\1" + _REDACTED, text)
    text = _WAHA_MSG_ID.sub("[waha-message-id]", text)
    text = _WA_ID.sub("[chat]", text)
    text = _EMAIL.sub("[email]", text)
    text = _CPF.sub("[cpf]", text)
    text = _PHONE_CANDIDATE.sub(_phone, text)
    return text


def redact_path(path: str) -> str:
    """Caminho de uma requisição para o access log: sem query string e sem tokens no path."""
    base, sep, _query = str(path).partition("?")
    base = _TOKEN_PATH.sub(r"\1" + _REDACTED, base)
    base = _WA_ID.sub("[chat]", base)
    return base + ("?" + _REDACTED if sep else "")


class SanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 - API do logging
        try:
            if record.name == "uvicorn.access" and isinstance(record.args, tuple) and len(record.args) == 5:
                client, method, path, version, status = record.args
                record.args = (client, method, redact_path(path), version, status)
                return True
            message = record.getMessage()
            record.msg = redact(message)
            record.args = None
            if record.exc_info and not record.exc_text:
                record.exc_text = logging.Formatter().formatException(record.exc_info)
            if record.exc_text:
                record.exc_text = redact(record.exc_text)
            if record.stack_info:
                record.stack_info = redact(record.stack_info)
        except Exception:  # noqa: BLE001 - sanitizar nunca pode derrubar o log
            record.msg = "[log removido: falha ao sanitizar]"
            record.args = None
            record.exc_info = None
            record.exc_text = None
        return True


_FILTER = SanitizingFilter()
# Loggers de bibliotecas que registram URLs completas (com chatId, syncToken…) em INFO.
_NOISY = ("httpx", "httpcore", "hpack", "urllib3")


def _attach(handler: logging.Handler) -> None:
    if not any(isinstance(f, SanitizingFilter) for f in handler.filters):
        handler.addFilter(_FILTER)


def install() -> None:
    """Idempotente: coloca o filtro em todo handler existente (raiz, uvicorn…)."""
    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)
    loggers = [logging.getLogger()] + [
        logger for logger in logging.Logger.manager.loggerDict.values() if isinstance(logger, logging.Logger)
    ]
    for logger in loggers:
        for handler in logger.handlers:
            _attach(handler)
