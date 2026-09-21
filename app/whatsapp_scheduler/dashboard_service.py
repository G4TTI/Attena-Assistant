"""Agregações de dados reais para o Dashboard.

Só leitura — nenhuma regra de negócio nova aqui. Cada função reaproveita
queries/serviços já existentes (`calendar_service.month_grid` pro bucketing
por dia/timezone, `models.OPEN_STATUSES`, etc.) e só monta o resumo que a
página precisa. Nada fica hardcoded: se não houver dado, a função devolve
lista/None vazios e o template decide o estado vazio.

Toda função recebe `user_id` e filtra por ele — o Dashboard é sempre do
usuário autenticado, nunca um agregado de todo mundo.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlmodel import Session, col, select

from . import calendar_service, whatsapp_service
from .clock import utcnow
from .models import (
    Automation,
    CalendarConnection,
    Dispatch,
    DispatchStatus,
    Event,
    EventSource,
    EventStatus,
    OPEN_STATUSES,
    Schedule,
    ScheduleGroup,
)
from .recurrence import local_to_utc, utc_to_local


def today_local_date(tz_name: str) -> date:
    return utc_to_local(utcnow(), tz_name).date()


def _local_day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]:
    start = local_to_utc(datetime.combine(day, time.min), tz_name)
    end = local_to_utc(datetime.combine(day + timedelta(days=1), time.min), tz_name)
    return start, end


# --------------------------------------------------------------------------- #
# Eventos
# --------------------------------------------------------------------------- #
def today_events(db: Session, user_id: str, tz_name: str, *, today: date | None = None) -> list[Event]:
    """Eventos de hoje, em qualquer calendário — reaproveita o mesmo
    bucketing por dia/timezone que a grade do Calendário já usa, então um
    evento cai no mesmo dia aqui e lá."""
    today = today or today_local_date(tz_name)
    weeks = calendar_service.month_grid(db, user_id, today.year, today.month, tz_name)
    for week in weeks:
        for day in week:
            if day["date"] == today:
                return sorted(day["events"], key=lambda e: e.start_utc)
    return []


def upcoming_today_count(events: list[Event]) -> int:
    now = utcnow()
    return sum(1 for e in events if e.start_utc > now)


def upcoming_events(db: Session, user_id: str, *, limit: int = 5) -> list[Event]:
    """Próximos eventos (qualquer dia), em ordem cronológica."""
    now = utcnow()
    return list(
        db.exec(
            select(Event)
            .where(col(Event.user_id) == user_id)
            .where(col(Event.status) == EventStatus.confirmed)
            .where(col(Event.start_utc) > now)
            .order_by(col(Event.start_utc))
            .limit(limit)
        ).all()
    )


# --------------------------------------------------------------------------- #
# Mensagens (Dispatch) — Dispatch não tem user_id próprio; sempre via join
# com Schedule (dono real do disparo).
# --------------------------------------------------------------------------- #
def scheduled_dispatches(db: Session, user_id: str) -> list[Dispatch]:
    return list(
        db.exec(
            select(Dispatch)
            .join(Schedule, col(Dispatch.schedule_id) == col(Schedule.id))
            .where(col(Schedule.user_id) == user_id)
            .where(col(Dispatch.status).in_(list(OPEN_STATUSES)))
            .order_by(col(Dispatch.scheduled_at_utc))
        ).all()
    )


def sent_count_on(db: Session, user_id: str, day: date, tz_name: str) -> int:
    start_utc, end_utc = _local_day_bounds_utc(day, tz_name)
    return len(
        db.exec(
            select(Dispatch)
            .join(Schedule, col(Dispatch.schedule_id) == col(Schedule.id))
            .where(col(Schedule.user_id) == user_id)
            .where(col(Dispatch.status) == DispatchStatus.sent)
            .where(col(Dispatch.sent_at_utc) >= start_utc)
            .where(col(Dispatch.sent_at_utc) < end_utc)
        ).all()
    )


def failed_count_on(db: Session, user_id: str, day: date, tz_name: str) -> int:
    start_utc, end_utc = _local_day_bounds_utc(day, tz_name)
    return len(
        db.exec(
            select(Dispatch)
            .join(Schedule, col(Dispatch.schedule_id) == col(Schedule.id))
            .where(col(Schedule.user_id) == user_id)
            .where(col(Dispatch.status) == DispatchStatus.failed)
            .where(col(Dispatch.scheduled_at_utc) >= start_utc)
            .where(col(Dispatch.scheduled_at_utc) < end_utc)
        ).all()
    )


def _group_info(db: Session, schedule: Schedule) -> tuple[int, str]:
    """(quantas mensagens tem o agendamento a que este `Schedule` pertence,
    nome do destinatário) — 1 mensagem e o próprio `recipient_input` se o
    schedule ainda não tem grupo."""
    if schedule.group_id is None:
        return 1, schedule.recipient_input
    group = db.get(ScheduleGroup, schedule.group_id)
    count = db.exec(select(func.count()).select_from(Schedule).where(col(Schedule.group_id) == schedule.group_id)).one()
    name = (group.recipient_name if group and group.recipient_name else schedule.recipient_input)
    return int(count or 1), name


def upcoming_dispatch_rows(db: Session, user_id: str, *, limit: int = 5, tz_name: str | None = None) -> list[dict]:
    """`tz_name`: fuso do USUÁRIO — o horário mostrado é sempre nele (o mesmo
    das outras telas), não no fuso guardado em cada schedule."""
    wa_labels = whatsapp_service.labels_by_session_name(db, user_id)
    rows: list[dict] = []
    for dispatch in scheduled_dispatches(db, user_id)[:limit]:
        schedule = db.get(Schedule, dispatch.schedule_id)
        if schedule is None:
            continue
        message_count, recipient = _group_info(db, schedule)
        rows.append(
            {
                "dispatch": dispatch,
                "schedule": schedule,
                "recipient": recipient,
                "send_local": utc_to_local(dispatch.scheduled_at_utc, tz_name or schedule.timezone),
                "message_count": message_count,
                "whatsapp_label": wa_labels.get(schedule.session, schedule.session),
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Atividade recente — merge por timestamp de fontes já existentes.
# --------------------------------------------------------------------------- #
def recent_activity(db: Session, user_id: str, *, limit: int = 6) -> list[dict]:
    items: list[dict] = []

    for dispatch in db.exec(
        select(Dispatch)
        .join(Schedule, col(Dispatch.schedule_id) == col(Schedule.id))
        .where(col(Schedule.user_id) == user_id)
        .where(col(Dispatch.status) == DispatchStatus.sent)
        .order_by(col(Dispatch.sent_at_utc).desc())
        .limit(limit)
    ).all():
        if dispatch.sent_at_utc is None:
            continue
        schedule = db.get(Schedule, dispatch.schedule_id)
        if schedule is None:
            continue
        items.append(
            {"kind": "sent", "at": dispatch.sent_at_utc, "label": f"Mensagem enviada para {schedule.recipient_input}"}
        )

    for dispatch in db.exec(
        select(Dispatch)
        .join(Schedule, col(Dispatch.schedule_id) == col(Schedule.id))
        .where(col(Schedule.user_id) == user_id)
        .where(col(Dispatch.status) == DispatchStatus.failed)
        .order_by(col(Dispatch.updated_at).desc())
        .limit(limit)
    ).all():
        schedule = db.get(Schedule, dispatch.schedule_id)
        if schedule is None:
            continue
        items.append(
            {
                "kind": "failed",
                "at": dispatch.updated_at,
                "label": f"Falha ao enviar mensagem para {schedule.recipient_input}",
            }
        )

    for event in db.exec(
        select(Event)
        .where(col(Event.user_id) == user_id)
        .where(col(Event.source) == EventSource.internal)
        .order_by(col(Event.created_at).desc())
        .limit(limit)
    ).all():
        items.append({"kind": "event", "at": event.created_at, "label": f"Evento criado — {event.title}"})

    for automation in db.exec(
        select(Automation)
        .join(Event, col(Automation.event_id) == col(Event.id))
        .where(col(Event.user_id) == user_id)
        .order_by(col(Automation.created_at).desc())
        .limit(limit)
    ).all():
        event = db.get(Event, automation.event_id)
        items.append(
            {
                "kind": "automation",
                "at": automation.created_at,
                "label": f"Automação criada — {event.title if event else 'evento'}",
            }
        )

    items.sort(key=lambda item: item["at"], reverse=True)
    return items[:limit]


def has_any_activity(db: Session, user_id: str) -> bool:
    """Já existe QUALQUER schedule, evento ou automação deste usuário, alguma
    vez (não só hoje/futuro)? Usado só pra decidir se o Dashboard mostra o
    resumo operacional ou o bloco de boas-vindas de quem acabou de criar a
    conta (v1.3, item 26) — não é uma condição de negócio em lugar nenhum."""
    has_schedule = db.exec(select(Schedule.id).where(col(Schedule.user_id) == user_id).limit(1)).first()
    if has_schedule is not None:
        return True
    has_event = db.exec(select(Event.id).where(col(Event.user_id) == user_id).limit(1)).first()
    if has_event is not None:
        return True
    has_automation = db.exec(
        select(Automation.id)
        .join(Event, col(Automation.event_id) == col(Event.id))
        .where(col(Event.user_id) == user_id)
        .limit(1)
    ).first()
    return has_automation is not None


def relative_label(at_utc: datetime) -> str:
    seconds = max(0, int((utcnow() - at_utc).total_seconds()))
    if seconds < 60:
        return "agora mesmo"
    minutes = seconds // 60
    if minutes < 60:
        return f"há {minutes} minuto{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    if hours < 24:
        return f"há {hours} hora{'s' if hours != 1 else ''}"
    days = hours // 24
    return f"há {days} dia{'s' if days != 1 else ''}"


# --------------------------------------------------------------------------- #
# Google Agenda — reaproveita calendar_service (mesmos campos que Configurações usa).
# --------------------------------------------------------------------------- #
def primary_calendar_connection(db: Session, user_id: str) -> CalendarConnection | None:
    connections = calendar_service.list_connections(db, user_id)
    return connections[0] if connections else None
