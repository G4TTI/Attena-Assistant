"""Motor de sincronização com provedores de calendário externos (Google e futuros).

Fluxo por calendário ativado (`sync_calendar`):
  1. tokens frescos (`ensure_fresh_tokens` renova se estiver perto de expirar);
  2. lista eventos — sync completo com `time_min`/`time_max` na primeira vez
     (sem `sync_token` salvo), incremental só com `sync_token` depois; se o
     provedor disser que o token expirou, refaz um sync completo na mesma
     chamada;
  3. reconcilia cada evento (`_reconcile_event`): cria/atualiza o `Event`;
     se o horário mudou e há automações ligadas, remarca o agendamento *no
     lugar* (`_reschedule_automations` -> `service.reschedule_group`); se foi
     cancelado, cancela as automações via `service.cancel_schedules`.

Roda como um serviço de background separado do `SchedulerService` de
WhatsApp (`CalendarSyncService`, mesmo formato start/stop/run_once) — cadência
diferente (minutos, não segundos) e domínio de falha separado: uma
instabilidade do Google não deve atrapalhar o envio de mensagens.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta

from sqlmodel import Session, col, select

from . import crypto, timing
from .calendar_providers import CalendarProvider, available_providers
from .calendar_providers.base import CalendarProviderError, OAuthTokens, RemoteCalendar, RemoteEvent
from .clock import utcnow
from .config import settings
from .db import get_engine
from .models import (
    Automation,
    AutomationSchedule,
    Calendar,
    CalendarConnection,
    CalendarConnectionStatus,
    Event,
    EventSource,
    EventStatus,
    Schedule,
    ScheduleGroup,
)
from .service import backfill_groups, cancel_schedules, reschedule_group

# O cálculo de horário mora em `timing.py`; estes nomes continuam exportados
# daqui só porque testes e chamadores antigos os importam de `calendar_sync`.
target_utc_for_message = timing.target_utc_for_message
target_utc_for_offset = timing.target_utc_for_offset

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


def _automation_target_utc(automation: Automation, event: Event) -> datetime:
    """Novo horário de INÍCIO de uma automação para o horário atual do evento —
    o cálculo é o de `timing` (o mesmo da criação e do preview)."""
    return timing.target_utc_for_offset(
        event.start_utc,
        automation.offset_amount,
        str(automation.offset_unit),
        str(automation.offset_direction),
        custom_time_local=automation.custom_time_local,
        event_timezone=event.timezone or settings.default_timezone,
    )


def _reschedule_automations(db: Session, event: Event, now: datetime) -> None:
    """Evento com novo horário: remarca cada agendamento (grupo) das automações
    ligadas, no lugar (sem duplicar) — `service.reschedule_group` é o mesmo
    caminho usado ao editar o horário de um agendamento."""
    automations = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
    if not automations:
        return
    if event.user_id:
        backfill_groups(db, event.user_id)  # schedules antigos ainda sem grupo
    for automation in automations:
        links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation.id)
        ).all()
        schedule_ids = [link.schedule_id for link in links]
        if not schedule_ids:
            continue
        group_ids = {
            gid
            for gid in db.exec(select(Schedule.group_id).where(col(Schedule.id).in_(schedule_ids))).all()
            if gid is not None
        }
        new_start_utc = _automation_target_utc(automation, event)
        for group_id in group_ids:
            group = db.get(ScheduleGroup, group_id)
            if group is not None:
                reschedule_group(db, group, new_start_utc)


def _cancel_automations(db: Session, event: Event) -> None:
    automations = db.exec(select(Automation).where(col(Automation.event_id) == event.id)).all()
    for automation in automations:
        links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation.id)
        ).all()
        cancel_schedules(db, [link.schedule_id for link in links])


def reschedule_event_automations(db: Session, event: Event) -> None:
    """Wrapper público de `_reschedule_automations` — usado também pela edição
    de eventos internos (`calendar_service.update_internal_event`), não só
    pelo sync do Google. Mesma garantia: recalcula no lugar, sem duplicar."""
    _reschedule_automations(db, event, utcnow())


def cancel_event_automations(db: Session, event: Event) -> None:
    """Wrapper público de `_cancel_automations` — usado também pela exclusão
    de eventos internos (`calendar_service.delete_internal_event`)."""
    _cancel_automations(db, event)


def _reconcile_event(db: Session, calendar: Calendar, user_id: str | None, remote: RemoteEvent, now: datetime) -> None:
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
        existing = Event(
            user_id=user_id, source=EventSource.google, calendar_id=calendar.id, external_id=remote.external_id
        )
    elif (
        (existing.user_id or user_id) == existing.user_id
        and existing.title == remote.title
        and existing.description == remote.description
        and existing.start_utc == remote.start_utc
        and existing.end_utc == remote.end_utc
        and existing.timezone == (remote.timezone or calendar.time_zone)
        and existing.all_day == remote.all_day
        and existing.status == EventStatus.confirmed
        and existing.recurring_event_id == remote.recurring_event_id
        and existing.provider_updated_at == remote.provider_updated_at
    ):
        return  # nada mudou — um sync completo relia (e regravava) o calendário inteiro à toa

    existing.user_id = existing.user_id or user_id  # backfill se o evento foi sincronizado antes da conexão ter dono
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


async def sync_calendar(
    db: Session, provider: CalendarProvider, tokens: OAuthTokens, calendar: Calendar, user_id: str | None
) -> None:
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

    def _reconcile_page() -> None:
        for remote_event in page.events:
            _reconcile_event(db, calendar, user_id, remote_event, now)

    # Um sync completo (primeira vez, ou token expirado) traz centenas de
    # eventos e cada um faz consulta + commit em SQLite. Direto na coroutine,
    # isso segurava o único event loop do processo — o app inteiro (modais,
    # sidebar, outros usuários) ficava travado enquanto o Google sincronizava.
    # Mesmo padrão de `asyncio.to_thread` que o scheduler já usa; o mesmo `db`
    # é usado de forma sequencial (nunca concorrente), então é seguro.
    await asyncio.to_thread(_reconcile_page)

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
                await sync_calendar(db, provider, tokens, calendar, connection.user_id)
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
