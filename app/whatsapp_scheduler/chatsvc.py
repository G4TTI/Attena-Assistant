"""Conversas do WhatsApp: lista de chats + histórico, com cache local.

O engine WEBJS demora ~30-60s para trazer o histórico de uma conversa, então:
- a lista de chats tem cache curto em memória;
- as mensagens ficam em `cached_messages` (SQLite): abrir de novo é instantâneo,
  e há um botão "atualizar" para forçar nova busca no WAHA.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session, col, select

from .clock import utcnow
from .config import settings
from .models import CachedMessage
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

# Cache em memória por sessão WAHA (cada usuário tem a sua) — mesma
# limitação de sempre: por processo, reseta a cada restart.
_chat_cache: dict[str, dict] = {}


def _cache_for(session: str) -> dict:
    return _chat_cache.setdefault(session, {"at": 0.0, "data": []})


def _fmt_ts(ts: int) -> str:
    if not ts:
        return ""
    dt = datetime.fromtimestamp(ts, tz=ZoneInfo(settings.default_timezone))
    today = datetime.now(tz=ZoneInfo(settings.default_timezone)).date()
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


def _normalize_chat(c: dict) -> dict:
    cid = str(c.get("id") or "")
    last = c.get("lastMessage") or {}
    return {
        "id": cid,
        "name": c.get("name") or cid.split("@")[0],
        "picture": c.get("picture"),
        "is_group": cid.endswith("@g.us"),
        "last_preview": _preview(last),
        "last_ts": last.get("timestamp") or 0,
        "last_when": _fmt_ts(last.get("timestamp") or 0),
        "last_from_me": bool(last.get("fromMe")),
    }


async def list_chats(waha: WahaClient, session: str, *, force: bool = False) -> list[dict]:
    cache = _cache_for(session)
    now = time.monotonic()
    if not force and cache["data"] and now - cache["at"] < settings.chat_list_cache_seconds:
        return cache["data"]
    raw = await waha.get_chats_overview(session, settings.chat_list_limit, timeout=settings.chat_list_timeout)
    chats = [_normalize_chat(c) for c in raw if c.get("id")]
    chats.sort(key=lambda c: c["last_ts"], reverse=True)
    cache.update(at=now, data=chats)
    return chats


def _row_to_msg(m: CachedMessage) -> dict:
    text = (m.body or "").strip()
    if not text:
        text = _MEDIA_LABEL.get(m.msg_type, "[mídia]" if m.has_media else "")
    return {
        "id": m.message_id,
        "from_me": m.from_me,
        "ts": m.ts,
        "when": _fmt_ts(m.ts),
        "text": text,
        "type": m.msg_type,
        "is_note": not text and not m.has_media,
    }


@dataclass
class ChatHistory:
    messages: list[dict]
    from_cache: bool
    synced_at: datetime | None
    error: str | None = None


def _cached_rows(db: Session, user_id: str, chat_id: str) -> list[CachedMessage]:
    return list(
        db.exec(
            select(CachedMessage)
            .where(col(CachedMessage.user_id) == user_id)
            .where(col(CachedMessage.chat_id) == chat_id)
            .order_by(col(CachedMessage.ts))
        ).all()
    )


async def get_history(
    db: Session, waha: WahaClient, user_id: str, session: str, chat_id: str, *, force: bool = False
) -> ChatHistory:
    rows = _cached_rows(db, user_id, chat_id)
    last_sync = max((r.synced_at for r in rows), default=None)
    fresh = last_sync is not None and (
        (utcnow() - last_sync).total_seconds() < settings.chat_messages_cache_seconds
    )
    if rows and not force and fresh:
        return ChatHistory([_row_to_msg(r) for r in rows], from_cache=True, synced_at=last_sync)

    try:
        raw = await waha.get_messages(
            session,
            chat_id,
            settings.chat_messages_limit,
            timeout=settings.history_timeout,
        )
    except WahaError as exc:
        logger.warning("falha ao buscar histórico de %s: %s", chat_id, exc)
        if rows:
            return ChatHistory(
                [_row_to_msg(r) for r in rows], from_cache=True, synced_at=last_sync, error=str(exc)
            )
        return ChatHistory([], from_cache=False, synced_at=None, error=str(exc))

    now = utcnow()
    for m in raw:
        mid = _msg_id(m)
        if not mid:
            continue
        row = db.get(CachedMessage, mid) or CachedMessage(message_id=mid, user_id=user_id, chat_id=chat_id)
        row.user_id = user_id
        row.chat_id = chat_id
        row.ts = int(m.get("timestamp") or 0)
        row.from_me = bool(m.get("fromMe"))
        row.body = (m.get("body") or "")[:8000]
        row.msg_type = str(m.get("type") or "chat")
        row.has_media = bool(m.get("hasMedia"))
        row.ack_name = m.get("ackName")
        row.synced_at = now
        db.add(row)
    db.commit()
    rows = _cached_rows(db, user_id, chat_id)
    return ChatHistory([_row_to_msg(r) for r in rows], from_cache=False, synced_at=now)


async def send_now(db: Session, waha: WahaClient, user_id: str, session: str, chat_id: str, text: str) -> dict:
    payload = await waha.send_text(session, chat_id, text)
    mid = extract_message_id(payload)
    if mid and not db.get(CachedMessage, mid):
        db.add(
            CachedMessage(
                message_id=mid,
                user_id=user_id,
                chat_id=chat_id,
                ts=int(time.time()),
                from_me=True,
                body=text,
                msg_type="chat",
            )
        )
        db.commit()
    _cache_for(session)["at"] = 0.0  # força a lista a atualizar no próximo load
    return payload


def _msg_id(m: dict) -> str | None:
    mid = m.get("id")
    if isinstance(mid, str):
        return mid
    if isinstance(mid, dict):
        return mid.get("_serialized") or mid.get("id")
    return None
