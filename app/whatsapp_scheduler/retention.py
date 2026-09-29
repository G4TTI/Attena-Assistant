"""Retenção mínima: o conteúdo privado some assim que deixa de ser necessário.

Política (detalhada em docs/SECURITY_AND_PRIVACY.md):

- Mensagem recebida / histórico / mídia do WhatsApp: 0 dias — nunca gravados
  pelo Attena (só memória, TTL curto: chatsvc.py).
- Mensagem programada: cifrada enquanto ainda pode sair. Ao virar estado final
  (enviada, cancelada, falha definitiva, ignorada) o ciphertext, o nonce e o
  destinatário cifrado viram NULL — no mesmo commit que muda o estado
  (`finalize_schedules`). Recorrência ativa mantém o conteúdo enquanto existir.
- Destinatário: cifrado enquanto algum agendamento dele está ativo; o HMAC
  (nunca o número) fica `recipient_hash_retention_days` e depois vira NULL.
- Automação: mensagens cifradas enquanto alguma entrega dela está ativa.
- Logs: só metadados (log_sanitizer.py).

`run_cleanup` (job `privacy_cleanup`, a cada `privacy_cleanup_seconds` e no boot)
é a rede de segurança: acha o que deveria ter sido apagado e não foi, e aplica
as retenções por prazo (IP de login, sessões antigas, tokens usados, tokens do
Google de conexões desconectadas, sessões do WAHA desconectadas). Só registra
contagens — nunca conteúdo.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlalchemy import and_, exists, func, or_
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from .clock import utcnow
from .config import settings
from .db import get_engine
from .models import (
    OPEN_STATUSES,
    TERMINAL_STATUSES,
    AutomationMessage,
    AutomationSchedule,
    CalendarConnection,
    CalendarConnectionStatus,
    Dispatch,
    EmailVerificationToken,
    LoginAuditEvent,
    PasswordResetToken,
    Schedule,
    ScheduleGroup,
    UserSession,
    WhatsAppSession,
)

logger = logging.getLogger("whatsapp_scheduler.retention")

# Uma mensagem de automação recém-criada ainda não tem as ligações com os
# agendamentos (são commits separados) — não expurgar nessa janela.
_AUTOMATION_GRACE = timedelta(minutes=10)


# --------------------------------------------------------------------------- #
# Expurgo de uma linha
# --------------------------------------------------------------------------- #
def purge_schedule(schedule: Schedule, now: datetime | None = None) -> bool:
    if not (schedule.message_ciphertext or schedule.encryption_nonce or schedule.recipient_phone_encrypted):
        return False
    schedule.message_ciphertext = None
    schedule.encryption_nonce = None
    schedule.encryption_key_version = None
    schedule.recipient_phone_encrypted = None
    schedule.content_purged_at = now or utcnow()
    return True


def purge_group(group: ScheduleGroup, now: datetime | None = None) -> bool:
    if not group.recipient_encrypted:
        return False
    group.recipient_encrypted = None
    group.content_purged_at = now or utcnow()
    return True


def purge_automation_message(message: AutomationMessage, now: datetime | None = None) -> bool:
    if not (message.message_ciphertext or message.encryption_nonce):
        return False
    message.message_ciphertext = None
    message.encryption_nonce = None
    message.encryption_key_version = None
    message.content_purged_at = now or utcnow()
    return True


# --------------------------------------------------------------------------- #
# "Terminou?" em SQL
# --------------------------------------------------------------------------- #
def _has_open_dispatch():
    return exists().where(col(Dispatch.schedule_id) == col(Schedule.id), col(Dispatch.status).in_(list(OPEN_STATUSES)))


def schedule_active_clause():
    """A mensagem ainda pode sair: regra ativa ou alguma dispatch aberta."""
    return or_(col(Schedule.enabled).is_(True), _has_open_dispatch())


def is_finished(db: Session, schedule: Schedule) -> bool:
    if schedule.enabled:
        return False
    open_dispatch = db.exec(
        select(Dispatch.id)
        .where(col(Dispatch.schedule_id) == schedule.id)
        .where(col(Dispatch.status).in_(list(OPEN_STATUSES)))
    ).first()
    return open_dispatch is None


def _group_finished(db: Session, group_id: str) -> bool:
    active = db.exec(
        select(func.count()).select_from(Schedule).where(col(Schedule.group_id) == group_id).where(schedule_active_clause())
    ).one()
    return not active


def _automation_message_finished(db: Session, message_id: str) -> bool:
    active = db.exec(
        select(func.count())
        .select_from(AutomationSchedule)
        .join(Schedule, col(Schedule.id) == col(AutomationSchedule.schedule_id))
        .where(col(AutomationSchedule.message_id) == message_id)
        .where(schedule_active_clause())
    ).one()
    return not active


def finalize_schedules(db: Session, schedules: Iterable[Schedule], now: datetime | None = None) -> int:
    """Chamada no MESMO ponto (e antes do mesmo commit) em que mensagens chegam a
    um estado final: expurga o conteúdo das que terminaram e, se o agendamento
    ou a mensagem de automação inteira terminou, o destinatário/texto deles.
    Não faz commit. Retorna quantas linhas foram expurgadas."""
    now = now or utcnow()
    finished = [s for s in schedules if is_finished(db, s)]
    purged = 0
    for schedule in finished:
        if purge_schedule(schedule, now):
            db.add(schedule)
            purged += 1
    if not finished:
        return 0
    db.flush()
    for group_id in {s.group_id for s in finished if s.group_id}:
        group = db.get(ScheduleGroup, group_id)
        if group is not None and group.recipient_encrypted and _group_finished(db, group_id):
            purge_group(group, now)
            db.add(group)
            purged += 1
    message_ids = set(
        db.exec(
            select(AutomationSchedule.message_id).where(col(AutomationSchedule.schedule_id).in_([s.id for s in finished]))
        ).all()
    )
    for message_id in message_ids:
        message = db.get(AutomationMessage, message_id)
        if message is not None and message.message_ciphertext and _automation_message_finished(db, message_id):
            purge_automation_message(message, now)
            db.add(message)
            purged += 1
    return purged


# --------------------------------------------------------------------------- #
# Job privacy_cleanup
# --------------------------------------------------------------------------- #
def _count(result) -> int:
    return max(int(getattr(result, "rowcount", 0) or 0), 0)


def run_cleanup(db: Session, now: datetime | None = None) -> dict[str, int]:
    """Uma passada completa (síncrona). Devolve contagens por categoria."""
    now = now or utcnow()
    counts: dict[str, int] = {}
    hash_cutoff = now - timedelta(days=settings.recipient_hash_retention_days)

    # 1. Mensagens encerradas que ainda têm conteúdo/destinatário cifrado.
    counts["schedules_content"] = _count(
        db.exec(
            sa_update(Schedule)
            .where(~schedule_active_clause())
            .where(
                or_(
                    col(Schedule.message_ciphertext).is_not(None),
                    col(Schedule.encryption_nonce).is_not(None),
                    col(Schedule.recipient_phone_encrypted).is_not(None),
                )
            )
            .values(
                message_ciphertext=None, encryption_nonce=None, encryption_key_version=None,
                recipient_phone_encrypted=None, content_purged_at=now,
            )
            .execution_options(synchronize_session=False)
        )
    )

    # 2. Agendamentos (grupos) sem nenhuma mensagem ativa com destinatário ainda cifrado.
    active_in_group = exists().where(col(Schedule.group_id) == col(ScheduleGroup.id), schedule_active_clause())
    counts["groups_recipient"] = _count(
        db.exec(
            sa_update(ScheduleGroup)
            .where(col(ScheduleGroup.recipient_encrypted).is_not(None))
            .where(~active_in_group)
            .values(recipient_encrypted=None, content_purged_at=now)
            .execution_options(synchronize_session=False)
        )
    )

    # 3. Mensagens de automação sem nenhuma entrega ativa.
    active_link = (
        select(AutomationSchedule.id)
        .join(Schedule, col(Schedule.id) == col(AutomationSchedule.schedule_id))
        .where(col(AutomationSchedule.message_id) == col(AutomationMessage.id))
        .where(schedule_active_clause())
        .exists()
    )
    counts["automation_messages"] = _count(
        db.exec(
            sa_update(AutomationMessage)
            .where(col(AutomationMessage.message_ciphertext).is_not(None))
            .where(col(AutomationMessage.created_at) < now - _AUTOMATION_GRACE)
            .where(~active_link)
            .values(message_ciphertext=None, encryption_nonce=None, encryption_key_version=None, content_purged_at=now)
            .execution_options(synchronize_session=False)
        )
    )

    # 4. Hash do destinatário depois do prazo.
    counts["recipient_hashes"] = _count(
        db.exec(
            sa_update(Schedule)
            .where(col(Schedule.recipient_phone_hash).is_not(None))
            .where(col(Schedule.content_purged_at).is_not(None))
            .where(col(Schedule.content_purged_at) < hash_cutoff)
            .values(recipient_phone_hash=None)
            .execution_options(synchronize_session=False)
        )
    ) + _count(
        db.exec(
            sa_update(ScheduleGroup)
            .where(col(ScheduleGroup.recipient_phone_hash).is_not(None))
            .where(col(ScheduleGroup.content_purged_at).is_not(None))
            .where(col(ScheduleGroup.content_purged_at) < hash_cutoff)
            .values(recipient_phone_hash=None)
            .execution_options(synchronize_session=False)
        )
    )
    expired_links = (
        select(Schedule.id)
        .where(col(Schedule.content_purged_at).is_not(None))
        .where(col(Schedule.content_purged_at) < hash_cutoff)
    )
    counts["recipient_hashes"] += _count(
        db.exec(
            sa_update(AutomationSchedule)
            .where(col(AutomationSchedule.recipient_phone_hash).is_not(None))
            .where(col(AutomationSchedule.schedule_id).in_(expired_links))
            .values(recipient_phone_hash=None)
            .execution_options(synchronize_session=False)
        )
    )
    counts["waha_message_hashes"] = _count(
        db.exec(
            sa_update(Dispatch)
            .where(col(Dispatch.waha_message_hash).is_not(None))
            .where(col(Dispatch.status).in_(list(TERMINAL_STATUSES)))
            .where(col(Dispatch.updated_at) < hash_cutoff)
            .values(waha_message_hash=None)
            .execution_options(synchronize_session=False)
        )
    )

    # 5. Trilha de login: IP/user-agent só pelo prazo curto; a linha, pelo prazo longo.
    ip_cutoff = now - timedelta(days=settings.login_ip_retention_days)
    counts["login_ips"] = _count(
        db.exec(
            sa_update(LoginAuditEvent)
            .where(col(LoginAuditEvent.created_at) < ip_cutoff)
            .where(or_(col(LoginAuditEvent.ip_address).is_not(None), col(LoginAuditEvent.user_agent).is_not(None)))
            .values(ip_address=None, user_agent=None)
            .execution_options(synchronize_session=False)
        )
    )
    counts["login_events"] = _count(
        db.exec(
            sa_delete(LoginAuditEvent)
            .where(col(LoginAuditEvent.created_at) < now - timedelta(days=settings.login_audit_retention_days))
            .execution_options(synchronize_session=False)
        )
    )

    # 6. Sessões de login: encerradas/expiradas saem; IP das ativas também tem prazo.
    session_cutoff = now - timedelta(days=settings.session_record_retention_days)
    counts["user_sessions"] = _count(
        db.exec(
            sa_delete(UserSession)
            .where(
                or_(
                    and_(col(UserSession.revoked_at).is_not(None), col(UserSession.revoked_at) < session_cutoff),
                    col(UserSession.expires_at) < session_cutoff,
                )
            )
            .execution_options(synchronize_session=False)
        )
    )
    counts["session_ips"] = _count(
        db.exec(
            sa_update(UserSession)
            .where(col(UserSession.created_at) < ip_cutoff)
            .where(or_(col(UserSession.ip_address).is_not(None), col(UserSession.user_agent).is_not(None)))
            .values(ip_address=None, user_agent=None)
            .execution_options(synchronize_session=False)
        )
    )

    # 7. Tokens de uso único já usados/expirados.
    token_cutoff = now - timedelta(days=settings.auth_token_retention_days)
    for name, model in (("password_reset_tokens", PasswordResetToken), ("email_tokens", EmailVerificationToken)):
        counts[name] = _count(
            db.exec(
                sa_delete(model)
                .where(or_(col(model.expires_at) < token_cutoff, and_(col(model.used_at).is_not(None), col(model.used_at) < token_cutoff)))
                .execution_options(synchronize_session=False)
            )
        )

    # 8. Tokens do Google de conexões desconectadas.
    counts["google_tokens"] = _count(
        db.exec(
            sa_update(CalendarConnection)
            .where(col(CalendarConnection.status) == CalendarConnectionStatus.disconnected)
            .where(or_(col(CalendarConnection.access_token_enc) != "", col(CalendarConnection.refresh_token_enc) != ""))
            .values(access_token_enc="", refresh_token_enc="", updated_at=now)
            .execution_options(synchronize_session=False)
        )
    )
    db.commit()

    # 9. Caches em memória (conversas, rate limit).
    from . import chatsvc, ratelimit

    counts["memory_cache_entries"] = chatsvc.purge_expired() + ratelimit.prune()
    return counts


def pending_waha_purges(db: Session) -> list[WhatsAppSession]:
    return list(
        db.exec(
            select(WhatsAppSession)
            .where(col(WhatsAppSession.disconnected_at).is_not(None))
            .where(col(WhatsAppSession.waha_purged_at).is_(None))
        ).all()
    )


async def purge_waha_session(waha, session: WhatsAppSession) -> bool:
    """Desloga e apaga a sessão no WAHA (credenciais + dados locais do WhatsApp
    Web). Idempotente: sessão já inexistente (404) conta como apagada."""
    from .waha import WahaError

    try:
        await waha.logout_session(session.session_name)
    except WahaError as exc:
        if exc.status_code not in (404, 400, 422):
            return False
    try:
        await waha.delete_session(session.session_name)
    except WahaError as exc:
        if exc.status_code != 404:
            return False
    return True


async def run_cleanup_async(waha=None) -> dict[str, int]:
    def _sync() -> tuple[dict[str, int], list[tuple[str, str]]]:
        with Session(get_engine()) as db:
            counts = run_cleanup(db)
            pending = [(s.id, s.session_name) for s in pending_waha_purges(db)] if waha is not None else []
        return counts, pending

    counts, pending = await asyncio.to_thread(_sync)
    purged_sessions = 0
    for session_id, _name in pending:
        with Session(get_engine()) as db:
            session = db.get(WhatsAppSession, session_id)
            if session is None:
                continue
            if await purge_waha_session(waha, session):
                session.waha_purged_at = utcnow()
                db.add(session)
                db.commit()
                purged_sessions += 1
    counts["waha_sessions"] = purged_sessions
    total = sum(counts.values())
    logger.info(
        "privacy_cleanup records_cleaned=%d %s", total, " ".join(f"{k}={v}" for k, v in sorted(counts.items()) if v)
    )
    return counts


class PrivacyCleanupService:
    """Loop de background — mesmo formato de SchedulerService/CalendarSyncService."""

    def __init__(self, waha=None) -> None:
        self.waha = waha
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="privacy-cleanup-loop")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=30)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None

    async def run_once(self) -> dict[str, int]:
        return await run_cleanup_async(self.waha)

    async def _run(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                await self.run_once()
            except Exception:
                logger.exception("erro no privacy_cleanup")
            wait = max(60.0, settings.privacy_cleanup_seconds - (time.monotonic() - started))
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass
