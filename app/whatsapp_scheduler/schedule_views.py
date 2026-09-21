"""Modelo de LEITURA dos agendamentos — o que as telas mostram.

Só lê. Junta `ScheduleGroup` + `Schedule` + `Dispatch` e devolve, para cada
mensagem, o status e o HORÁRIO REAL de disparo, já no fuso do usuário. É a
fonte única das telas Agendamentos, Conversas e Dashboard: o mesmo status e o
mesmo horário aparecem em todas.

Estados de uma mensagem (`MessageView.status`):
  scheduled  aguardando o horário            🕐
  sending    sendo enviada agora             ⏳
  sent       confirmada pelo WhatsApp        ✓
  failed     esgotou as tentativas           ⚠️
  skipped    atrasada demais (ignorada)      ⚠️
  canceled   cancelada pelo usuário          ○

O status de um agendamento inteiro (`GroupView.status`) é derivado desses,
nunca guardado — por isso nunca discorda do que de fato foi enviado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlmodel import Session, col, select

from . import timing, whatsapp_service
from .clock import utcnow
from .models import (
    OPEN_STATUSES,
    CachedMessage,
    Dispatch,
    DispatchStatus,
    Schedule,
    ScheduleGroup,
    ScheduleSource,
)
from .service import backfill_groups

STATUS_LABELS = {
    "scheduled": "Agendado",
    "sending": "Enviando",
    "sent": "Enviado",
    "failed": "Falhou",
    "skipped": "Ignorado",
    "canceled": "Cancelado",
    "partial": "Parcial",
}
# Rótulo de cada estado de uma MENSAGEM (feminino — "mensagem agendada/enviada…").
MESSAGE_LABELS = {
    "scheduled": "Agendada",
    "sending": "Enviando",
    "sent": "Enviada",
    "failed": "Falhou",
    "skipped": "Ignorada",
    "canceled": "Cancelada",
}
# Ícone (texto) de cada estado de MENSAGEM — o template troca por SVG do projeto.
STATUS_ICONS = {"scheduled": "🕐", "sending": "⏳", "sent": "✓", "failed": "⚠️", "skipped": "⚠️", "canceled": "○"}

# Quanto tempo mensagens já encerradas continuam aparecendo dentro da conversa.
_CONVERSATION_HISTORY_WINDOW = timedelta(days=3)
_LIST_RECENT_FINISHED = 50


@dataclass
class MessageView:
    schedule: Schedule
    status: str
    when_utc: datetime  # horário real do disparo (ou do envio, se já saiu)
    when_local: datetime  # o mesmo, no fuso do usuário
    dispatch: Dispatch | None = None

    @property
    def position(self) -> int:
        return self.schedule.position

    @property
    def text(self) -> str:
        return self.schedule.text

    @property
    def error(self) -> str | None:
        return self.dispatch.last_error if self.dispatch is not None else None

    @property
    def attempts(self) -> int:
        return self.dispatch.attempts if self.dispatch is not None else 0

    @property
    def label(self) -> str:
        return MESSAGE_LABELS.get(self.status, self.status)

    @property
    def icon(self) -> str:
        return STATUS_ICONS.get(self.status, "")

    @property
    def can_cancel(self) -> bool:
        return self.status == "scheduled" and self.schedule.enabled


@dataclass
class GroupView:
    group: ScheduleGroup
    messages: list[MessageView]
    status: str
    when_utc: datetime
    when_local: datetime
    whatsapp_label: str
    editable: bool
    recurrence: str | None = None
    tz_name: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.group.id

    @property
    def recipient(self) -> str:
        """Nome do contato; sem nome, o número formatado ("5511999998888@c.us" -> "+5511999998888")."""
        if self.group.recipient_name:
            return self.group.recipient_name
        raw = self.group.recipient_input
        head = raw.split("@", 1)[0]
        return f"+{head}" if raw.endswith("@c.us") and head.isdigit() else raw

    @property
    def label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def pill(self) -> str:
        """Classe CSS de `.pill` (já existentes em base.html)."""
        return {"scheduled": "pending", "sending": "processing", "partial": "skipped", "skipped": "skipped"}.get(
            self.status, self.status
        )

    @property
    def is_open(self) -> bool:
        return self.status in ("scheduled", "sending")

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def is_recurring(self) -> bool:
        return bool(self.recurrence)

    @property
    def can_cancel(self) -> bool:
        return self.is_open


# --------------------------------------------------------------------------- #
# Derivação de status
# --------------------------------------------------------------------------- #
def message_status(schedule: Schedule, dispatches: list[Dispatch]) -> tuple[str, Dispatch | None]:
    """(status, dispatch que o representa). Uma dispatch aberta (pending/
    processing) sempre manda — é o que vai acontecer; senão vale a última."""
    open_ones = [d for d in dispatches if d.status in OPEN_STATUSES]
    if open_ones:
        current = min(open_ones, key=lambda d: d.scheduled_at_utc)
        return ("sending" if current.status == DispatchStatus.processing else "scheduled"), current
    if not dispatches:
        # Sem dispatch ainda: mensagem encadeada esperando a anterior (ou recém-criada).
        return ("scheduled" if schedule.enabled else "canceled"), None
    last = max(dispatches, key=lambda d: d.scheduled_at_utc)
    return {
        DispatchStatus.sent: "sent",
        DispatchStatus.failed: "failed",
        DispatchStatus.skipped: "skipped",
        DispatchStatus.canceled: "canceled",
    }.get(last.status, "scheduled"), last


def group_status(message_statuses: list[str]) -> str:
    """Status do agendamento inteiro a partir das mensagens dele."""
    sts = set(message_statuses)
    if not sts:
        return "canceled"
    if sts & {"scheduled", "sending"}:
        return "sending" if ("sending" in sts or "sent" in sts) else "scheduled"
    if sts == {"sent"}:
        return "sent"
    if sts == {"canceled"}:
        return "canceled"
    if "sent" in sts:
        return "partial"  # parte saiu e o resto falhou/foi cancelado
    return "failed" if sts & {"failed", "skipped"} else "canceled"


def _message_view(schedule: Schedule, dispatches: list[Dispatch], tz_name: str) -> MessageView:
    status, dispatch = message_status(schedule, dispatches)
    if dispatch is None:
        when_utc = timing.to_utc(schedule.first_run_local, schedule.timezone)
    elif status == "sent" and dispatch.sent_at_utc is not None:
        when_utc = dispatch.sent_at_utc
    else:
        when_utc = dispatch.scheduled_at_utc
    return MessageView(
        schedule=schedule, status=status, when_utc=when_utc, when_local=timing.to_local(when_utc, tz_name), dispatch=dispatch
    )


def _is_editable(group: ScheduleGroup, schedules: list[Schedule], by_schedule: dict[str, list[Dispatch]]) -> bool:
    """Mesma regra de `service.update_sequence`: só antes de qualquer envio."""
    if group.source == ScheduleSource.calendar or not schedules:
        return False
    if not all(s.enabled for s in schedules):
        return False
    return all(
        d.status == DispatchStatus.pending and d.attempts == 0 for s in schedules for d in by_schedule.get(s.id, [])
    )


# --------------------------------------------------------------------------- #
# Carga em lote (3 consultas, sem N+1)
# --------------------------------------------------------------------------- #
def _chunks(items: list[str], size: int = 500):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _load_schedules(db: Session, group_ids: list[str]) -> dict[str, list[Schedule]]:
    by_group: dict[str, list[Schedule]] = {}
    for chunk in _chunks(group_ids):
        for s in db.exec(
            select(Schedule).where(col(Schedule.group_id).in_(chunk)).order_by(col(Schedule.position))
        ).all():
            by_group.setdefault(s.group_id, []).append(s)  # type: ignore[arg-type]
    return by_group


def _load_dispatches(db: Session, schedule_ids: list[str]) -> dict[str, list[Dispatch]]:
    by_schedule: dict[str, list[Dispatch]] = {}
    for chunk in _chunks(schedule_ids):
        for d in db.exec(select(Dispatch).where(col(Dispatch.schedule_id).in_(chunk))).all():
            by_schedule.setdefault(d.schedule_id, []).append(d)
    return by_schedule


def _build_group_views(db: Session, groups: list[ScheduleGroup], user_id: str, tz_name: str) -> list[GroupView]:
    if not groups:
        return []
    schedules_by_group = _load_schedules(db, [g.id for g in groups])
    all_schedule_ids = [s.id for ss in schedules_by_group.values() for s in ss]
    dispatches = _load_dispatches(db, all_schedule_ids)
    labels = whatsapp_service.labels_by_session_name(db, user_id)

    views: list[GroupView] = []
    for group in groups:
        schedules = schedules_by_group.get(group.id, [])
        messages = [_message_view(s, dispatches.get(s.id, []), tz_name) for s in schedules]
        status = group_status([m.status for m in messages])
        open_messages = [m for m in messages if m.status in ("scheduled", "sending")]
        representative = min(open_messages, key=lambda m: m.when_utc) if open_messages else (messages[0] if messages else None)
        when_utc = representative.when_utc if representative else timing.to_utc(group.start_local, group.timezone)
        views.append(
            GroupView(
                group=group,
                messages=messages,
                status=status,
                when_utc=when_utc,
                when_local=timing.to_local(when_utc, tz_name),
                whatsapp_label=labels.get(group.session, group.session),
                editable=_is_editable(group, schedules, dispatches),
                recurrence=schedules[0].recurrence if schedules else None,
                tz_name=tz_name,
            )
        )
    return views


# --------------------------------------------------------------------------- #
# Consultas usadas pelas telas
# --------------------------------------------------------------------------- #
def list_group_views(db: Session, user_id: str, tz_name: str) -> list[GroupView]:
    """Agendamentos do usuário: os abertos primeiro (o mais próximo no topo),
    depois os últimos encerrados (o mais recente primeiro)."""
    backfill_groups(db, user_id)
    open_group_ids = (
        select(Schedule.group_id)
        .where(col(Schedule.user_id) == user_id)
        .where(col(Schedule.enabled).is_(True))
        .where(col(Schedule.group_id).is_not(None))  # NOT IN com NULL nunca casa com nada
    )
    open_groups = list(
        db.exec(
            select(ScheduleGroup)
            .where(col(ScheduleGroup.user_id) == user_id)
            .where(col(ScheduleGroup.id).in_(open_group_ids))
        ).all()
    )
    finished = list(
        db.exec(
            select(ScheduleGroup)
            .where(col(ScheduleGroup.user_id) == user_id)
            .where(col(ScheduleGroup.id).not_in(open_group_ids))
            .order_by(col(ScheduleGroup.created_at).desc())
            .limit(_LIST_RECENT_FINISHED)
        ).all()
    )
    views = _build_group_views(db, open_groups + finished, user_id, tz_name)
    open_views = sorted((v for v in views if v.is_open), key=lambda v: v.when_utc)
    done_views = sorted((v for v in views if not v.is_open), key=lambda v: v.when_utc, reverse=True)
    return open_views + done_views


def get_group_view(db: Session, group_id: str, user_id: str, tz_name: str) -> GroupView | None:
    group = db.get(ScheduleGroup, group_id)
    if group is None or group.user_id != user_id:
        return None
    views = _build_group_views(db, [group], user_id, tz_name)
    return views[0] if views else None


def conversation_items(
    db: Session, user_id: str, session_name: str, chat_id: str, tz_name: str
) -> tuple[list[MessageView], set[str]]:
    """Mensagens agendadas desta conversa, para aparecerem DENTRO dela.

    Devolve (itens, ids_enviados):
    - itens: agendadas/enviando sempre; falhas/canceladas dos últimos dias; e
      enviadas que ainda não aparecem no histórico local (raro — o scheduler
      já grava a mensagem enviada no cache da conversa).
    - ids_enviados: `waha_message_id` das enviadas por agendamento, pra marcar
      no histórico quais bolhas vieram de um agendamento (✓ agendada)."""
    now = utcnow()
    window_start = now - _CONVERSATION_HISTORY_WINDOW
    schedules = list(
        db.exec(
            select(Schedule)
            .where(col(Schedule.user_id) == user_id)
            .where(col(Schedule.session) == session_name)
            .where(col(Schedule.chat_id) == chat_id)
            .where((col(Schedule.enabled).is_(True)) | (col(Schedule.updated_at) >= window_start))
            .order_by(col(Schedule.created_at), col(Schedule.position))
        ).all()
    )
    if not schedules:
        return [], set()
    dispatches = _load_dispatches(db, [s.id for s in schedules])

    sent_ids: set[str] = set()
    for ds in dispatches.values():
        sent_ids.update(d.waha_message_id for d in ds if d.status == DispatchStatus.sent and d.waha_message_id)
    cached_ids: set[str] = set()
    if sent_ids:
        for chunk in _chunks(list(sent_ids)):
            cached_ids.update(
                db.exec(
                    select(CachedMessage.message_id)
                    .where(col(CachedMessage.user_id) == user_id)
                    .where(col(CachedMessage.message_id).in_(chunk))
                ).all()
            )

    items: list[MessageView] = []
    for schedule in schedules:
        view = _message_view(schedule, dispatches.get(schedule.id, []), tz_name)
        if view.status in ("scheduled", "sending"):
            items.append(view)
        elif view.status == "sent":
            mid = view.dispatch.waha_message_id if view.dispatch else None
            if mid and mid in cached_ids:
                continue  # já é uma bolha normal do histórico
            if view.when_utc >= window_start:
                items.append(view)
        elif view.when_utc >= window_start:
            items.append(view)
    items.sort(key=lambda m: (m.when_utc, m.position))
    return items, sent_ids
