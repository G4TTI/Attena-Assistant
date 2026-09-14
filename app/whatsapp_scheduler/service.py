"""Regras de negócio compartilhadas entre a API REST e a UI web."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session, col, select

from .clock import utcnow
from .config import settings
from .models import OPEN_STATUSES, Dispatch, DispatchStatus, Schedule, ScheduleDependency
from .recipients import normalize_recipient
from .recurrence import RecurrenceError, normalize_recurrence
from .scheduler import materialize_one


class ValidationError(ValueError):
    """Dado de entrada inválido (vira HTTP 422)."""


def _resolve_local(send_at: datetime, tz_name: str) -> datetime:
    if send_at.tzinfo is not None:
        return send_at.astimezone(ZoneInfo(tz_name)).replace(tzinfo=None)
    return send_at.replace(tzinfo=None)


def create_schedule(
    db: Session,
    *,
    recipient: str,
    text: str,
    send_at: datetime,
    timezone: str | None = None,
    recurrence: str | None = None,
    session: str | None = None,
    max_attempts: int = 3,
    depends_on_schedule_id: str | None = None,
) -> Schedule:
    text = (text or "").strip()
    if not text:
        raise ValidationError("A mensagem não pode ficar vazia.")

    tz_name = (timezone or settings.default_timezone).strip()
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"Timezone inválida: {tz_name!r}") from exc

    try:
        chat_id = normalize_recipient(recipient)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    cron: str | None = None
    if recurrence and recurrence.strip():
        try:
            cron = normalize_recurrence(recurrence)
        except RecurrenceError as exc:
            raise ValidationError(str(exc)) from exc

    if max_attempts < 1 or max_attempts > 10:
        raise ValidationError("max_attempts deve estar entre 1 e 10.")

    schedule = Schedule(
        session=(session or settings.waha_session).strip() or settings.waha_session,
        recipient_input=recipient.strip(),
        chat_id=chat_id,
        text=text,
        timezone=tz_name,
        first_run_local=_resolve_local(send_at, tz_name),
        recurrence=cron,
        max_attempts=max_attempts,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    if depends_on_schedule_id is not None:
        db.add(ScheduleDependency(schedule_id=schedule.id, depends_on_schedule_id=depends_on_schedule_id))
        db.commit()

    # Cria já a primeira dispatch para aparecer na lista imediatamente —
    # se houver dependência ainda não resolvida, materialize_one() não faz
    # nada este tick (ver scheduler._dependency_gate) e tenta de novo depois.
    materialize_one(db, schedule)
    return schedule


def cancel_schedule(db: Session, schedule_id: str) -> bool:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None or not schedule.enabled:
        return False
    schedule.enabled = False
    schedule.updated_at = utcnow()
    db.add(schedule)

    open_dispatches = db.exec(
        select(Dispatch)
        .where(col(Dispatch.schedule_id) == schedule_id)
        .where(col(Dispatch.status).in_(list(OPEN_STATUSES)))
    ).all()
    for dispatch in open_dispatches:
        dispatch.status = DispatchStatus.canceled
        dispatch.last_error = "Agendamento cancelado."
        dispatch.updated_at = utcnow()
        db.add(dispatch)

    db.commit()
    return True


def run_now(db: Session, schedule_id: str) -> Dispatch | None:
    """Antecipa o envio para agora (para testar ponta a ponta).

    Se já existe uma dispatch pendente, apenas adianta o horário dela; senão,
    cria uma nova.
    """
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        return None

    pending = db.exec(
        select(Dispatch)
        .where(col(Dispatch.schedule_id) == schedule_id)
        .where(col(Dispatch.status) == DispatchStatus.pending)
        .order_by(col(Dispatch.scheduled_at_utc))
    ).first()
    if pending is not None:
        pending.scheduled_at_utc = utcnow()
        pending.updated_at = utcnow()
        db.add(pending)
        db.commit()
        db.refresh(pending)
        return pending

    dispatch = Dispatch(
        schedule_id=schedule_id,
        scheduled_at_utc=utcnow(),
        status=DispatchStatus.pending,
    )
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)
    return dispatch
