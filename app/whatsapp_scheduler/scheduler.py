"""O núcleo: comparar "horário agendado <= agora" e disparar via WAHA.

Fluxo a cada tick:
  1. materialize_due()  -> garante a próxima `Dispatch` pendente de cada regra
  2. dispatch_due()     -> envia as dispatches vencidas

O banco (SQLite) é a fonte da verdade; sobreviver a reinícios é automático porque
o filtro é sempre `scheduled_at_utc <= now`.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, col, select

from . import clock
from .config import settings
from .db import get_engine
from .models import OPEN_STATUSES, CachedMessage, Dispatch, DispatchStatus, Schedule, ScheduleDependency
from .recurrence import local_to_utc, next_run_utc, normalize_recurrence
from .waha import WahaClient, WahaError, extract_message_id

logger = logging.getLogger("whatsapp_scheduler.scheduler")

# Teto de passadas por tick (uma sequência tem no máximo 20 mensagens).
_MAX_CHAIN_PASSES = 25


# --------------------------------------------------------------------------- #
# Materialização (passo 1)
# --------------------------------------------------------------------------- #
def _dependency_gate(db: Session, sch: Schedule) -> str:
    """"wait" | "proceed" | "abort" — trava genérica de ordem entre schedules
    encadeados (mensagens de uma automação). Sem dependência = "proceed"
    sempre (comportamento de hoje, intocado para todo schedule "normal").

    A trava é pelo ESTADO CONFIRMADO da predecessora, não por horário
    pré-calculado: só libera quando a última dispatch dela chegou a `sent`;
    se ela terminou (não está mais `enabled`) sem ter sido enviada — falhou,
    foi pulada por atraso, foi cancelada, ou sua própria cadeia já abortou
    sem nunca despachar — a cadeia aborta aqui também, em vez de disparar
    fora de ordem. Isso resolve a cadeia inteira em no máximo N ticks (um
    elo por tick), porque uma dependência abortada sem nunca ter tido
    dispatch (`last is None`) ainda cai no ramo `not dep.enabled` assim que
    ela própria for desativada pelo auto-disable que `_materialize_schedule`
    já faz hoje para todo schedule de disparo único.
    """
    dep = db.exec(
        select(ScheduleDependency).where(col(ScheduleDependency.schedule_id) == sch.id)
    ).first()
    if dep is None:
        return "proceed"

    dependency = db.get(Schedule, dep.depends_on_schedule_id)
    if dependency is None:
        return "abort"  # referência solta, não deveria acontecer — falha segura

    last = db.exec(
        select(Dispatch)
        .where(col(Dispatch.schedule_id) == dependency.id)
        .order_by(col(Dispatch.scheduled_at_utc).desc())
    ).first()
    if last is not None and last.status == DispatchStatus.sent:
        return "proceed"
    if not dependency.enabled:
        return "abort"
    return "wait"


def _compute_next_utc(sch: Schedule, last: Dispatch | None, now: datetime) -> datetime | None:
    """Quando deve acontecer a próxima ocorrência desta regra? None = nunca mais."""
    if last is None:
        # Primeira ocorrência de todas: honra exatamente o horário escolhido,
        # esteja ele no passado (a regra de atraso decide enviar/pular) ou futuro.
        return local_to_utc(sch.first_run_local, sch.timezone)

    if not sch.recurrence:
        return None  # disparo único já tem sua dispatch

    cron = normalize_recurrence(sch.recurrence)
    after = max(last.scheduled_at_utc, now)
    return next_run_utc(cron, sch.timezone, after)


def _materialize_schedule(
    db: Session, sch: Schedule, now: datetime, *, known_open: set[str] | None = None
) -> Dispatch | None:
    """`known_open`: ids de schedules que o chamador já sabe (numa consulta só)
    terem dispatch aberta — evita 1 consulta por regra a cada tick, que com
    centenas de mensagens de automação agendadas era quase tudo trabalho à toa."""
    if known_open is not None:
        if sch.id in known_open:
            return None
    else:
        already_open = db.exec(
            select(Dispatch)
            .where(col(Dispatch.schedule_id) == sch.id)
            .where(col(Dispatch.status).in_(list(OPEN_STATUSES)))
        ).first()
        if already_open is not None:
            return None

    gate = _dependency_gate(db, sch)
    if gate == "wait":
        return None
    if gate == "abort":
        sch.enabled = False
        sch.updated_at = now
        db.add(sch)
        return None

    last = db.exec(
        select(Dispatch)
        .where(col(Dispatch.schedule_id) == sch.id)
        .order_by(col(Dispatch.scheduled_at_utc).desc())
    ).first()

    next_utc = _compute_next_utc(sch, last, now)
    if next_utc is None:
        if not sch.recurrence and sch.enabled:
            sch.enabled = False
            sch.updated_at = now
            db.add(sch)
        return None

    dispatch = Dispatch(schedule_id=sch.id, scheduled_at_utc=next_utc, status=DispatchStatus.pending)
    db.add(dispatch)
    logger.debug("schedule %s -> nova dispatch em %s UTC", sch.id, next_utc.isoformat())
    return dispatch


def _recover_stuck(db: Session, now: datetime) -> None:
    cutoff = now - timedelta(minutes=settings.stuck_processing_minutes)
    stuck = db.exec(
        select(Dispatch)
        .where(col(Dispatch.status) == DispatchStatus.processing)
        .where(col(Dispatch.updated_at) < cutoff)
    ).all()
    for d in stuck:
        d.status = DispatchStatus.pending
        d.last_error = "Recuperada: presa em 'processing' (provável reinício abrupto)."
        d.updated_at = now
        db.add(d)
    if stuck:
        logger.warning("recuperadas %d dispatches presas em processing", len(stuck))


def _waiting_on_open_chain(
    schedule_id: str, deps: dict[str, str], open_ids: set[str], enabled_ids: set[str], *, _depth: int = 0
) -> bool:
    """True se a cadeia desta mensagem está travada numa antecessora ATIVA que ainda tem
    dispatch aberta (direta ou mais atrás na sequência) — nesse caso `_dependency_gate`
    responderia "wait", então nem precisa consultar o banco. Com N mensagens agendadas
    esperando, isso troca ~3 consultas por mensagem, a cada tick, por zero."""
    predecessor = deps.get(schedule_id)
    if predecessor is None or predecessor not in enabled_ids or _depth > 50:
        return False
    if predecessor in open_ids:
        return True
    return _waiting_on_open_chain(predecessor, deps, open_ids, enabled_ids, _depth=_depth + 1)


def materialize_due() -> None:
    """Sync — roda em thread separada a partir do loop."""
    now = clock.utcnow()
    with Session(get_engine()) as db:
        _recover_stuck(db, now)
        schedules = db.exec(select(Schedule).where(col(Schedule.enabled).is_(True))).all()
        open_ids = set(
            db.exec(select(Dispatch.schedule_id).where(col(Dispatch.status).in_(list(OPEN_STATUSES)))).all()
        )
        enabled_ids = {s.id for s in schedules}
        deps = {
            row.schedule_id: row.depends_on_schedule_id
            for row in db.exec(
                select(ScheduleDependency)
                .join(Schedule, col(Schedule.id) == col(ScheduleDependency.schedule_id))
                .where(col(Schedule.enabled).is_(True))
            ).all()
        }
        for sch in schedules:
            if _waiting_on_open_chain(sch.id, deps, open_ids, enabled_ids):
                continue  # a mensagem anterior ainda não saiu: o gate responderia "wait" — sem gastar consultas
            try:
                _materialize_schedule(db, sch, now, known_open=open_ids)
            except Exception:  # não deixa uma regra ruim travar as outras
                logger.exception("falha ao materializar schedule %s", sch.id)
        db.commit()


def materialize_one(db: Session, sch: Schedule) -> Dispatch | None:
    """Materializa uma única regra usando uma sessão já aberta (usado pela API)."""
    dispatch = _materialize_schedule(db, sch, clock.utcnow())
    db.commit()
    return dispatch


# --------------------------------------------------------------------------- #
# Disparo (passo 2)
# --------------------------------------------------------------------------- #
def _backoff_seconds(attempt: int) -> int:
    table = settings.backoff_seconds or [60]
    return table[min(max(attempt, 1), len(table)) - 1]


async def dispatch_due(waha: WahaClient) -> int:
    """Envia todas as dispatches vencidas. Retorna quantas foram efetivamente enviadas."""
    now = clock.utcnow()
    claimed: list[str] = []

    with Session(get_engine()) as db:
        rows = db.exec(
            select(Dispatch)
            .where(col(Dispatch.status) == DispatchStatus.pending)
            .where(col(Dispatch.scheduled_at_utc) <= now)
            .order_by(col(Dispatch.scheduled_at_utc))
            .limit(settings.dispatch_batch)
        ).all()
        for d in rows:
            overdue_min = (now - d.scheduled_at_utc).total_seconds() / 60.0
            if overdue_min > settings.max_overdue_minutes:
                d.status = DispatchStatus.skipped
                d.last_error = f"Atrasada {int(overdue_min)} min (limite {settings.max_overdue_minutes})."
                d.updated_at = now
                db.add(d)
                logger.warning("dispatch %s pulada (atraso de %d min)", d.id, int(overdue_min))
                continue
            d.status = DispatchStatus.processing
            d.updated_at = now
            db.add(d)
            claimed.append(d.id)
        db.commit()

    sent = 0
    for i, dispatch_id in enumerate(claimed):
        if await _send_one(waha, dispatch_id):
            sent += 1
        if i < len(claimed) - 1:
            base = max(settings.send_jitter_seconds, 0.0)
            if base:
                await asyncio.sleep(base + random.uniform(0, base))
    return sent


async def _send_one(waha: WahaClient, dispatch_id: str) -> bool:
    # 1. lê o necessário e fecha a sessão antes de qualquer await de rede
    with Session(get_engine()) as db:
        d = db.get(Dispatch, dispatch_id)
        if d is None or d.status != DispatchStatus.processing:
            return False
        sch = db.get(Schedule, d.schedule_id)
        if sch is None:
            d.status = DispatchStatus.canceled
            d.last_error = "Schedule removido antes do envio."
            d.updated_at = clock.utcnow()
            db.add(d)
            db.commit()
            return False
        session_name = sch.session
        chat_id = sch.chat_id
        text = sch.text
        max_attempts = sch.max_attempts
        owner_id = sch.user_id
        attempts = d.attempts

    # 2. a sessão do WhatsApp está pronta?
    try:
        info = await waha.get_session_status(session_name)
        status = str(info.get("status") or "").upper()
        session_err = None
    except WahaError as exc:
        status, session_err = "", str(exc)

    if status != "WORKING":
        with Session(get_engine()) as db:
            d = db.get(Dispatch, dispatch_id)
            if d is not None and d.status == DispatchStatus.processing:
                d.status = DispatchStatus.pending
                d.scheduled_at_utc = clock.utcnow() + timedelta(seconds=60)
                d.last_error = (
                    f"Sessão '{session_name}' não está pronta (status={status or 'desconhecido'}). "
                    f"{session_err or 'Pareie o WhatsApp para retomar.'}"
                )
                d.updated_at = clock.utcnow()
                db.add(d)
                db.commit()
        logger.warning("dispatch %s adiada: sessão '%s' status=%s", dispatch_id, session_name, status)
        return False

    # 3. envia (sem sessão de banco aberta)
    try:
        payload = await waha.send_text(session_name, chat_id, text)
        ok, err, message_id = True, None, extract_message_id(payload)
    except WahaError as exc:
        ok, err, message_id = False, str(exc), None

    # 4. grava o resultado
    with Session(get_engine()) as db:
        d = db.get(Dispatch, dispatch_id)
        if d is None:
            return ok
        now = clock.utcnow()
        # O usuário pode ter cancelado enquanto o envio estava em andamento.
        # Se o envio deu certo a mensagem já saiu, então o registro fiel é
        # "sent"; se falhou, o cancelamento vale — não ressuscita com retry.
        canceled_meanwhile = d.status != DispatchStatus.processing
        if ok:
            d.status = DispatchStatus.sent
            d.sent_at_utc = now
            d.waha_message_id = message_id
            d.last_error = None
            logger.info("dispatch %s enviada para %s", dispatch_id, chat_id)
            _remember_sent_message(db, owner_id, chat_id, text, message_id, now)
        elif canceled_meanwhile:
            logger.info("dispatch %s cancelada durante o envio; falha não gera retry", dispatch_id)
        else:
            d.attempts = attempts + 1
            d.last_error = (err or "erro desconhecido")[:1000]
            if d.attempts < max_attempts:
                delay = _backoff_seconds(d.attempts)
                d.status = DispatchStatus.pending
                d.scheduled_at_utc = now + timedelta(seconds=delay)
                logger.warning(
                    "dispatch %s falhou (tentativa %d/%d), retry em %ds: %s",
                    dispatch_id, d.attempts, max_attempts, delay, err,
                )
            else:
                d.status = DispatchStatus.failed
                logger.error(
                    "dispatch %s falhou definitivamente (%d tentativas): %s",
                    dispatch_id, d.attempts, err,
                )
        d.updated_at = now
        db.add(d)
        db.commit()
    return ok


def _remember_sent_message(
    db: Session, user_id: str | None, chat_id: str, text: str, message_id: str | None, now: datetime
) -> None:
    """Grava a mensagem agendada que acabou de sair no cache da conversa (mesma
    coisa que `chatsvc.send_now` faz no envio imediato) — assim ela já aparece
    no histórico da conversa sem esperar a próxima busca no WAHA."""
    if not message_id or not user_id or db.get(CachedMessage, message_id) is not None:
        return
    db.add(
        CachedMessage(
            message_id=message_id,
            user_id=user_id,
            chat_id=chat_id,
            ts=int(now.replace(tzinfo=timezone.utc).timestamp()),
            from_me=True,
            body=text,
            msg_type="chat",
        )
    )


# --------------------------------------------------------------------------- #
# Serviço de background
# --------------------------------------------------------------------------- #
class SchedulerService:
    def __init__(self, waha: WahaClient) -> None:
        self.waha = waha
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="scheduler-loop")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=settings.request_timeout + 5)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None

    async def run_once(self) -> int:
        """Um tick. Repete enquanto algo foi enviado: a mensagem N+1 de uma
        sequência só materializa depois que a N é confirmada como enviada
        (`_dependency_gate`), então sem repetir cada mensagem esperaria um
        tick inteiro (30 s) pela anterior. O espaçamento entre elas é o mesmo
        jitter usado entre envios de um lote."""
        total = 0
        for _ in range(_MAX_CHAIN_PASSES):
            await asyncio.to_thread(materialize_due)
            sent = await dispatch_due(self.waha)
            total += sent
            if not sent:
                break
            base = max(settings.send_jitter_seconds, 0.0)
            if base:
                await asyncio.sleep(base + random.uniform(0, base))
        return total

    async def _run(self) -> None:
        logger.info("scheduler iniciado (tick=%ss)", settings.tick_seconds)
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                await self.run_once()
            except Exception:
                logger.exception("erro no tick do scheduler")
            elapsed = time.monotonic() - started
            wait = max(1.0, settings.tick_seconds - elapsed)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass
        logger.info("scheduler parado")
