"""Motor de sincronização com provedores de calendário externos (Google e futuros).

Fluxo por calendário ativado (`sync_calendar`):
  1. tokens frescos (`ensure_fresh_tokens` renova se estiver perto de expirar);
  2. lista eventos — sync completo com `time_min`/`time_max` na primeira vez
     (sem `sync_token` salvo), incremental só com `sync_token` depois; se o
     provedor disser que o token expirou, refaz um sync completo na mesma
     chamada;
  3. reconcilia cada evento (`_reconcile_event`): cria/atualiza o `Event`;
     se o horário mudou e há automações ligadas, recalcula o agendamento
     *no lugar* (`_reschedule_automations`); se foi cancelado, cancela as
     automações via `cancel_schedule` (de `service.py`, intocado).

Roda como um serviço de background separado do `SchedulerService` de
WhatsApp (`CalendarSyncService`, mesmo formato start/stop/run_once) — cadência
diferente (minutos, não segundos) e domínio de falha separado: uma
instabilidade do Google não deve atrapalhar o envio de mensagens.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from . import crypto
from .calendar_providers import CalendarProvider, available_providers
from .calendar_providers.base import CalendarProviderError, OAuthTokens, RemoteCalendar, RemoteEvent
from .clock import utcnow
from .config import settings
from .db import get_engine
from .models import (
    Automation,
    AutomationMessage,
    AutomationSchedule,
    Calendar,
    CalendarConnection,
    CalendarConnectionStatus,
    Dispatch,
    DispatchStatus,
    Event,
    EventSource,
    EventStatus,
    Schedule,
)
from .service import cancel_schedule

logger = logging.getLogger("whatsapp_scheduler.calendar_sync")

_TOKEN_REFRESH_MARGIN = timedelta(seconds=60)


async def ensure_fresh_tokens(db: Session, connection: CalendarConnection, provider: CalendarProvider) -> OAuthTokens:
    """Decifra os tokens salvos; renova (e persiste) se estiverem perto de expirar."""
    tokens = OAuthTokens(
        access_token=crypto.decrypt(connection.access_token_enc),
        refresh_token=crypto.decrypt(connection.refresh_token_enc),
        expires_at=connection.token_expires_at,
        scope=connection.scope,
    )
    if tokens.expires_at > utcnow() + _TOKEN_REFRESH_MARGIN:
        return tokens

    try:
        fresh = await provider.refresh(tokens)
    except CalendarProviderError as exc:
        connection.status = CalendarConnectionStatus.error
        connection.last_sync_error = f"Falha ao renovar token: {exc}"
        connection.updated_at = utcnow()
        db.add(connection)
        db.commit()
        raise

    connection.access_token_enc = crypto.encrypt(fresh.access_token)
    connection.refresh_token_enc = crypto.encrypt(fresh.refresh_token)
    connection.token_expires_at = fresh.expires_at
    connection.updated_at = utcnow()
    db.add(connection)
    db.commit()
    return fresh


def _offset_timedelta(amount: int, unit: str) -> timedelta:
    if unit == "minutes":
        return timedelta(minutes=amount)
    if unit == "hours":
        return timedelta(hours=amount)
    if unit == "days":
        return timedelta(days=amount)
    if unit == "weeks":
        return timedelta(weeks=amount)
    raise ValueError(f"Unidade de offset desconhecida: {unit!r}")


def target_utc_for_offset(event_start_utc: datetime, amount: int, unit: str, direction: str) -> datetime:
    delta = _offset_timedelta(amount, unit)
    if direction == "before":
        return event_start_utc - delta
    if direction == "after":
        return event_start_utc + delta
    return event_start_utc  # "at"


def target_utc_for_message(
    event_start_utc: datetime, amount: int, unit: str, direction: str, position: int, gap_seconds: int
) -> datetime:
    """Igual a `target_utc_for_offset`, mais o intervalo acumulado até a
    mensagem `position` (0 = primeira, sem gap) de uma automação de várias
    mensagens. Usado tanto na criação quanto no recálculo — se o recálculo
    não reaplicar o gap por posição, uma edição de horário do evento
    colapsaria todas as mensagens da automação no mesmo instante."""
    base = target_utc_for_offset(event_start_utc, amount, unit, direction)
    return base + timedelta(seconds=position * gap_seconds)


def _reschedule_automations(db: Session, event: Event, now: datetime) -> None:
    """Evento com novo horário: recalcula cada automação ligada, no lugar (sem duplicar)."""
    automations = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
    for automation in automations:
        links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation.id)
        ).all()
        if not links:
            continue
        messages_by_id = {
            m.id: m
            for m in db.exec(
                select(AutomationMessage).where(col(AutomationMessage.automation_id) == automation.id)
            ).all()
        }
        for link in links:
            message = messages_by_id.get(link.message_id)
            schedule = db.get(Schedule, link.schedule_id)
            if message is None or schedule is None or not schedule.enabled:
                continue

            target_utc = target_utc_for_message(
                event.start_utc,
                automation.offset_amount,
                str(automation.offset_unit),
                str(automation.offset_direction),
                message.position,
                automation.message_gap_seconds,
            )
            # first_run_local é ingênuo, na timezone do próprio schedule — mesma
            # convenção usada por service.create_schedule.
            new_local = (
                target_utc.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(schedule.timezone)).replace(tzinfo=None)
            )
            schedule.first_run_local = new_local
            schedule.updated_at = now
            db.add(schedule)

            # UPDATE condicional guardado (não ler → mudar atributo → commitar):
            # a sincronização pode intercalar com dispatch_due() reivindicando a
            # mesma dispatch (ambos rodam no mesmo loop assíncrono, e há um
            # `await` de rede entre a leitura do evento e este ponto). Se a
            # dispatch já saiu de "pending" nesse meio-tempo, este UPDATE
            # simplesmente não afeta nenhuma linha — não sobrescreve um envio já
            # em andamento nem cria uma linha duplicada.
            db.exec(
                sa_update(Dispatch)
                .where(col(Dispatch.schedule_id) == schedule.id)
                .where(col(Dispatch.status) == DispatchStatus.pending)
                .values(scheduled_at_utc=target_utc, updated_at=now)
            )
    db.commit()


def _cancel_automations(db: Session, event: Event) -> None:
    automations = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
    for automation in automations:
        links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation.id)
        ).all()
        for link in links:
            cancel_schedule(db, link.schedule_id)


def reschedule_event_automations(db: Session, event: Event) -> None:
    """Wrapper público de `_reschedule_automations` — usado também pela edição
    de eventos internos (`calendar_service.update_internal_event`), não só
    pelo sync do Google. Mesma garantia: recalcula no lugar, sem duplicar."""
    _reschedule_automations(db, event, utcnow())


def cancel_event_automations(db: Session, event: Event) -> None:
    """Wrapper público de `_cancel_automations` — usado também pela exclusão
    de eventos internos (`calendar_service.delete_internal_event`)."""
    _cancel_automations(db, event)


def _reconcile_event(db: Session, calendar: Calendar, remote: RemoteEvent, now: datetime) -> None:
    existing = db.exec(
        select(Event)
        .where(col(Event.calendar_id) == calendar.id)
        .where(col(Event.external_id) == remote.external_id)
    ).first()

    if remote.cancelled:
        if existing is None:
            return  # nunca soubemos desse evento — nada a fazer
        if existing.status != EventStatus.cancelled:
            existing.status = EventStatus.cancelled
            existing.updated_at = now
            db.add(existing)
            db.commit()
            _cancel_automations(db, existing)
        return

    if remote.start_utc is None or remote.end_utc is None:
        logger.warning("evento %s sem start/end e não marcado como cancelado — ignorando", remote.external_id)
        return

    time_changed = existing is not None and existing.start_utc != remote.start_utc

    if existing is None:
        existing = Event(source=EventSource.google, calendar_id=calendar.id, external_id=remote.external_id)

    existing.title = remote.title
    existing.description = remote.description
    existing.start_utc = remote.start_utc
    existing.end_utc = remote.end_utc
    existing.timezone = remote.timezone or calendar.time_zone
    existing.all_day = remote.all_day
    existing.status = EventStatus.confirmed
    existing.recurring_event_id = remote.recurring_event_id
    existing.provider_updated_at = remote.provider_updated_at
    existing.updated_at = now
    db.add(existing)
    db.commit()
    db.refresh(existing)

    if time_changed:
        _reschedule_automations(db, existing, now)


async def sync_calendar(db: Session, provider: CalendarProvider, tokens: OAuthTokens, calendar: Calendar) -> None:
    now = utcnow()
    remote_calendar = RemoteCalendar(external_id=calendar.external_id, name=calendar.name, time_zone=calendar.time_zone)

    def _bounds() -> tuple[datetime, datetime]:
        return (
            now - timedelta(days=settings.calendar_sync_window_past_days),
            now + timedelta(days=settings.calendar_sync_window_future_days),
        )

    sync_token = calendar.sync_token
    if sync_token:
        page = await provider.list_events(tokens, remote_calendar, sync_token=sync_token)
    else:
        time_min, time_max = _bounds()
        page = await provider.list_events(tokens, remote_calendar, time_min=time_min, time_max=time_max)

    if page.sync_token_invalid:
        calendar.sync_token = None
        db.add(calendar)
        db.commit()
        time_min, time_max = _bounds()
        page = await provider.list_events(tokens, remote_calendar, time_min=time_min, time_max=time_max)

    for remote_event in page.events:
        _reconcile_event(db, calendar, remote_event, now)

    calendar.sync_token = page.next_sync_token
    calendar.updated_at = now
    db.add(calendar)
    db.commit()


async def sync_connection(
    db: Session, connection: CalendarConnection, providers: dict[str, CalendarProvider] | None = None
) -> None:
    provider = (providers or available_providers()).get(connection.provider)
    if provider is None:
        logger.warning("provedor desconhecido para a conexão %s: %s", connection.id, connection.provider)
        return
    try:
        tokens = await ensure_fresh_tokens(db, connection, provider)
        calendars = db.exec(
            select(Calendar)
            .where(col(Calendar.connection_id) == connection.id)
            .where(col(Calendar.enabled).is_(True))
        ).all()
        for calendar in calendars:
            try:
                await sync_calendar(db, provider, tokens, calendar)
            except CalendarProviderError:
                raise
            except Exception:
                logger.exception("falha ao sincronizar calendário %s", calendar.id)
        connection.status = CalendarConnectionStatus.active
        connection.last_sync_error = None
    except CalendarProviderError as exc:
        connection.status = CalendarConnectionStatus.error
        connection.last_sync_error = str(exc)
    connection.last_sync_at = utcnow()
    connection.updated_at = utcnow()
    db.add(connection)
    db.commit()


async def sync_all(providers: dict[str, CalendarProvider] | None = None) -> None:
    with Session(get_engine()) as db:
        connections = db.exec(
            select(CalendarConnection).where(col(CalendarConnection.status) != CalendarConnectionStatus.disconnected)
        ).all()
        for connection in connections:
            try:
                await sync_connection(db, connection, providers)
            except Exception:  # não deixa uma conexão ruim travar as outras
                logger.exception("falha ao sincronizar conexão %s", connection.id)


class CalendarSyncService:
    """Loop de background para sincronização automática — mesmo formato do `SchedulerService`.

    `providers` é injetável (default: o registry real) para permitir testar o
    loop inteiro com um provedor fake, sem tocar rede.
    """

    def __init__(self, providers: dict[str, CalendarProvider] | None = None) -> None:
        self._providers = providers
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="calendar-sync-loop")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=30)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None

    async def run_once(self) -> None:
        await sync_all(self._providers)

    async def _run(self) -> None:
        logger.info("sincronização de calendários iniciada (intervalo=%ss)", settings.calendar_sync_seconds)
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                await self.run_once()
            except Exception:
                logger.exception("erro no tick de sincronização de calendários")
            elapsed = time.monotonic() - started
            wait = max(1.0, settings.calendar_sync_seconds - elapsed)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass
        logger.info("sincronização de calendários parada")
