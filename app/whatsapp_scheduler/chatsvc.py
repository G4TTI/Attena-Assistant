"""Conversas do WhatsApp: lista de chats + histórico — SÓ PARA VISUALIZAÇÃO.

O Attena não é um banco de conversas: nada do que vem daqui (mensagens
recebidas ou enviadas, nomes, fotos, mídias) é gravado no banco, em arquivo ou
em log. Cada tela busca no WAHA na hora e entrega ao usuário autenticado.

O engine WEBJS demora para trazer o histórico, então existe um cache — só em
MEMÓRIA do processo, por (usuário, WhatsApp, conversa), com TTL curto
(`chat_list_cache_seconds` / `chat_messages_cache_seconds`). Entrada vencida é
removida (não só ignorada): em toda leitura/escrita e a cada tick do scheduler
(`purge_expired`). Reiniciar o processo apaga tudo.

Mídia nunca é baixada (`downloadMedia=false`); a foto de perfil é uma URL do
próprio WhatsApp que o navegador do usuário carrega direto.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .clock import utcnow
from .config import settings
from .waha import WahaClient, WahaError, extract_message_id

logger = logging.getLogger("whatsapp_scheduler.chatsvc")

_MEDIA_LABEL = {
    "image": "[imagem]",
    "video": "[vídeo]",
    "ptt": "[áudio]",
    "audio": "[áudio]",
    "document": "[documento]",
    "sticker": "[figurinha]",
    "location": "[localização]",
    "vcard": "[contato]",
    "call_log": "[chamada]",
}

# session_name -> {"at": monotonic, "data": [...]}
_chat_cache: dict[str, dict] = {}
# (user_id, session_name, chat_id) -> {"at": monotonic, "fetched_at": datetime, "messages": [...]}
_history_cache: dict[tuple[str, str, str], dict] = {}


def purge_expired() -> int:
    """Remove da memória toda entrada vencida. Retorna quantas saíram."""
    now = time.monotonic()
    removed = 0
    for key in [k for k, v in _chat_cache.items() if now - v["at"] >= settings.chat_list_cache_seconds]:
        _chat_cache.pop(key, None)
        removed += 1
    for key in [k for k, v in _history_cache.items() if now - v["at"] >= settings.chat_messages_cache_seconds]:
        _history_cache.pop(key, None)
        removed += 1
    return removed


def forget_session(session: str) -> None:
    """Descarta tudo em memória de uma sessão (ex.: WhatsApp desconectado)."""
    _chat_cache.pop(session, None)
    for key in [k for k in _history_cache if k[1] == session]:
        _history_cache.pop(key, None)


def _fresh_chats(session: str) -> list[dict] | None:
    purge_expired()
    entry = _chat_cache.get(session)
    return entry["data"] if entry else None


def cached_chat_name(session: str, chat_id: str) -> str | None:
    """Nome do contato na lista de conversas AINDA em cache (nunca vai à rede)."""
    for chat in _fresh_chats(session) or []:
        if chat["id"] == chat_id:
            name = (chat.get("name") or "").strip()
            return name if name and name != chat_id.split("@")[0] else None
    return None


def _fmt_ts(ts: int, tz_name: str) -> str:
    if not ts:
        return ""
    dt = datetime.fromtimestamp(ts, tz=ZoneInfo(tz_name))
    today = datetime.now(tz=ZoneInfo(tz_name)).date()
    if dt.date() == today:
        return dt.strftime("%H:%M")
    return dt.strftime("%d/%m %H:%M")


def _preview(msg: dict) -> str:
    body = (msg.get("body") or "").strip().replace("\n", " ")
    if body:
        return body[:60]
    if msg.get("hasMedia") or msg.get("type") in _MEDIA_LABEL:
        return _MEDIA_LABEL.get(str(msg.get("type")), "[mídia]")
    return ""


def _normalize_chat(c: dict, tz_name: str) -> dict:
    cid = str(c.get("id") or "")
    last = c.get("lastMessage") or {}
    return {
        "id": cid,
        "name": c.get("name") or cid.split("@")[0],
        "picture": c.get("picture"),
        "is_group": cid.endswith("@g.us"),
        "last_preview": _preview(last),
        "last_ts": last.get("timestamp") or 0,
        "last_when": _fmt_ts(last.get("timestamp") or 0, tz_name),
        "last_from_me": bool(last.get("fromMe")),
    }


async def list_chats(waha: WahaClient, session: str, tz_name: str, *, force: bool = False) -> list[dict]:
    cached = None if force else _fresh_chats(session)
    if cached is not None:
        return cached
    raw = await waha.get_chats_overview(session, settings.chat_list_limit, timeout=settings.chat_list_timeout)
    chats = [_normalize_chat(c, tz_name) for c in raw if c.get("id")]
    chats.sort(key=lambda c: c["last_ts"], reverse=True)
    _chat_cache[session] = {"at": time.monotonic(), "data": chats}
    return chats


def _normalize_message(m: dict, tz_name: str) -> dict | None:
    mid = _msg_id(m)
    if not mid:
        return None
    ts = int(m.get("timestamp") or 0)
    msg_type = str(m.get("type") or "chat")
    has_media = bool(m.get("hasMedia"))
    text = (m.get("body") or "").strip()
    if not text:
        text = _MEDIA_LABEL.get(msg_type, "[mídia]" if has_media else "")
    return {
        "id": mid,
        "from_me": bool(m.get("fromMe")),
        "ts": ts,
        "when": _fmt_ts(ts, tz_name),
        "text": text,
        "type": msg_type,
        "is_note": not text and not has_media,
    }


@dataclass
class ChatHistory:
    messages: list[dict]
    from_cache: bool
    synced_at: datetime | None
    error: str | None = None


async def get_history(
    waha: WahaClient, user_id: str, session: str, chat_id: str, tz_name: str, *, force: bool = False
) -> ChatHistory:
    """Histórico de uma conversa, direto do WAHA (ou do cache em memória, se
    ainda fresco). Nunca grava nada."""
    purge_expired()
    key = (user_id, session, chat_id)
    entry = _history_cache.get(key)
    if entry and not force:
        return ChatHistory(entry["messages"], from_cache=True, synced_at=entry["fetched_at"])
    try:
        raw = await waha.get_messages(session, chat_id, settings.chat_messages_limit, timeout=settings.history_timeout)
    except WahaError as exc:
        logger.warning("falha ao buscar histórico de uma conversa (sessão %s): status=%s", session, exc.status_code)
        if entry:
            return ChatHistory(entry["messages"], from_cache=True, synced_at=entry["fetched_at"], error=str(exc))
        return ChatHistory([], from_cache=False, synced_at=None, error=str(exc))
    messages = [m for m in (_normalize_message(r, tz_name) for r in raw) if m is not None]
    messages.sort(key=lambda m: m["ts"])
    fetched_at = utcnow()
    _history_cache[key] = {"at": time.monotonic(), "fetched_at": fetched_at, "messages": messages}
    return ChatHistory(messages, from_cache=False, synced_at=fetched_at)


def cached_message_ids(user_id: str, session: str, chat_id: str) -> set[str]:
    entry = _history_cache.get((user_id, session, chat_id))
    return {m["id"] for m in entry["messages"]} if entry else set()


async def send_now(waha: WahaClient, user_id: str, session: str, chat_id: str, text: str) -> str | None:
    """Envio imediato. Nada é gravado: só invalida os caches em memória para a
    próxima leitura trazer a mensagem do próprio WhatsApp. Retorna o id da
    mensagem no WAHA (quando o engine informa)."""
    payload = await waha.send_text(session, chat_id, text)
    _chat_cache.pop(session, None)
    _history_cache.pop((user_id, session, chat_id), None)
    return extract_message_id(payload)


def _msg_id(m: dict) -> str | None:
    mid = m.get("id")
    if isinstance(mid, str):
        return mid
    if isinstance(mid, dict):
        return mid.get("_serialized") or mid.get("id")
    return None
