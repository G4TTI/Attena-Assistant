"""Regra de negócio de calendários externos — equivalente a `service.py`, mas
para conexões/calendários/eventos/automações. Sempre que possível, chama as
funções já existentes e intocadas de `service.py` (`create_schedule`,
`cancel_schedule`) em vez de duplicar a lógica de agendamento.
"""

from __future__ import annotations

import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from datetime import time as dt_time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete as sa_delete
from sqlmodel import Session, col, select

from . import crypto
from .calendar_providers import get_provider
from .calendar_providers.base import CalendarProviderError, RemoteCalendar
from .calendar_sync import (
    cancel_event_automations,
    ensure_fresh_tokens,
    reschedule_event_automations,
    sync_connection,
    target_utc_for_message,
    target_utc_for_offset,
)
from .chatsvc import list_chats
from .clock import utcnow
from .config import settings
from .models import (
    Automation,
    AutomationMessage,
    AutomationSchedule,
    Calendar,
    CalendarConnection,
    CalendarConnectionStatus,
    Event,
    EventAutomation,
    EventSource,
    EventStatus,
    EventSyncStatus,
    OffsetDirection,
    OffsetUnit,
    Schedule,
)
from .recipients import RecipientError, normalize_recipient
from .recurrence import RecurrenceError, local_to_utc, parse_hhmm, utc_to_local
from .service import ValidationError, cancel_schedule, create_schedule

logger = logging.getLogger("whatsapp_scheduler.calendar_service")


class NotConfiguredError(RuntimeError):
    """Credenciais do provedor (ou a chave de cifra) ainda não configuradas."""


def missing_config(provider_key: str = "google") -> list[str]:
    """Nomes exatos das variáveis de ambiente que faltam configurar."""
    missing = []
    if not crypto.is_configured():
        missing.append("TOKEN_ENCRYPTION_KEY")
    provider = get_provider(provider_key)
    if not provider.is_configured():
        missing += ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
    return missing


def start_connect(provider_key: str = "google") -> tuple[str, str]:
    """Retorna (authorize_url, state); o state deve ir num cookie httponly p/ validar no callback."""
    missing = missing_config(provider_key)
    if missing:
        raise NotConfiguredError(
            "Integração não configurada. Defina no .env: " + ", ".join(missing)
        )
    provider = get_provider(provider_key)
    state = secrets.token_urlsafe(24)
    return provider.get_authorize_url(state), state


async def finish_connect(db: Session, *, provider_key: str, code: str, user_id: str) -> CalendarConnection:
    missing = missing_config(provider_key)
    if missing:
        raise NotConfiguredError("Integração não configurada. Defina no .env: " + ", ".join(missing))

    provider = get_provider(provider_key)
    tokens = await provider.exchange_code(code)
    email = await provider.get_account_identifier(tokens)

    existing = None
    if email:
        existing = db.exec(
            select(CalendarConnection)
            .where(col(CalendarConnection.user_id) == user_id)
            .where(col(CalendarConnection.provider) == provider_key)
            .where(col(CalendarConnection.account_identifier) == email)
        ).first()

    connection = existing or CalendarConnection(provider=provider_key, user_id=user_id)
    connection.account_identifier = email or connection.account_identifier or "conta Google"
    connection.access_token_enc = crypto.encrypt(tokens.access_token)
    connection.refresh_token_enc = crypto.encrypt(tokens.refresh_token)
    connection.token_expires_at = tokens.expires_at
    connection.scope = tokens.scope
    connection.status = CalendarConnectionStatus.active
    connection.last_sync_error = None
    connection.updated_at = utcnow()
    db.add(connection)
    db.commit()
    db.refresh(connection)

    # Já popula a lista de calendários disponíveis (desativados por padrão —
    # o usuário escolhe quais sincronizar a seguir).
    await refresh_remote_calendars(db, connection)
    return connection


async def refresh_remote_calendars(db: Session, connection: CalendarConnection) -> list[Calendar]:
    provider = get_provider(connection.provider)
    tokens = await ensure_fresh_tokens(db, connection, provider)
    try:
        remote_calendars = await provider.list_calendars(tokens)
    except CalendarProviderError as exc:
        connection.status = CalendarConnectionStatus.error
        connection.last_sync_error = str(exc)
        connection.updated_at = utcnow()
        db.add(connection)
        db.commit()
        raise

    existing_by_external = {
        c.external_id: c
        for c in db.exec(select(Calendar).where(col(Calendar.connection_id) == connection.id)).all()
    }
    rows: list[Calendar] = []
    for remote in remote_calendars:
        row = existing_by_external.get(remote.external_id)
        if row is None:
            row = Calendar(connection_id=connection.id, external_id=remote.external_id, enabled=False)
        row.name = remote.name
        row.time_zone = remote.time_zone
        row.color = remote.color
        row.updated_at = utcnow()
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def list_connections(db: Session, user_id: str) -> list[CalendarConnection]:
    """Só conexões que ainda "existem" pro usuário — `disconnected` é um
    soft-delete (a linha continua no banco só pra manter o histórico de
    schedules já cancelados por ela), então nunca deve aparecer como uma
    conta conectada em Configurações, nem virar a "conexão principal" do
    Dashboard. Reconectar a mesma conta cria uma linha nova apenas se essa
    aqui não existir mais — ver `finish_connect`, que já reaproveita por
    (user_id, provider, e-mail) independente do status."""
    return list(
        db.exec(
            select(CalendarConnection)
            .where(col(CalendarConnection.user_id) == user_id)
            .where(col(CalendarConnection.status) != CalendarConnectionStatus.disconnected)
            .order_by(col(CalendarConnection.created_at))
        ).all()
    )


def _owned_connection(db: Session, connection_id: str, user_id: str) -> CalendarConnection | None:
    connection = db.get(CalendarConnection, connection_id)
    if connection is None or connection.user_id != user_id:
        return None
    return connection


_WRITE_SCOPE = "https://www.googleapis.com/auth/calendar"


def connection_has_write_scope(connection: CalendarConnection) -> bool:
    """Compara por token exato (não substring) — `"...calendar.readonly"`
    contém a palavra "calendar" mas NÃO é o escopo de escrita."""
    return _WRITE_SCOPE in (connection.scope or "").split()


def list_calendars(db: Session, connection_id: str, user_id: str) -> list[Calendar]:
    if _owned_connection(db, connection_id, user_id) is None:
        return []
    return list(
        db.exec(
            select(Calendar).where(col(Calendar.connection_id) == connection_id).order_by(col(Calendar.name))
        ).all()
    )


def _owned_calendar(db: Session, calendar_id: str, user_id: str) -> Calendar | None:
    calendar = db.get(Calendar, calendar_id)
    if calendar is None:
        return None
    connection = db.get(CalendarConnection, calendar.connection_id)
    if connection is None or connection.user_id != user_id:
        return None
    return calendar


def set_calendar_enabled(db: Session, calendar_id: str, enabled: bool, user_id: str) -> Calendar | None:
    calendar = _owned_calendar(db, calendar_id, user_id)
    if calendar is None:
        return None
    calendar.enabled = enabled
    calendar.updated_at = utcnow()
    if not enabled:
        # Desativar só para de sincronizar esse calendário daqui pra frente;
        # eventos/automações já existentes não são tocados.
        calendar.sync_token = None
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


async def sync_now(db: Session, connection_id: str, user_id: str) -> CalendarConnection | None:
    connection = _owned_connection(db, connection_id, user_id)
    if connection is None:
        return None
    await sync_connection(db, connection)
    db.refresh(connection)
    return connection


def disconnect(db: Session, connection_id: str, user_id: str) -> bool:
    """Para novas sincronizações e cancela mensagens futuras ainda pendentes
    ligadas a esta conta — preserva histórico e mensagens já enviadas.
    """
    connection = _owned_connection(db, connection_id, user_id)
    if connection is None:
        return False

    calendar_ids = [
        c.id for c in db.exec(select(Calendar).where(col(Calendar.connection_id) == connection_id)).all()
    ]
    if calendar_ids:
        event_ids = [
            e.id for e in db.exec(select(Event).where(col(Event.calendar_id).in_(calendar_ids))).all()
        ]
        if event_ids:
            automation_ids = [
                a.id for a in db.exec(select(Automation).where(col(Automation.event_id).in_(event_ids))).all()
            ]
            if automation_ids:
                links = db.exec(
                    select(AutomationSchedule).where(col(AutomationSchedule.automation_id).in_(automation_ids))
                ).all()
                for link in links:
                    cancel_schedule(db, link.schedule_id)

    connection.status = CalendarConnectionStatus.disconnected
    connection.updated_at = utcnow()
    db.add(connection)
    db.commit()
    return True


def _parse_offset(offset_unit: str, offset_direction: str) -> tuple[OffsetUnit, OffsetDirection]:
    try:
        unit = OffsetUnit(offset_unit)
    except ValueError as exc:
        raise ValidationError(f"Unidade de tempo inválida: {offset_unit!r}") from exc
    try:
        direction = OffsetDirection(offset_direction)
    except ValueError as exc:
        raise ValidationError(f"Regra de tempo inválida: {offset_direction!r}") from exc
    return unit, direction


def _resolve_custom_time(direction: OffsetDirection, custom_time_local: str | None) -> str | None:
    """direction != custom: ignora qualquer valor recebido (nunca persiste
    lixo). direction == custom: exige um "HH:MM" válido."""
    if direction != OffsetDirection.custom:
        return None
    if not custom_time_local or not custom_time_local.strip():
        raise ValidationError("Informe o horário do disparo personalizado.")
    try:
        parse_hhmm(custom_time_local.strip())
    except RecurrenceError as exc:
        raise ValidationError(str(exc)) from exc
    return custom_time_local.strip()


_DUPLICATE_WINDOW = timedelta(seconds=15)


def _find_duplicate_automation(
    db: Session,
    *,
    event_id: str,
    unit: OffsetUnit,
    direction: OffsetDirection,
    amount: int,
    custom_time_local: str | None,
    message_texts: list[str],
    chat_ids: set[str],
    now: datetime,
) -> Automation | None:
    """Evita duplicar: duplo clique, duplo submit, ou salvar a mesma automação
    duas vezes. A trava é no nível da `Automation` inteira (não por
    mensagem/destinatário individual) — como uma automação agora cria N
    `Schedule`s (mensagens x destinatários), checar duplicidade por-mensagem
    faria o segundo submit tentar ligar o `Schedule` já existente numa nova
    `AutomationSchedule`, violando o UNIQUE de `schedule_id` ali. Escopado em
    "todos os schedules ainda ativos" e numa janela curta pra não atrapalhar
    o fluxo de editar (cancela a antiga e cria uma quase idêntica logo em
    seguida — ver `update_event_automation`)."""
    window_start = now - _DUPLICATE_WINDOW
    candidates = db.exec(
        select(Automation)
        .where(col(Automation.event_id) == event_id)
        .where(col(Automation.offset_amount) == amount)
        .where(col(Automation.offset_unit) == unit)
        .where(col(Automation.offset_direction) == direction)
        .where(col(Automation.custom_time_local) == custom_time_local)
        .where(col(Automation.created_at) >= window_start)
    ).all()
    for automation in candidates:
        messages = db.exec(
            select(AutomationMessage)
            .where(col(AutomationMessage.automation_id) == automation.id)
            .order_by(col(AutomationMessage.position))
        ).all()
        if [m.text for m in messages] != message_texts:
            continue
        links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation.id)
        ).all()
        if {link.recipient_chat_id for link in links} != chat_ids:
            continue
        schedule_ids = [link.schedule_id for link in links]
        schedules = (
            db.exec(select(Schedule).where(col(Schedule.id).in_(schedule_ids))).all() if schedule_ids else []
        )
        if not schedules or not all(s.enabled for s in schedules):
            continue  # já cancelada/editada — não é o mesmo submit, deixa criar de novo
        return automation
    return None


def create_event_automation(
    db: Session,
    *,
    event_id: str,
    user_id: str,
    waha_session: str,
    recipients: list[str],
    messages: list[str],
    offset_amount: int,
    offset_unit: str,
    offset_direction: str,
    custom_time_local: str | None = None,
    timezone_name: str | None = None,
    max_attempts: int = 3,
) -> Automation:
    event = db.get(Event, event_id)
    if event is None or event.user_id != user_id:
        raise ValidationError("Evento não encontrado.")

    recipients = [r.strip() for r in recipients if r.strip()]
    if not recipients:
        raise ValidationError("Selecione ao menos um destinatário.")
    message_texts = [m.strip() for m in messages if m.strip()]
    if not message_texts:
        raise ValidationError("Adicione ao menos uma mensagem.")
    if offset_amount < 0:
        raise ValidationError("O tempo da regra não pode ser negativo.")

    unit, direction = _parse_offset(offset_unit, offset_direction)
    custom_time_local = _resolve_custom_time(direction, custom_time_local)
    tz_name = timezone_name or event.timezone or settings.default_timezone
    event_tz = event.timezone or settings.default_timezone

    chat_ids: list[str] = []
    for recipient in recipients:
        try:
            chat_ids.append(normalize_recipient(recipient))
        except RecipientError as exc:
            raise ValidationError(str(exc)) from exc

    now = utcnow()
    duplicate = _find_duplicate_automation(
        db,
        event_id=event.id,
        unit=unit,
        direction=direction,
        amount=offset_amount,
        custom_time_local=custom_time_local,
        message_texts=message_texts,
        chat_ids=set(chat_ids),
        now=now,
    )
    if duplicate is not None:
        return duplicate

    automation = Automation(
        event_id=event.id,
        offset_amount=offset_amount,
        offset_unit=unit,
        offset_direction=direction,
        custom_time_local=custom_time_local,
    )
    db.add(automation)
    db.commit()
    db.refresh(automation)

    message_rows: list[AutomationMessage] = []
    for position, text in enumerate(message_texts):
        message = AutomationMessage(automation_id=automation.id, position=position, text=text)
        db.add(message)
        db.commit()
        db.refresh(message)
        message_rows.append(message)

    # Uma cadeia de Schedules por destinatário (mensagem 0 sem dependência,
    # cada mensagem seguinte depende da anterior DO MESMO destinatário —
    # garante ordem de entrega mesmo sob falha/retry, ver scheduler.py).
    for recipient, chat_id in zip(recipients, chat_ids):
        previous_schedule_id: str | None = None
        for message in message_rows:
            target_utc = target_utc_for_message(
                event.start_utc,
                offset_amount,
                unit.value,
                direction.value,
                message.position,
                automation.message_gap_seconds,
                custom_time_local=custom_time_local,
                event_timezone=event_tz,
            )
            schedule = create_schedule(
                db,
                user_id=user_id,
                session=waha_session,
                recipient=recipient,
                text=message.text,
                send_at=target_utc.replace(tzinfo=timezone.utc),
                timezone=tz_name,
                max_attempts=max_attempts,
                depends_on_schedule_id=previous_schedule_id,
            )
            db.add(
                AutomationSchedule(
                    automation_id=automation.id,
                    message_id=message.id,
                    schedule_id=schedule.id,
                    recipient_chat_id=chat_id,
                )
            )
            db.commit()
            previous_schedule_id = schedule.id

    return automation


def _owned_automation(db: Session, automation_id: str, user_id: str) -> Automation | None:
    automation = db.get(Automation, automation_id)
    if automation is None:
        return None
    event = db.get(Event, automation.event_id)
    if event is None or event.user_id != user_id:
        return None
    return automation


def remove_event_automation(db: Session, automation_id: str, user_id: str) -> bool:
    automation = _owned_automation(db, automation_id, user_id)
    if automation is None:
        return False
    links = db.exec(select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation_id)).all()
    for link in links:
        cancel_schedule(db, link.schedule_id)
    return True


def update_event_automation(
    db: Session,
    automation_id: str,
    *,
    user_id: str,
    waha_session: str,
    recipients: list[str],
    messages: list[str],
    offset_amount: int,
    offset_unit: str,
    offset_direction: str,
    custom_time_local: str | None = None,
    timezone_name: str | None = None,
) -> Automation:
    """"Editar" = cancelar todos os schedules da automação antiga + apagar as
    linhas de ligação + criar uma nova do zero. Não muta `Schedule` em lugar:
    se alguma mensagem já tivesse uma dispatch `sent`, mutar reescreveria
    retroativamente o histórico do que já foi enviado.

    Ordem obrigatória (SQLite, `PRAGMA foreign_keys=ON`, sem `Relationship()`
    do ORM pra ordenar sozinho): cancelar os schedules primeiro (preserva
    Schedule/Dispatch como histórico), depois as linhas-folha
    (AutomationSchedule), depois AutomationMessage, só então Automation.
    """
    automation = _owned_automation(db, automation_id, user_id)
    if automation is None:
        raise ValidationError("Automação não encontrada.")
    event_id = automation.event_id

    links = db.exec(select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation_id)).all()
    for link in links:
        cancel_schedule(db, link.schedule_id)
    db.exec(sa_delete(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation_id))
    db.exec(sa_delete(AutomationMessage).where(col(AutomationMessage.automation_id) == automation_id))
    db.delete(automation)
    db.commit()

    return create_event_automation(
        db,
        event_id=event_id,
        user_id=user_id,
        waha_session=waha_session,
        recipients=recipients,
        messages=messages,
        offset_amount=offset_amount,
        offset_unit=offset_unit,
        offset_direction=offset_direction,
        custom_time_local=custom_time_local,
        timezone_name=timezone_name,
    )


def event_automations(db: Session, event_id: str, user_id: str) -> list[dict]:
    """Uma entrada por `Automation`, com suas mensagens em ordem e, para cada
    uma, o `Schedule` de cada destinatário (pra mostrar status de envio
    individual) — usado pelo modal de detalhe do evento e pela API REST."""
    event = db.get(Event, event_id)
    if event is None or event.user_id != user_id:
        return []
    automations = db.exec(
        select(Automation).where(col(Automation.event_id) == event_id).order_by(col(Automation.created_at))
    ).all()
    out: list[dict] = []
    for automation in automations:
        messages = db.exec(
            select(AutomationMessage)
            .where(col(AutomationMessage.automation_id) == automation.id)
            .order_by(col(AutomationMessage.position))
        ).all()
        links = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation.id)
        ).all()
        schedule_ids = [link.schedule_id for link in links]
        schedules = {
            s.id: s
            for s in (
                db.exec(select(Schedule).where(col(Schedule.id).in_(schedule_ids))).all() if schedule_ids else []
            )
        }
        recipients: dict[str, str] = {}
        for link in links:
            sch = schedules.get(link.schedule_id)
            if sch is not None:
                recipients.setdefault(link.recipient_chat_id, sch.recipient_input)
        message_rows = [
            {
                "message": message,
                "per_recipient": [
                    {"recipient": schedules[link.schedule_id].recipient_input, "schedule": schedules[link.schedule_id]}
                    for link in links
                    if link.message_id == message.id and link.schedule_id in schedules
                ],
            }
            for message in messages
        ]
        # Horário real da 1ª mensagem (position 0) — dado já persistido em
        # Schedule.first_run_local, não recalculado aqui, pra exibir o
        # instante exato do disparo (ex.: no modal de detalhe do evento).
        first_send_local = None
        if message_rows and message_rows[0]["per_recipient"]:
            first_send_local = message_rows[0]["per_recipient"][0]["schedule"].first_run_local
        out.append(
            {
                "automation": automation,
                "recipients": list(recipients.values()),
                "messages": message_rows,
                "enabled": any(s.enabled for s in schedules.values()),
                "first_send_local": first_send_local,
            }
        )
    return out


def migrate_legacy_automations(db: Session) -> None:
    """Converte, uma única vez, as automações do modelo antigo (incremento 2
    — `EventAutomation`, 1 `Schedule` por linha, 1 mensagem só) para o novo
    modelo multi-mensagem (`Automation`/`AutomationMessage`/`AutomationSchedule`).

    Idempotente (checa por `AutomationSchedule.schedule_id` já migrado) e
    roda dentro de UMA transação só — se cair no meio, nada commita e o
    próximo boot recomeça limpo, sem risco de criar uma `Automation` "órfã"
    duplicada na próxima tentativa. Chamada no `lifespan()` do `main.py`,
    antes de iniciar o scheduler e o sync de calendário. `Schedule`/`Dispatch`
    originais nunca são tocados — só ganham uma nova linha de ligação.
    """
    already_migrated = {
        row for row in db.exec(select(AutomationSchedule.schedule_id)).all()
    }
    legacy_rows = db.exec(select(EventAutomation)).all()
    migrated = 0
    for old in legacy_rows:
        if old.schedule_id in already_migrated:
            continue
        schedule = db.get(Schedule, old.schedule_id)
        if schedule is None:
            continue  # defensivo: nada apaga Schedule, não deveria acontecer

        automation = Automation(
            event_id=old.event_id,
            offset_amount=old.offset_amount,
            offset_unit=old.offset_unit,
            offset_direction=old.offset_direction,
            created_at=old.created_at,
            updated_at=old.updated_at,
        )
        db.add(automation)
        db.flush()
        message = AutomationMessage(automation_id=automation.id, position=0, text=schedule.text)
        db.add(message)
        db.flush()
        db.add(
            AutomationSchedule(
                automation_id=automation.id,
                message_id=message.id,
                schedule_id=schedule.id,
                recipient_chat_id=schedule.chat_id,
            )
        )
        migrated += 1
    if migrated:
        db.commit()
        logger.info("migradas %d automações do formato antigo (event_automations) pro novo formato", migrated)


def agenda(db: Session, user_id: str, *, days: int | None = None) -> list[Event]:
    """Eventos a partir de agora até `days` dias à frente (default: settings).
    Usado pela API REST (`/api/calendar/events`) — a UI web usa `month_grid`."""
    span = days if days is not None else settings.calendar_agenda_default_days
    start = utcnow() - timedelta(hours=6)  # margem pra ainda ver eventos de "hoje" já em andamento
    end = utcnow() + timedelta(days=span)
    return list(
        db.exec(
            select(Event)
            .where(col(Event.user_id) == user_id)
            .where(col(Event.start_utc) >= start)
            .where(col(Event.start_utc) <= end)
            .where(col(Event.status) == EventStatus.confirmed)
            .order_by(col(Event.start_utc))
        ).all()
    )


def month_grid(db: Session, user_id: str, year: int, month: int) -> list[list[dict]]:
    """Grade de 6 semanas (42 dias, domingo a sábado) pro mês pedido.

    A janela de busca tem uma margem de 24h além dos limites "exatos" da
    grade: um evento com timezone bem distante de `default_timezone` (ex.:
    Asia/Tokyo vs. America/Sao_Paulo) pode ter `start_utc` fora dos limites
    estritos mesmo pertencendo visualmente a uma célula da grade. Cada
    evento é distribuído na SUA PRÓPRIA timezone (não em `default_timezone`),
    igual o dia-a-dia já fazia — e o lookup é por dict, nunca por índice
    fixo, porque mesmo com a margem um evento ainda pode cair fora das 42
    células (é só ignorado nesse caso, não quebra a grade).
    """
    default_tz = settings.default_timezone
    first_of_month = date(year, month, 1)
    # date.weekday(): segunda=0..domingo=6; a grade começa no domingo (=0).
    days_since_sunday = (first_of_month.weekday() + 1) % 7
    grid_start = first_of_month - timedelta(days=days_since_sunday)
    grid_end = grid_start + timedelta(days=41)  # 42 dias = 6 semanas

    query_start = local_to_utc(datetime.combine(grid_start, dt_time.min), default_tz) - timedelta(hours=24)
    query_end = local_to_utc(datetime.combine(grid_end + timedelta(days=1), dt_time.min), default_tz) + timedelta(
        hours=24
    )

    events = db.exec(
        select(Event)
        .where(col(Event.user_id) == user_id)
        .where(col(Event.status) == EventStatus.confirmed)
        .where(col(Event.start_utc) >= query_start)
        .where(col(Event.start_utc) < query_end)
        .order_by(col(Event.start_utc))
    ).all()

    cells: dict[date, list[Event]] = {grid_start + timedelta(days=i): [] for i in range(42)}
    for event in events:
        tz = event.timezone or default_tz
        try:
            local_date = utc_to_local(event.start_utc, tz).date()
        except (ZoneInfoNotFoundError, ValueError):
            continue
        bucket = cells.get(local_date)
        if bucket is not None:
            bucket.append(event)

    today_local = utc_to_local(utcnow(), default_tz).date()
    weeks: list[list[dict]] = []
    for w in range(6):
        week = []
        for d in range(7):
            day = grid_start + timedelta(days=w * 7 + d)
            week.append(
                {
                    "date": day,
                    "in_month": day.month == month,
                    "is_today": day == today_local,
                    "events": cells[day],
                }
            )
        weeks.append(week)
    return weeks


def _validate_event_fields(title: str, description: str, start_local: datetime, end_local: datetime, tz_name: str) -> tuple[str, str]:
    title = (title or "").strip()
    if not title:
        raise ValidationError("O título do evento não pode ficar vazio.")
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"Timezone inválida: {tz_name!r}") from exc
    if end_local <= start_local:
        raise ValidationError("O horário final precisa ser depois do horário inicial.")
    return title, (description or "").strip()


async def _google_provider_and_tokens(db: Session, calendar: Calendar):
    connection = db.get(CalendarConnection, calendar.connection_id)
    if connection is None:
        raise ValidationError("A conexão Google deste calendário não foi encontrada.")
    provider = get_provider(connection.provider)
    tokens = await ensure_fresh_tokens(db, connection, provider)
    return provider, tokens


def _remote_calendar(calendar: Calendar) -> RemoteCalendar:
    return RemoteCalendar(external_id=calendar.external_id, name=calendar.name, time_zone=calendar.time_zone)


def _set_sync_status(db: Session, event_id: str, *, status: str, error: str | None) -> None:
    row = db.get(EventSyncStatus, event_id)
    if row is None:
        row = EventSyncStatus(event_id=event_id)
    row.status = status
    row.error = error
    row.updated_at = utcnow()
    db.add(row)
    db.commit()


def _delete_automations_for_event(db: Session, event_id: str) -> None:
    automation_ids = [a.id for a in db.exec(select(Automation).where(col(Automation.event_id) == event_id)).all()]
    if not automation_ids:
        return
    db.exec(sa_delete(AutomationSchedule).where(col(AutomationSchedule.automation_id).in_(automation_ids)))
    db.exec(sa_delete(AutomationMessage).where(col(AutomationMessage.automation_id).in_(automation_ids)))
    db.exec(sa_delete(Automation).where(col(Automation.id).in_(automation_ids)))
    db.commit()


async def create_internal_event(
    db: Session,
    *,
    user_id: str,
    title: str,
    description: str = "",
    start_local: datetime,
    end_local: datetime,
    timezone_name: str,
    target_calendar_id: str | None = None,
) -> Event:
    """`target_calendar_id` (opcional) é o id (interno, de `Calendar`) de um
    calendário Google habilitado — cria o evento localmente sempre (mesmo se
    o push pro Google falhar, o registro local nunca se perde), e só então
    tenta criar no Google. Se o push falhar, o evento fica sem vínculo
    (`external_id=None`) e o erro fica em `EventSyncStatus` pro usuário ver
    e tentar de novo depois."""
    title, description = _validate_event_fields(title, description, start_local, end_local, timezone_name)
    event = Event(
        user_id=user_id,
        source=EventSource.internal,
        title=title,
        description=description,
        start_utc=local_to_utc(start_local, timezone_name),
        end_utc=local_to_utc(end_local, timezone_name),
        timezone=timezone_name,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    if target_calendar_id:
        calendar = _owned_calendar(db, target_calendar_id, user_id)
        if calendar is None or not calendar.enabled:
            raise ValidationError("Calendário Google selecionado não está disponível.")
        try:
            provider, tokens = await _google_provider_and_tokens(db, calendar)
            external_id = await provider.create_event(
                tokens,
                _remote_calendar(calendar),
                title=title,
                description=description,
                start_utc=event.start_utc,
                end_utc=event.end_utc,
                timezone=timezone_name,
            )
        except CalendarProviderError as exc:
            logger.warning("falha ao criar evento %s no Google: %s", event.id, exc)
            _set_sync_status(db, event.id, status="error", error=str(exc))
        else:
            event.calendar_id = calendar.id
            event.external_id = external_id
            db.add(event)
            db.commit()
            db.refresh(event)
            _set_sync_status(db, event.id, status="synced", error=None)
    return event


async def update_internal_event(
    db: Session,
    event_id: str,
    *,
    user_id: str,
    title: str,
    description: str = "",
    start_local: datetime,
    end_local: datetime,
    timezone_name: str,
) -> Event:
    """Se o evento estiver vinculado a um calendário Google, o PATCH é
    tentado ANTES de qualquer alteração local ser commitada — se o Google
    falhar (ex.: conta ainda com escopo de leitura), nada muda localmente.
    Sem essa ordem, uma falha silenciosa deixaria o app com um horário local
    que o Google não tem, e o próximo pull-sync reverteria a edição sozinho
    (e reagendaria a automação de volta) sem o usuário perceber."""
    event = db.get(Event, event_id)
    if event is None or event.user_id != user_id:
        raise ValidationError("Evento não encontrado.")
    if event.source != EventSource.internal:
        raise ValidationError("Eventos sincronizados do Google não podem ser editados aqui — só a automação.")

    title, description = _validate_event_fields(title, description, start_local, end_local, timezone_name)
    new_start_utc = local_to_utc(start_local, timezone_name)
    new_end_utc = local_to_utc(end_local, timezone_name)
    time_changed = new_start_utc != event.start_utc

    if event.calendar_id and event.external_id:
        calendar = db.get(Calendar, event.calendar_id)
        if calendar is None:
            raise ValidationError("O calendário Google vinculado a este evento não foi encontrado.")
        try:
            provider, tokens = await _google_provider_and_tokens(db, calendar)
            await provider.update_event(
                tokens,
                _remote_calendar(calendar),
                event.external_id,
                title=title,
                description=description,
                start_utc=new_start_utc,
                end_utc=new_end_utc,
                timezone=timezone_name,
            )
        except CalendarProviderError as exc:
            _set_sync_status(db, event.id, status="error", error=str(exc))
            raise ValidationError(
                f"Não consegui atualizar no Google Agenda ({exc}). Nada foi alterado — se a conta ainda "
                "estiver com acesso só de leitura, reconecte-a em Configurações e tente de novo."
            ) from exc
        _set_sync_status(db, event.id, status="synced", error=None)

    event.title = title
    event.description = description
    event.start_utc = new_start_utc
    event.end_utc = new_end_utc
    event.timezone = timezone_name
    event.updated_at = utcnow()
    db.add(event)
    db.commit()
    db.refresh(event)

    if time_changed:
        reschedule_event_automations(db, event)
    return event


async def delete_internal_event(db: Session, event_id: str, *, user_id: str, also_delete_google: bool = False) -> bool:
    """`also_delete_google` só importa se o evento estiver vinculado — se o
    DELETE no Google falhar, o evento local NÃO é excluído (evita que ele
    reapareça como um evento "novo" vindo do Google no próximo pull-sync
    enquanto ainda existe lá). As automações são canceladas antes de
    qualquer chamada ao Google — isso é sempre local e seguro,
    independentemente do resultado do push."""
    event = db.get(Event, event_id)
    if event is None or event.user_id != user_id:
        return False
    if event.source != EventSource.internal:
        raise ValidationError("Eventos sincronizados do Google não podem ser excluídos aqui.")

    # Ordem obrigatória (PRAGMA foreign_keys=ON, sem Relationship() do ORM
    # pra ordenar sozinho): cancelar os schedules primeiro (preserva
    # Schedule/Dispatch como histórico), depois as linhas de ligação, só
    # então o evento.
    cancel_event_automations(db, event)
    _delete_automations_for_event(db, event_id)

    if event.calendar_id and event.external_id and also_delete_google:
        calendar = db.get(Calendar, event.calendar_id)
        if calendar is not None:
            try:
                provider, tokens = await _google_provider_and_tokens(db, calendar)
                await provider.delete_event(tokens, _remote_calendar(calendar), event.external_id)
            except CalendarProviderError as exc:
                raise ValidationError(
                    f"Não consegui excluir no Google Agenda ({exc}). O evento não foi excluído — tente de novo."
                ) from exc

    sync_row = db.get(EventSyncStatus, event_id)
    if sync_row is not None:
        db.delete(sync_row)
        db.commit()
    db.delete(event)
    db.commit()
    return True


async def list_contacts(waha, waha_session: str) -> list[dict]:
    """Contatos pra automação — reaproveita a lista de conversas do WhatsApp
    já existente (`chatsvc.list_chats`); não cria uma base de contatos nova."""
    chats = await list_chats(waha, waha_session)
    return [
        {"id": c["id"], "name": c["name"], "picture": c.get("picture"), "is_group": c["is_group"]} for c in chats
    ]
