"""Regras de negócio de AGENDAMENTO — o modelo único usado por Conversas,
Agendamentos e Calendário (automações).

Um agendamento é um `ScheduleGroup`: 1 destinatário + 1 WhatsApp + horário de
início + sequência de mensagens (`Schedule`s com o mesmo `group_id`, ordenadas
por `position`). Todo fluxo cria/cancela/edita/remarca por aqui, e o cálculo
de horário vem de `timing.py` — nenhuma tela calcula horário por conta própria.

O motor de envio (`scheduler.py`) só enxerga `Schedule`/`Dispatch`. A ordem
dentro da sequência é garantida por `ScheduleDependency` (cada mensagem espera
a anterior ser CONFIRMADA como enviada), então a mensagem 2 nunca sai antes da 1,
mesmo sob falha/retry.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from . import clock, timing
from .clock import utcnow
from .config import settings
from .errors import ValidationError
from .models import (
    OPEN_STATUSES,
    AutomationMessage,
    AutomationSchedule,
    Automation,
    Dispatch,
    DispatchStatus,
    Schedule,
    ScheduleDependency,
    ScheduleGroup,
    ScheduleSource,
)
from .recipients import RecipientError, normalize_recipient
from .recurrence import RecurrenceError, normalize_recurrence
from .scheduler import materialize_one
from .timing import DEFAULT_MAX_ATTEMPTS, DEFAULT_MESSAGE_GAP_SECONDS

logger = logging.getLogger("whatsapp_scheduler.service")

__all__ = [
    "ValidationError",
    "clean_messages",
    "backfill_groups",
    "cancel_group",
    "cancel_schedule",
    "cancel_schedules",
    "create_schedule",
    "create_sequence",
    "get_group",
    "group_schedules",
    "reschedule_group",
    "run_group_now",
    "run_now",
    "update_sequence",
]

# Tolerância pra "agora" nos formulários: escolher o minuto atual ainda vale.
_PAST_TOLERANCE = timedelta(minutes=1)


# --------------------------------------------------------------------------- #
# Criação
# --------------------------------------------------------------------------- #
def clean_messages(messages: list[str]) -> list[str]:
    """Tira espaços, descarta vazias e valida quantidade/tamanho."""
    texts = [(m or "").strip() for m in messages]
    texts = [t for t in texts if t]
    if not texts:
        raise ValidationError("A mensagem não pode ficar vazia.")
    if len(texts) > timing.MAX_MESSAGES_PER_SEQUENCE:
        raise ValidationError(f"No máximo {timing.MAX_MESSAGES_PER_SEQUENCE} mensagens por agendamento.")
    if any(len(t) > timing.MAX_MESSAGE_LENGTH for t in texts):
        raise ValidationError(f"Cada mensagem pode ter no máximo {timing.MAX_MESSAGE_LENGTH} caracteres.")
    return texts


def _normalize_cron(recurrence: str | None, message_count: int) -> str | None:
    if not (recurrence and recurrence.strip()):
        return None
    if message_count > 1:
        # A trava de ordem (dependência) espera a última dispatch da mensagem
        # anterior ser enviada; com recorrência a anterior já materializou a
        # próxima ocorrência e a cadeia sairia de sincronia. Só faz sentido com 1.
        raise ValidationError("A recorrência só está disponível para agendamentos com uma única mensagem.")
    try:
        return normalize_recurrence(recurrence)
    except RecurrenceError as exc:
        raise ValidationError(str(exc)) from exc


def _normalize_chat(recipient: str) -> str:
    try:
        return normalize_recipient(recipient)
    except (RecipientError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc


def _check_attempts(max_attempts: int) -> None:
    if max_attempts < 1 or max_attempts > 10:
        raise ValidationError("max_attempts deve estar entre 1 e 10.")


def _resolve_start(start: datetime, tz_name: str) -> tuple[datetime, datetime]:
    """(horário de parede, UTC) do início — datas extremas viram erro de validação, não 500."""
    try:
        start_local = timing.check_year(timing.resolve_local(start, tz_name))
        return start_local, timing.to_utc(start_local, tz_name)
    except ValidationError:
        raise
    except (OverflowError, ValueError, OSError) as exc:
        raise ValidationError("Data/hora fora do intervalo aceito.") from exc


# Duas requisições iguais em sequência (duplo clique, Enter + clique, retry de rede) viram UM agendamento.
_DUPLICATE_WINDOW = timedelta(seconds=20)


def _recent_identical_group(
    db: Session, *, user_id: str, chat_id: str, session: str, start_local: datetime, texts: list[str], source: ScheduleSource
) -> tuple[ScheduleGroup, list[Schedule]] | None:
    candidates = db.exec(
        select(ScheduleGroup)
        .where(col(ScheduleGroup.user_id) == user_id)
        .where(col(ScheduleGroup.chat_id) == chat_id)
        .where(col(ScheduleGroup.session) == session)
        .where(col(ScheduleGroup.start_local) == start_local)
        .where(col(ScheduleGroup.source) == source)
        .where(col(ScheduleGroup.created_at) >= utcnow() - _DUPLICATE_WINDOW)
    ).all()
    for group in candidates:
        schedules = group_schedules(db, group.id)
        if schedules and all(s.enabled for s in schedules) and [s.text for s in schedules] == texts:
            return group, schedules
    return None


def _chain_dependencies(db: Session, schedules: list[Schedule]) -> None:
    for previous, current in zip(schedules, schedules[1:]):
        db.add(ScheduleDependency(schedule_id=current.id, depends_on_schedule_id=previous.id))


def create_sequence(
    db: Session,
    *,
    user_id: str,
    session: str,
    recipient: str,
    messages: list[str],
    start: datetime,
    timezone: str | None = None,
    source: ScheduleSource | str = ScheduleSource.manual,
    recurrence: str | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    gap_seconds: int = DEFAULT_MESSAGE_GAP_SECONDS,
    allow_past: bool = True,
    recipient_name: str | None = None,
    dedupe: bool = False,
) -> tuple[ScheduleGroup, list[Schedule]]:
    """Cria UM agendamento (grupo) com a sequência inteira, numa transação só.

    `start` é o horário de INÍCIO da sequência: naive = horário de parede no
    fuso `timezone`; com offset = convertido pra `timezone`. A mensagem 0 sai
    exatamente nele; a mensagem N, em `start + N * gap_seconds`. Formulários
    passam `allow_past=False` pra recusar um horário que já passou (a
    automação de um evento já passado continua permitida, como sempre foi) e
    `dedupe=True` pra que um envio duplicado do mesmo formulário não crie o
    agendamento duas vezes."""
    texts = clean_messages(messages)
    tz_name = timing.validate_timezone(timezone or settings.default_timezone)
    chat_id = _normalize_chat(recipient)
    cron = _normalize_cron(recurrence, len(texts))
    _check_attempts(max_attempts)
    session = (session or "").strip()
    if not session:
        raise ValidationError("Escolha por qual WhatsApp enviar.")

    start_local, start_utc = _resolve_start(start, tz_name)
    if not allow_past and start_utc < clock.utcnow() - _PAST_TOLERANCE:
        raise ValidationError("O horário escolhido já passou. Escolha uma data e horário futuros.")
    times_utc = timing.sequence_times_utc(start_utc, len(texts), gap_seconds)

    if dedupe:
        existing = _recent_identical_group(
            db, user_id=user_id, chat_id=chat_id, session=session, start_local=start_local, texts=texts, source=ScheduleSource(source)
        )
        if existing is not None:
            return existing

    source = ScheduleSource(source)
    group = ScheduleGroup(
        user_id=user_id,
        source=source,
        session=session,
        recipient_input=recipient.strip(),
        recipient_name=(recipient_name or "").strip()[:120] or None,
        chat_id=chat_id,
        timezone=tz_name,
        start_local=start_local,
        message_gap_seconds=gap_seconds,
    )
    db.add(group)
    db.flush()

    schedules: list[Schedule] = []
    for position, (text, at_utc) in enumerate(zip(texts, times_utc)):
        schedule = Schedule(
            user_id=user_id,
            group_id=group.id,
            position=position,
            session=session,
            recipient_input=group.recipient_input,
            chat_id=chat_id,
            text=text,
            timezone=tz_name,
            # A 1ª usa o horário digitado tal qual (sem ida-e-volta por UTC,
            # que mudaria um horário inexistente numa virada de horário de verão).
            first_run_local=start_local if position == 0 else timing.to_local(at_utc, tz_name),
            recurrence=cron,
            max_attempts=max_attempts,
        )
        db.add(schedule)
        schedules.append(schedule)
    db.flush()
    _chain_dependencies(db, schedules)
    db.commit()

    db.refresh(group)
    for schedule in schedules:
        db.refresh(schedule)
    # Cria já a 1ª dispatch pra aparecer na lista na hora; as seguintes esperam
    # a anterior ser enviada (scheduler._dependency_gate) e materializam depois.
    for schedule in schedules:
        materialize_one(db, schedule)
    return group, schedules


def create_schedule(
    db: Session,
    *,
    user_id: str,
    session: str,
    recipient: str,
    text: str,
    send_at: datetime,
    timezone: str | None = None,
    recurrence: str | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    source: ScheduleSource | str = ScheduleSource.manual,
) -> Schedule:
    """Agendamento de UMA mensagem (API REST e chamadas simples): um grupo de 1."""
    _, schedules = create_sequence(
        db,
        user_id=user_id,
        session=session,
        recipient=recipient,
        messages=[text],
        start=send_at,
        timezone=timezone,
        source=source,
        recurrence=recurrence,
        max_attempts=max_attempts,
    )
    return schedules[0]


# --------------------------------------------------------------------------- #
# Leitura básica
# --------------------------------------------------------------------------- #
def get_group(db: Session, group_id: str, user_id: str) -> ScheduleGroup | None:
    """Sempre valida o dono — nunca devolve o agendamento de outro usuário."""
    group = db.get(ScheduleGroup, group_id)
    if group is None or group.user_id != user_id:
        return None
    return group


def group_schedules(db: Session, group_id: str) -> list[Schedule]:
    return list(
        db.exec(
            select(Schedule).where(col(Schedule.group_id) == group_id).order_by(col(Schedule.position))
        ).all()
    )


# --------------------------------------------------------------------------- #
# Cancelamento
# --------------------------------------------------------------------------- #
def _apply_cancel(db: Session, schedule: Schedule, now: datetime) -> None:
    schedule.enabled = False
    schedule.updated_at = now
    db.add(schedule)
    open_dispatches = db.exec(
        select(Dispatch)
        .where(col(Dispatch.schedule_id) == schedule.id)
        .where(col(Dispatch.status).in_(list(OPEN_STATUSES)))
    ).all()
    for dispatch in open_dispatches:
        dispatch.status = DispatchStatus.canceled
        dispatch.last_error = "Agendamento cancelado."
        dispatch.updated_at = now
        db.add(dispatch)


def _rewire_dependents(db: Session, schedule_id: str) -> None:
    """Uma mensagem do MEIO da sequência foi cancelada de propósito pelo
    usuário: as seguintes passam a esperar a anterior à cancelada (em vez de
    abortarem em cadeia, que é o comportamento certo só pra FALHA)."""
    own = db.get(ScheduleDependency, schedule_id)
    followers = db.exec(
        select(ScheduleDependency).where(col(ScheduleDependency.depends_on_schedule_id) == schedule_id)
    ).all()
    for follower in followers:
        if own is not None:
            follower.depends_on_schedule_id = own.depends_on_schedule_id
            db.add(follower)
        else:
            db.delete(follower)


def cancel_schedule(db: Session, schedule_id: str, *, user_id: str | None = None) -> bool:
    """Cancela UMA mensagem agendada (a de uma conversa, a da API). As
    mensagens seguintes da mesma sequência continuam valendo.

    `user_id=None` é usado só pelas chamadas internas (cascatas) que já
    validaram o dono do recurso pai — todo caminho vindo de rota HTTP passa o
    `user_id` do usuário autenticado."""
    schedule = db.get(Schedule, schedule_id)
    if schedule is None or not schedule.enabled:
        return False
    if user_id is not None and schedule.user_id != user_id:
        return False
    _rewire_dependents(db, schedule.id)
    _apply_cancel(db, schedule, utcnow())
    db.commit()
    return True


def cancel_schedules(db: Session, schedule_ids: list[str], *, user_id: str | None = None) -> int:
    """Cancela VÁRIAS mensagens numa transação só (grupo inteiro, cascata de
    desconexão/exclusão). Sem religar dependências: tudo some junto, e assim o
    scheduler nunca vê uma mensagem "solta" entre um commit e o outro."""
    if not schedule_ids:
        return 0
    now = utcnow()
    canceled = 0
    for schedule in db.exec(select(Schedule).where(col(Schedule.id).in_(schedule_ids))).all():
        if not schedule.enabled:
            continue
        if user_id is not None and schedule.user_id != user_id:
            continue
        _apply_cancel(db, schedule, now)
        canceled += 1
    db.commit()
    return canceled


def cancel_group(db: Session, group_id: str, *, user_id: str) -> bool:
    group = get_group(db, group_id, user_id)
    if group is None:
        return False
    ids = [s.id for s in group_schedules(db, group_id) if s.enabled]
    if not ids:
        return False
    cancel_schedules(db, ids, user_id=user_id)
    return True


# --------------------------------------------------------------------------- #
# Remarcar (mudou o horário de início) e editar
# --------------------------------------------------------------------------- #
def reschedule_group(db: Session, group: ScheduleGroup, new_start_utc: datetime) -> None:
    """Muda o INÍCIO da sequência (evento remarcado, ou edição do horário): a
    mensagem N passa a sair em `novo_início + N*gap`. Só mexe no que ainda não
    saiu. Faz commit."""
    now = utcnow()
    tz_name = group.timezone
    new_start_local = timing.to_local(new_start_utc, tz_name)
    schedules = group_schedules(db, group.id)
    times_utc = timing.sequence_times_utc(
        new_start_utc, (max((s.position for s in schedules), default=0) + 1), group.message_gap_seconds
    )
    group.start_local = new_start_local
    group.updated_at = now
    db.add(group)
    for schedule in schedules:
        if not schedule.enabled:
            continue
        target_utc = times_utc[schedule.position]
        schedule.first_run_local = new_start_local if schedule.position == 0 else timing.to_local(target_utc, tz_name)
        schedule.updated_at = now
        db.add(schedule)
        # UPDATE condicional (não ler → mudar → commitar): o scheduler pode estar
        # reivindicando esta dispatch agora; se ela já saiu de "pending" este
        # UPDATE não afeta nenhuma linha — não sobrescreve um envio em andamento.
        db.exec(
            sa_update(Dispatch)
            .where(col(Dispatch.schedule_id) == schedule.id)
            .where(col(Dispatch.status) == DispatchStatus.pending)
            .values(scheduled_at_utc=target_utc, updated_at=now)
        )
    db.commit()


def run_group_now(db: Session, group_id: str, *, user_id: str) -> bool:
    """"Enviar agora" de um agendamento: a sequência INTEIRA passa a começar agora
    (mensagem 0 já, as seguintes com o intervalo de sempre) — antecipar só a 1ª
    deixaria as outras no horário original, dias depois. Mesmo caminho da remarcação."""
    group = get_group(db, group_id, user_id)
    if group is None or not any(s.enabled for s in group_schedules(db, group.id)):
        return False
    reschedule_group(db, group, clock.utcnow())
    return True


def _delete_schedule_rows(db: Session, schedule_ids: list[str]) -> None:
    """Apaga mensagens que NUNCA foram enviadas (edição de um agendamento ainda
    intacto) — sem histórico a preservar. Ordem por causa das FKs."""
    if not schedule_ids:
        return
    db.exec(sa_delete(Dispatch).where(col(Dispatch.schedule_id).in_(schedule_ids)))
    db.exec(
        sa_delete(ScheduleDependency).where(
            col(ScheduleDependency.schedule_id).in_(schedule_ids)
            | col(ScheduleDependency.depends_on_schedule_id).in_(schedule_ids)
        )
    )
    db.exec(sa_delete(Schedule).where(col(Schedule.id).in_(schedule_ids)))


def update_sequence(
    db: Session,
    group_id: str,
    *,
    user_id: str,
    session: str,
    messages: list[str],
    start: datetime,
    recurrence: str | None = None,
    allow_past: bool = False,
) -> ScheduleGroup:
    """Edita um agendamento que AINDA NÃO começou a ser enviado (Conversas e
    Agendamentos). Muda horário, WhatsApp, textos, quantidade e ordem das
    mensagens; o destinatário não muda (pra outro, crie um novo). Se qualquer
    mensagem já foi enviada/está sendo enviada/falhou/foi cancelada, recusa —
    reescrever isso apagaria o histórico do que já saiu.

    Agendamentos vindos do Calendário são editados pela automação do evento."""
    group = get_group(db, group_id, user_id)
    if group is None:
        raise ValidationError("Agendamento não encontrado.")
    if group.source == ScheduleSource.calendar:
        raise ValidationError("Este agendamento vem de uma automação do Calendário — edite a automação no evento.")

    texts = clean_messages(messages)
    cron = _normalize_cron(recurrence, len(texts))
    session = (session or "").strip()
    if not session:
        raise ValidationError("Escolha por qual WhatsApp enviar.")
    start_local, start_utc = _resolve_start(start, group.timezone)
    if not allow_past and start_utc < clock.utcnow() - _PAST_TOLERANCE:
        raise ValidationError("O horário escolhido já passou. Escolha uma data e horário futuros.")

    old = group_schedules(db, group.id)
    old_ids = [s.id for s in old]
    if not old or not all(s.enabled for s in old):
        raise ValidationError("Este agendamento já foi cancelado ou concluído e não pode mais ser editado.")

    # Guarda atômica contra o scheduler: apaga as dispatches "pending" JÁ e
    # confere quantas eram. Se alguma mudou de estado (reivindicada/enviada)
    # entre a leitura e o DELETE, a conta não fecha e nada é alterado.
    all_dispatches = db.exec(select(Dispatch).where(col(Dispatch.schedule_id).in_(old_ids))).all()
    untouched = [d for d in all_dispatches if d.status == DispatchStatus.pending and d.attempts == 0]
    if len(untouched) != len(all_dispatches):
        raise ValidationError(
            "Este agendamento já começou a ser enviado e não pode mais ser editado. "
            "Cancele-o e crie um novo, se precisar."
        )
    result = db.exec(
        sa_delete(Dispatch)
        .where(col(Dispatch.schedule_id).in_(old_ids))
        .where(col(Dispatch.status) == DispatchStatus.pending)
        .where(col(Dispatch.attempts) == 0)
    )
    if result.rowcount != len(untouched):
        db.rollback()
        raise ValidationError("O envio deste agendamento acabou de começar e ele não pode mais ser editado.")

    now = utcnow()
    times_utc = timing.sequence_times_utc(start_utc, len(texts), group.message_gap_seconds)
    max_attempts = old[0].max_attempts

    kept = old[: len(texts)]
    _delete_schedule_rows(db, [s.id for s in old[len(texts):]])
    # A chain antiga é refeita do zero (posições/quantidade podem ter mudado).
    db.exec(sa_delete(ScheduleDependency).where(col(ScheduleDependency.schedule_id).in_([s.id for s in kept])))

    schedules: list[Schedule] = []
    for position, (text, at_utc) in enumerate(zip(texts, times_utc)):
        schedule = kept[position] if position < len(kept) else Schedule(
            user_id=user_id,
            group_id=group.id,
            recipient_input=group.recipient_input,
            chat_id=group.chat_id,
            max_attempts=max_attempts,
            text="",
            timezone=group.timezone,
            first_run_local=start_local,
        )
        schedule.position = position
        schedule.session = session
        schedule.text = text
        schedule.first_run_local = start_local if position == 0 else timing.to_local(at_utc, group.timezone)
        schedule.recurrence = cron
        schedule.enabled = True
        schedule.updated_at = now
        db.add(schedule)
        schedules.append(schedule)
    group.session = session
    group.start_local = start_local
    group.updated_at = now
    db.add(group)
    db.flush()
    _chain_dependencies(db, schedules)
    db.commit()

    for schedule in schedules:
        db.refresh(schedule)
        materialize_one(db, schedule)
    db.refresh(group)
    return group


# --------------------------------------------------------------------------- #
# "Enviar agora" (teste ponta a ponta)
# --------------------------------------------------------------------------- #
def run_now(db: Session, schedule_id: str, *, user_id: str | None = None) -> Dispatch | None:
    """Antecipa o envio para agora (para testar ponta a ponta).

    Se já existe uma dispatch pendente, apenas adianta o horário dela; senão,
    cria uma nova.
    """
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        return None
    if user_id is not None and schedule.user_id != user_id:
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


# --------------------------------------------------------------------------- #
# Migração: agrupa Schedules criados antes do modelo único
# --------------------------------------------------------------------------- #
def _chunks(items: list[str], size: int = 500):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def backfill_groups(db: Session, user_id: str | None = None) -> int:
    """Idempotente. Dá um `ScheduleGroup` a cada `Schedule` que ainda não tem:
    - mensagens de uma automação do Calendário viram UM grupo por
      (automação, destinatário), com a posição da mensagem na automação;
    - qualquer outro `Schedule` vira um grupo de 1 mensagem (origem `manual`).
    Roda no boot (main.py) e antes de listar os agendamentos de um usuário —
    nenhuma linha é apagada, só ganha `group_id`/`position`. Retorna quantos
    `Schedule`s foram agrupados."""
    query = select(Schedule).where(col(Schedule.group_id).is_(None)).where(col(Schedule.user_id).is_not(None))
    if user_id is not None:
        query = query.where(col(Schedule.user_id) == user_id)
    orphans = list(db.exec(query.order_by(col(Schedule.created_at))).all())
    if not orphans:
        return 0

    links: dict[str, AutomationSchedule] = {}
    for chunk in _chunks([s.id for s in orphans]):
        for link in db.exec(select(AutomationSchedule).where(col(AutomationSchedule.schedule_id).in_(chunk))).all():
            links[link.schedule_id] = link
    message_positions: dict[str, int] = {}
    for chunk in _chunks(list({link.message_id for link in links.values()})):
        for message in db.exec(select(AutomationMessage).where(col(AutomationMessage.id).in_(chunk))).all():
            message_positions[message.id] = message.position
    gaps: dict[str, int] = {}
    for chunk in _chunks(list({link.automation_id for link in links.values()})):
        for automation in db.exec(select(Automation).where(col(Automation.id).in_(chunk))).all():
            gaps[automation.id] = automation.message_gap_seconds

    groups: dict[tuple, ScheduleGroup] = {}
    lowest_position: dict[str, int] = {}
    assignments: list[tuple[Schedule, ScheduleGroup, int]] = []
    for schedule in orphans:
        link = links.get(schedule.id)
        if link is not None:
            key: tuple = ("automation", link.automation_id, link.recipient_chat_id)
            position = message_positions.get(link.message_id, 0)
            source, gap = ScheduleSource.calendar, gaps.get(link.automation_id, DEFAULT_MESSAGE_GAP_SECONDS)
        else:
            key, position = ("schedule", schedule.id), 0
            source, gap = ScheduleSource.manual, DEFAULT_MESSAGE_GAP_SECONDS
        group = groups.get(key)
        if group is None:
            group = ScheduleGroup(
                user_id=schedule.user_id,  # type: ignore[arg-type]  # filtrado por is_not(None) acima
                source=source,
                session=schedule.session,
                recipient_input=schedule.recipient_input,
                chat_id=schedule.chat_id,
                timezone=schedule.timezone,
                start_local=schedule.first_run_local,
                message_gap_seconds=gap,
                created_at=schedule.created_at,
            )
            groups[key] = group
            db.add(group)
            lowest_position[group.id] = position
        elif position < lowest_position[group.id]:
            lowest_position[group.id] = position
            group.start_local = schedule.first_run_local
        assignments.append((schedule, group, position))
    # Sem `relationship()` o SQLAlchemy não garante a ordem grupo -> schedule: grava os grupos antes.
    db.flush()
    for schedule, group, position in assignments:
        schedule.group_id = group.id
        schedule.position = position
        db.add(schedule)
    db.commit()
    logger.info("agrupados %d schedules em %d agendamentos (modelo único)", len(orphans), len(groups))
    return len(orphans)
