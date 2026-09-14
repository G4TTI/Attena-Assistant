from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, col, select

from whatsapp_scheduler import calendar_service, calendar_sync
from whatsapp_scheduler.calendar_providers.base import OAuthTokens, RemoteEvent
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.models import (
    AutomationMessage,
    AutomationSchedule,
    Calendar,
    CalendarConnection,
    CalendarConnectionStatus,
    Dispatch,
    DispatchStatus,
    Event,
    EventStatus,
    Schedule,
)

TZ = "America/Sao_Paulo"
FROZEN = datetime(2026, 6, 1, 12, 0, 0)


@pytest.fixture
def frozen_clock(monkeypatch):
    holder = {"now": FROZEN}
    monkeypatch.setattr("whatsapp_scheduler.clock.utcnow", lambda: holder["now"])
    return holder


def make_connection(db: Session) -> CalendarConnection:
    from whatsapp_scheduler import crypto

    conn = CalendarConnection(
        provider="google",
        account_identifier="user@example.com",
        access_token_enc=crypto.encrypt("access"),
        refresh_token_enc=crypto.encrypt("refresh"),
        token_expires_at=FROZEN + timedelta(hours=1),
        status=CalendarConnectionStatus.active,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def make_calendar(db: Session, conn: CalendarConnection, *, external_id="primary", enabled=True) -> Calendar:
    cal = Calendar(connection_id=conn.id, external_id=external_id, name="Meu calendário", time_zone=TZ, enabled=enabled)
    db.add(cal)
    db.commit()
    db.refresh(cal)
    return cal


def remote_event(external_id: str, start: datetime, *, cancelled=False, title="Consulta") -> RemoteEvent:
    return RemoteEvent(
        external_id=external_id,
        title=title,
        description="",
        start_utc=None if cancelled else start,
        end_utc=None if cancelled else start + timedelta(hours=1),
        timezone=None if cancelled else TZ,
        all_day=False,
        cancelled=cancelled,
    )


def tokens() -> OAuthTokens:
    return OAuthTokens(access_token="a", refresh_token="r", expires_at=FROZEN + timedelta(hours=1))


def dispatches_of(schedule_id: str) -> list[Dispatch]:
    with Session(get_engine()) as db:
        return list(
            db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule_id).order_by(col(Dispatch.scheduled_at_utc))).all()
        )


def first_schedule_of(automation_id: str) -> Schedule:
    with Session(get_engine()) as db:
        (link,) = db.exec(
            select(AutomationSchedule).where(col(AutomationSchedule.automation_id) == automation_id)
        ).all()
        return db.get(Schedule, link.schedule_id)


async def test_first_sync_imports_events_using_time_bounds(db, fake_google, frozen_clock):
    conn = make_connection(db)
    cal = make_calendar(db, conn)
    start = FROZEN + timedelta(hours=2)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start)]

    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    events = db.exec(select(Event).where(col(Event.calendar_id) == cal.id)).all()
    assert len(events) == 1
    assert events[0].external_id == "ext-1"
    assert events[0].title == "Consulta"
    assert events[0].start_utc == start

    call = fake_google.list_events_calls[-1]
    assert call["sync_token"] is None
    assert call["time_min"] is not None and call["time_max"] is not None

    db.refresh(cal)
    assert cal.sync_token == "next-token"


async def test_incremental_sync_uses_stored_sync_token(db, fake_google, frozen_clock):
    conn = make_connection(db)
    cal = make_calendar(db, conn)
    cal.sync_token = "stored-token"
    db.add(cal)
    db.commit()
    fake_google.events_by_calendar["primary"] = []

    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    call = fake_google.list_events_calls[-1]
    assert call["sync_token"] == "stored-token"
    assert call["time_min"] is None and call["time_max"] is None


async def test_event_time_change_reschedules_same_dispatch_without_duplicating(db, fake_google, frozen_clock):
    conn = make_connection(db)
    cal = make_calendar(db, conn)
    start1 = FROZEN + timedelta(hours=2)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start1)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    event = db.exec(select(Event).where(col(Event.calendar_id) == cal.id)).first()
    automation = calendar_service.create_event_automation(
        db,
        event_id=event.id,
        recipients=["+55 11 99999-8888"],
        messages=["Lembrete"],
        offset_amount=1,
        offset_unit="hours",
        offset_direction="before",
    )
    schedule = first_schedule_of(automation.id)
    (dispatch,) = dispatches_of(schedule.id)
    original_id = dispatch.id
    assert dispatch.scheduled_at_utc == start1 - timedelta(hours=1)

    # Google move o evento 1h pra frente.
    start2 = start1 + timedelta(hours=1)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start2)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    ds = dispatches_of(schedule.id)
    assert len(ds) == 1  # sem linha duplicada
    assert ds[0].id == original_id
    assert ds[0].scheduled_at_utc == start2 - timedelta(hours=1)


async def test_time_change_with_no_pending_dispatch_is_noop(db, fake_google, frozen_clock):
    conn = make_connection(db)
    cal = make_calendar(db, conn)
    start1 = FROZEN + timedelta(hours=2)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start1)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    event = db.exec(select(Event).where(col(Event.calendar_id) == cal.id)).first()
    automation = calendar_service.create_event_automation(
        db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
        offset_amount=1, offset_unit="hours", offset_direction="before",
    )
    schedule = first_schedule_of(automation.id)
    (dispatch,) = dispatches_of(schedule.id)
    # Simula que já foi enviada.
    with Session(get_engine()) as s:
        d = s.get(Dispatch, dispatch.id)
        d.status = DispatchStatus.sent
        s.add(d)
        s.commit()

    start2 = start1 + timedelta(hours=3)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start2)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    ds = dispatches_of(schedule.id)
    assert len(ds) == 1
    assert ds[0].status == DispatchStatus.sent
    assert ds[0].scheduled_at_utc == dispatch.scheduled_at_utc  # não mexeu


async def test_dispatch_already_processing_is_not_overwritten_by_reschedule(db, fake_google, frozen_clock):
    """Simula a corrida: dispatch_due() já reivindicou a dispatch (status=processing)
    bem no momento em que a sincronização tenta reagendar — o UPDATE guardado
    não deve sobrescrever."""
    conn = make_connection(db)
    cal = make_calendar(db, conn)
    start1 = FROZEN + timedelta(hours=2)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start1)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    event = db.exec(select(Event).where(col(Event.calendar_id) == cal.id)).first()
    automation = calendar_service.create_event_automation(
        db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
        offset_amount=1, offset_unit="hours", offset_direction="before",
    )
    schedule = first_schedule_of(automation.id)
    (dispatch,) = dispatches_of(schedule.id)
    original_scheduled_at = dispatch.scheduled_at_utc
    with Session(get_engine()) as s:
        d = s.get(Dispatch, dispatch.id)
        d.status = DispatchStatus.processing
        s.add(d)
        s.commit()

    start2 = start1 + timedelta(hours=1)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start2)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    ds = dispatches_of(schedule.id)
    assert len(ds) == 1
    assert ds[0].status == DispatchStatus.processing
    assert ds[0].scheduled_at_utc == original_scheduled_at  # UPDATE guardado não afetou


async def test_cancelled_event_cancels_open_dispatch_and_keeps_event_row(db, fake_google, frozen_clock):
    conn = make_connection(db)
    cal = make_calendar(db, conn)
    start1 = FROZEN + timedelta(hours=2)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start1)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    event = db.exec(select(Event).where(col(Event.calendar_id) == cal.id)).first()
    automation = calendar_service.create_event_automation(
        db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
        offset_amount=1, offset_unit="hours", offset_direction="before",
    )
    schedule = first_schedule_of(automation.id)

    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start1, cancelled=True)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    db.refresh(event)
    assert event.status == EventStatus.cancelled  # linha preservada, não apagada

    with Session(get_engine()) as s:
        sched = s.get(Schedule, schedule.id)
        assert sched.enabled is False
    (dispatch,) = dispatches_of(schedule.id)
    assert dispatch.status == DispatchStatus.canceled


async def test_sent_dispatch_untouched_after_event_cancelled(db, fake_google, frozen_clock):
    conn = make_connection(db)
    cal = make_calendar(db, conn)
    start1 = FROZEN + timedelta(hours=2)
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start1)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)
    event = db.exec(select(Event).where(col(Event.calendar_id) == cal.id)).first()
    automation = calendar_service.create_event_automation(
        db, event_id=event.id, recipients=["+55 11 99999-8888"], messages=["x"],
        offset_amount=1, offset_unit="hours", offset_direction="before",
    )
    schedule = first_schedule_of(automation.id)
    (dispatch,) = dispatches_of(schedule.id)
    with Session(get_engine()) as s:
        d = s.get(Dispatch, dispatch.id)
        d.status = DispatchStatus.sent
        s.add(d)
        s.commit()

    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", start1, cancelled=True)]
    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    (d,) = dispatches_of(schedule.id)
    assert d.status == DispatchStatus.sent  # histórico intocado


async def test_expired_sync_token_triggers_full_resync(db, fake_google, frozen_clock):
    conn = make_connection(db)
    cal = make_calendar(db, conn)
    cal.sync_token = "stale"
    db.add(cal)
    db.commit()

    fake_google.invalidate_sync_token_for.add("primary")
    fake_google.events_by_calendar["primary"] = [remote_event("ext-1", FROZEN + timedelta(hours=1))]
    fake_google.next_sync_token_by_calendar["primary"] = "fresh-token"

    await calendar_sync.sync_calendar(db, fake_google, tokens(), cal)

    # duas chamadas nesta sincronização: a incremental que expirou + o resync completo
    assert len(fake_google.list_events_calls) == 2
    assert fake_google.list_events_calls[0]["sync_token"] == "stale"
    assert fake_google.list_events_calls[1]["sync_token"] is None

    db.refresh(cal)
    assert cal.sync_token == "fresh-token"
    events = db.exec(select(Event).where(col(Event.calendar_id) == cal.id)).all()
    assert len(events) == 1


async def test_disabled_calendar_is_skipped_by_sync_connection(db, fake_google, frozen_clock):
    conn = make_connection(db)
    make_calendar(db, conn, external_id="off", enabled=False)
    fake_google.events_by_calendar["off"] = [remote_event("should-not-import", FROZEN + timedelta(hours=1))]

    await calendar_sync.sync_connection(db, conn, providers={"google": fake_google})

    assert fake_google.list_events_calls == []
    assert db.exec(select(Event)).all() == []


async def test_sync_connection_syncs_enabled_calendars_only(db, fake_google, frozen_clock):
    conn = make_connection(db)
    make_calendar(db, conn, external_id="on", enabled=True)
    make_calendar(db, conn, external_id="off", enabled=False)
    fake_google.events_by_calendar["on"] = [remote_event("e1", FROZEN + timedelta(hours=1))]
    fake_google.events_by_calendar["off"] = [remote_event("e2", FROZEN + timedelta(hours=1))]

    await calendar_sync.sync_connection(db, conn, providers={"google": fake_google})

    synced_calendars = {c["calendar"] for c in fake_google.list_events_calls}
    assert synced_calendars == {"on"}
    db.refresh(conn)
    assert conn.status == CalendarConnectionStatus.active
    assert conn.last_sync_at is not None
