"""API REST de agendamentos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from ..db import get_session
from ..models import Dispatch, Schedule
from ..schemas import DispatchRead, ScheduleCreate, ScheduleRead
from ..service import ValidationError, cancel_schedule, create_schedule, run_now

router = APIRouter(prefix="/api", tags=["schedules"])


def _load(db: Session, schedule_id: str) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return schedule


def _dispatches(db: Session, schedule_id: str) -> list[Dispatch]:
    return list(
        db.exec(
            select(Dispatch)
            .where(col(Dispatch.schedule_id) == schedule_id)
            .order_by(col(Dispatch.scheduled_at_utc).desc())
        ).all()
    )


@router.post("/schedules", response_model=ScheduleRead, status_code=201)
def create(payload: ScheduleCreate, db: Session = Depends(get_session)) -> ScheduleRead:
    try:
        schedule = create_schedule(
            db,
            recipient=payload.recipient,
            text=payload.text,
            send_at=payload.send_at,
            timezone=payload.timezone,
            recurrence=payload.recurrence,
            session=payload.session,
            max_attempts=payload.max_attempts,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ScheduleRead.of(schedule, _dispatches(db, schedule.id))


@router.get("/schedules", response_model=list[ScheduleRead])
def list_schedules(
    db: Session = Depends(get_session),
    enabled: bool | None = Query(None),
) -> list[ScheduleRead]:
    stmt = select(Schedule).order_by(col(Schedule.created_at).desc())
    if enabled is not None:
        stmt = stmt.where(col(Schedule.enabled).is_(enabled))
    schedules = db.exec(stmt).all()
    return [ScheduleRead.of(s, _dispatches(db, s.id)) for s in schedules]


@router.get("/schedules/{schedule_id}", response_model=ScheduleRead)
def get_schedule(schedule_id: str, db: Session = Depends(get_session)) -> ScheduleRead:
    schedule = _load(db, schedule_id)
    return ScheduleRead.of(schedule, _dispatches(db, schedule_id))


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_session)) -> dict:
    if not cancel_schedule(db, schedule_id):
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return {"status": "canceled", "id": schedule_id}


@router.post("/schedules/{schedule_id}/run-now", response_model=DispatchRead, status_code=202)
def trigger_now(schedule_id: str, db: Session = Depends(get_session)) -> DispatchRead:
    dispatch = run_now(db, schedule_id)
    if dispatch is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return DispatchRead.of(dispatch)
