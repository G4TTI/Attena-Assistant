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
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from . import timing, whatsapp_service
from .clock import utcnow
from .models import (
    OPEN_STATUSES,
    Automation,
    AutomationSchedule,
    CachedMessage,
    Dispatch,
    DispatchStatus,
    Event,
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

SOURCE_LABELS = {
    ScheduleSource.manual: "Agendamentos",
    ScheduleSource.conversation: "Conversa",
    ScheduleSource.calendar: "Calendário",
}
# Estados de uma mensagem que ainda vai sair ("programada").
OPEN_MESSAGE_STATUSES = ("scheduled", "sending")

# Quanto tempo mensagens já encerradas continuam aparecendo dentro da conversa.
_CONVERSATION_HISTORY_WINDOW = timedelta(days=3)
_LIST_RECENT_FINISHED = 50
# Até quantas mensagens programadas aparecem uma a uma dentro da conversa; a
# partir daí elas viram um botão só ("Ver mensagens programadas").
CONVERSATION_INLINE_LIMIT = 4
# Painel de mensagens programadas: quantas mensagens vêm por vez (sempre
# sequências inteiras) e o teto de "carregar mais".
PANEL_PAGE_SIZE = 30
PANEL_MAX_LIMIT = 1000


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


def _dispatch_exists(*conditions):
    return exists().where(col(Dispatch.schedule_id) == col(Schedule.id), *conditions)


def open_clause():
    """`message_status(...) in ("scheduled", "sending")` em SQL, pra contar sem
    carregar as linhas: tem dispatch aberta, ou ainda nenhuma e está ativa."""
    return or_(
        _dispatch_exists(col(Dispatch.status).in_(list(OPEN_STATUSES))),
        and_(col(Schedule.enabled).is_(True), ~_dispatch_exists()),
    )


def canceled_clause():
    """`message_status(...) == "canceled"` em SQL: nenhuma dispatch aberta e
    (desativada sem nunca ter tido dispatch, ou a ÚLTIMA dispatch foi cancelada).
    `test_sql_status_clauses_match_message_status` garante que não divergem."""
    later = aliased(Dispatch)
    last_is_canceled = _dispatch_exists(
        col(Dispatch.status) == DispatchStatus.canceled,
        # Compara com a dispatch do nível de cima (e não com `Schedule.id`): o SQLAlchemy só
        # correlaciona com o SELECT imediatamente acima — com Schedule aqui o subselect virava
        # um produto cartesiano com `schedules`.
        ~exists().where(
            col(later.schedule_id) == col(Dispatch.schedule_id),
            col(later.scheduled_at_utc) > col(Dispatch.scheduled_at_utc),
        ),
    )
    return and_(
        ~_dispatch_exists(col(Dispatch.status).in_(list(OPEN_STATUSES))),
        or_(and_(col(Schedule.enabled).is_(False), ~_dispatch_exists()), last_is_canceled),
    )


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


# --------------------------------------------------------------------------- #
# Conversas: o que aparece DENTRO da conversa e o painel "Mensagens programadas"
# --------------------------------------------------------------------------- #
def _chat_scope(user_id: str, session_name: str, chat_id: str) -> tuple:
    """Uma conversa = (usuário, WhatsApp, chat). Toda consulta daqui passa por isso."""
    return (
        col(Schedule.user_id) == user_id,
        col(Schedule.session) == session_name,
        col(Schedule.chat_id) == chat_id,
    )


def _count(db: Session, scope: tuple, clause) -> int:
    return int(db.exec(select(func.count()).select_from(Schedule).where(*scope, clause)).one())


def _by_time(m: MessageView) -> tuple:
    return (m.when_utc, m.position)


@dataclass
class ConversationScheduled:
    """Mensagens agendadas de uma conversa, do jeito que a conversa as mostra:

    - até `CONVERSATION_INLINE_LIMIT` programadas: uma bolha por mensagem;
    - acima disso: um botão só ("Ver mensagens programadas"), que abre o painel;
    - canceladas nunca viram bolha — ficam no painel; enquanto houver
      cancelamento recente aparece só um link discreto;
    - falhas e enviadas que ainda não estão no histórico continuam como bolhas
      (são o histórico real da conversa)."""

    open_items: list[MessageView] = field(default_factory=list)
    recent_items: list[MessageView] = field(default_factory=list)
    recent_canceled: int = 0  # canceladas nos últimos dias
    # Todas as canceladas da conversa (o mesmo número do painel) — só é contado
    # quando há cancelamento recente, o único caso em que a conversa o mostra.
    canceled_count: int = 0
    sent_ids: set[str] = field(default_factory=set)
    # Epoch do último envio confirmado: quando aumenta, a tela recarrega o histórico
    # pra a bolha real da mensagem aparecer.
    last_sent_ts: int = 0

    @property
    def open_count(self) -> int:
        return len(self.open_items)

    @property
    def collapsed(self) -> bool:
        return self.open_count > CONVERSATION_INLINE_LIMIT

    @property
    def inline_items(self) -> list[MessageView]:
        items = self.recent_items if self.collapsed else self.recent_items + self.open_items
        return sorted(items, key=_by_time)

    @property
    def next_open(self) -> MessageView | None:
        return self.open_items[0] if self.open_items else None

    @property
    def show_canceled_link(self) -> bool:
        return self.recent_canceled > 0 and not self.collapsed


def conversation_scheduled(
    db: Session, user_id: str, session_name: str, chat_id: str, tz_name: str
) -> ConversationScheduled:
    """Mensagens agendadas desta conversa, para aparecerem DENTRO dela (ver
    `ConversationScheduled`). Roda a cada poucos segundos com a conversa aberta,
    então só carrega as programadas e as encerradas (não canceladas) dos últimos
    dias; as canceladas são só contadas, no banco — nunca viram bolha."""
    now = utcnow()
    window_start = now - _CONVERSATION_HISTORY_WINDOW
    scope = _chat_scope(user_id, session_name, chat_id)
    recent = col(Schedule.updated_at) >= window_start
    view = ConversationScheduled(recent_canceled=_count(db, scope, and_(recent, canceled_clause())))
    if view.recent_canceled:  # o total só aparece no link, que só existe com cancelamento recente
        view.canceled_count = _count(db, scope, canceled_clause())
    schedules = list(
        db.exec(
            select(Schedule)
            .where(*scope)
            .where(or_(open_clause(), and_(recent, ~canceled_clause())))
            .order_by(col(Schedule.created_at), col(Schedule.position))
        ).all()
    )
    if not schedules:
        return view
    dispatches = _load_dispatches(db, [s.id for s in schedules])

    sent = [d for ds in dispatches.values() for d in ds if d.status == DispatchStatus.sent]
    view.sent_ids = {d.waha_message_id for d in sent if d.waha_message_id}
    view.last_sent_ts = max(
        (int(d.sent_at_utc.replace(tzinfo=timezone.utc).timestamp()) for d in sent if d.sent_at_utc is not None),
        default=0,
    )
    cached_ids: set[str] = set()
    for chunk in _chunks(list(view.sent_ids)):
        cached_ids.update(
            db.exec(
                select(CachedMessage.message_id)
                .where(col(CachedMessage.user_id) == user_id)
                .where(col(CachedMessage.message_id).in_(chunk))
            ).all()
        )

    for schedule in schedules:
        item = _message_view(schedule, dispatches.get(schedule.id, []), tz_name)
        if item.status in OPEN_MESSAGE_STATUSES:
            view.open_items.append(item)
        elif item.status == "canceled":
            continue  # não deveria chegar aqui (a consulta já as exclui): cancelada nunca vira bolha
        elif item.status == "sent":
            mid = item.dispatch.waha_message_id if item.dispatch else None
            if mid and mid in cached_ids:
                continue  # já é uma bolha normal do histórico
            if item.when_utc >= window_start:
                view.recent_items.append(item)
        elif item.when_utc >= window_start:
            view.recent_items.append(item)
    view.open_items.sort(key=_by_time)
    return view


def chat_recipient_name(db: Session, user_id: str, session_name: str, chat_id: str) -> str | None:
    """Nome do contato como ficou no agendamento mais recente desta conversa (sem ir ao WhatsApp)."""
    return db.exec(
        select(ScheduleGroup.recipient_name)
        .where(col(ScheduleGroup.user_id) == user_id)
        .where(col(ScheduleGroup.session) == session_name)
        .where(col(ScheduleGroup.chat_id) == chat_id)
        .where(col(ScheduleGroup.recipient_name).is_not(None))
        .order_by(col(ScheduleGroup.created_at).desc())
    ).first()


@dataclass
class PanelGroup:
    """Um agendamento (sequência) dentro do painel, só com as mensagens do filtro."""

    group: ScheduleGroup | None  # None = mensagem antiga, de antes dos agendamentos agrupados
    messages: list[MessageView]
    total_messages: int
    start_local: datetime | None = None
    event_title: str | None = None

    @property
    def id(self) -> str | None:
        return self.group.id if self.group is not None else None

    @property
    def source_label(self) -> str:
        return SOURCE_LABELS.get(self.group.source, "") if self.group is not None else ""

    @property
    def can_cancel_all(self) -> bool:
        return self.group is not None and sum(1 for m in self.messages if m.can_cancel) >= 2

    @property
    def time_format(self) -> str:
        """As mensagens de uma sequência saem com segundos de diferença: aí os segundos aparecem."""
        return "%H:%M:%S" if any(m.when_local.second for m in self.messages) else "%H:%M"


@dataclass
class ScheduledPanel:
    """Painel "Mensagens programadas" de uma conversa (componente ScheduledMessagesPanel)."""

    chat_id: str
    show_scheduled: bool
    show_canceled: bool
    limit: int
    scheduled_count: int
    canceled_count: int
    groups: list[PanelGroup] = field(default_factory=list)
    has_more: bool = False

    @property
    def no_filter(self) -> bool:
        return not (self.show_scheduled or self.show_canceled)

    @property
    def selectable(self) -> bool:
        """Alguma mensagem da página pode ser marcada pra cancelar em massa."""
        return any(m.can_cancel for g in self.groups for m in g.messages)

    @property
    def can_load_more(self) -> bool:
        return self.has_more and self.limit < PANEL_MAX_LIMIT

    @property
    def next_limit(self) -> int:
        return min(self.limit + PANEL_PAGE_SIZE, PANEL_MAX_LIMIT)

    def params(self, **overrides: object) -> dict:
        """Estado do painel (filtros + quanto já carregou) — acompanha toda requisição dele."""
        params: dict = {
            "chat": self.chat_id,
            "scheduled": int(self.show_scheduled),
            "canceled": int(self.show_canceled),
            "limit": self.limit,
        }
        params.update(overrides)
        return params


def _event_titles(db: Session, user_id: str, group_ids: list[str]) -> dict[str, str]:
    """Título do evento de cada agendamento criado por uma automação do Calendário."""
    titles: dict[str, str] = {}
    for chunk in _chunks(group_ids):
        rows = db.exec(
            select(Schedule.group_id, Event.title)
            .select_from(Schedule)
            .join(AutomationSchedule, col(AutomationSchedule.schedule_id) == col(Schedule.id))
            .join(Automation, col(Automation.id) == col(AutomationSchedule.automation_id))
            .join(Event, col(Event.id) == col(Automation.event_id))
            .where(col(Schedule.group_id).in_(chunk))
            .where(col(Event.user_id) == user_id)
        ).all()
        for group_id, title in rows:
            if title and group_id not in titles:
                titles[group_id] = title
    return titles


def scheduled_panel(
    db: Session,
    user_id: str,
    session_name: str,
    chat_id: str,
    tz_name: str,
    *,
    show_scheduled: bool = True,
    show_canceled: bool = False,
    limit: int = PANEL_PAGE_SIZE,
) -> ScheduledPanel:
    """Mensagens programadas e/ou canceladas de UMA conversa, agrupadas por
    agendamento (cada sequência na sua ordem). O filtro e os contadores rodam
    no banco; a lista vem em páginas de sequências inteiras (`limit` mensagens,
    no mínimo) — as com mensagem programada primeiro, a próxima a sair no topo;
    depois as só canceladas, a mais recente primeiro."""
    scope = _chat_scope(user_id, session_name, chat_id)
    panel = ScheduledPanel(
        chat_id=chat_id,
        show_scheduled=show_scheduled,
        show_canceled=show_canceled,
        limit=max(PANEL_PAGE_SIZE, min(int(limit or 0), PANEL_MAX_LIMIT)),
        scheduled_count=_count(db, scope, open_clause()),
        canceled_count=_count(db, scope, canceled_clause()),
    )
    wanted: set[str] = set()
    clauses = []
    if show_scheduled:
        wanted.update(OPEN_MESSAGE_STATUSES)
        clauses.append(open_clause())
    if show_canceled:
        wanted.add("canceled")
        clauses.append(canceled_clause())
    if not clauses:
        return panel

    schedules = list(db.exec(select(Schedule).where(*scope).where(or_(*clauses))).all())
    dispatches = _load_dispatches(db, [s.id for s in schedules])
    by_key: dict[str, list[MessageView]] = {}
    for schedule in schedules:
        item = _message_view(schedule, dispatches.get(schedule.id, []), tz_name)
        if item.status in wanted:
            by_key.setdefault(schedule.group_id or schedule.id, []).append(item)

    def next_open(items: list[MessageView]) -> datetime | None:
        return min((m.when_utc for m in items if m.status in OPEN_MESSAGE_STATUSES), default=None)

    pending = sorted((k for k in by_key if next_open(by_key[k]) is not None), key=lambda k: next_open(by_key[k]))
    pending_set = set(pending)
    done = sorted(
        (k for k in by_key if k not in pending_set), key=lambda k: max(m.when_utc for m in by_key[k]), reverse=True
    )
    page: list[str] = []
    shown = 0
    for key in pending + done:
        if shown >= panel.limit:
            break
        page.append(key)
        shown += len(by_key[key])
    panel.has_more = len(page) < len(by_key)

    group_ids = [k for k in page if by_key[k][0].schedule.group_id]
    groups: dict[str, ScheduleGroup] = {}
    totals: dict[str, int] = {}
    for chunk in _chunks(group_ids):
        groups.update(
            (g.id, g)
            for g in db.exec(
                select(ScheduleGroup)
                .where(col(ScheduleGroup.id).in_(chunk))
                .where(col(ScheduleGroup.user_id) == user_id)
            ).all()
        )
        totals.update(
            db.exec(
                select(Schedule.group_id, func.count())
                .where(col(Schedule.group_id).in_(chunk))
                .group_by(col(Schedule.group_id))
            ).all()
        )
    titles = _event_titles(db, user_id, [gid for gid, g in groups.items() if g.source == ScheduleSource.calendar])

    for key in page:
        group = groups.get(key)
        panel.groups.append(
            PanelGroup(
                group=group,
                messages=sorted(by_key[key], key=lambda m: (m.position, m.when_utc)),
                total_messages=totals.get(key, len(by_key[key])),
                start_local=(
                    timing.to_local(timing.to_utc(group.start_local, group.timezone), tz_name) if group else None
                ),
                event_title=titles.get(key),
            )
        )
    return panel
