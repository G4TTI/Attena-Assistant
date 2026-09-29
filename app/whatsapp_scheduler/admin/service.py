"""Consultas do admin — só METADADOS, sempre por SELECT de colunas explícitas
e devolvendo DTOs (dataclasses). Nenhuma consulta aqui lê ciphertext, hash de
destinatário, token OAuth, `password_hash` ou CPF; nenhuma decifra nada."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import and_, exists, func, or_
from sqlmodel import Session, col, select

from .. import failures, plans
from ..billing import metrics as billing_metrics
from ..billing import service as billing
from ..clock import utcnow
from ..models import (
    ENTITLED_SUBSCRIPTION_STATUSES,
    AdminAuditLog,
    AuditEventType,
    Automation,
    CalendarConnection,
    CalendarConnectionStatus,
    CrmProfile,
    CrmUserTag,
    Dispatch,
    DispatchStatus,
    Event,
    LoginAuditEvent,
    Plan,
    Schedule,
    Subscription,
    SubscriptionStatus,
    User,
    WhatsAppSession,
)
from . import crm

ONLINE_WINDOW = timedelta(minutes=15)
PER_PAGE = 25

ACTION_LABELS = {
    "crm_status_changed": "Alterou status do CRM",
    "crm_tag_added": "Adicionou tag",
    "crm_tag_removed": "Removeu tag",
    "crm_tag_created": "Criou tag",
    "crm_tag_deleted": "Excluiu tag",
    "crm_note_added": "Adicionou nota",
    "crm_note_updated": "Alterou nota",
    "crm_note_deleted": "Excluiu nota",
    "user_suspended": "Suspendeu conta",
    "user_reactivated": "Reativou conta",
    "plan_changed_manually": "Alterou plano manualmente",
    "plan_updated": "Editou plano do catálogo",
}


def _like(q: str) -> str:
    q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{q}%"


def _count(db: Session, query) -> int:
    return int(db.exec(select(func.count()).select_from(query.subquery())).one())


def _scalar(db: Session, query) -> int:
    return int(db.exec(query).one() or 0)


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@dataclass
class DashboardMetrics:
    total_users: int
    active_accounts: int
    suspended_accounts: int
    new_users_7d: int
    new_users_30d: int
    logins_24h: int
    failed_logins_24h: int
    online: int
    active_24h: int
    active_7d: int
    active_30d: int
    whatsapps_configured: int
    scheduled_pending: int
    sent_total: int
    sent_24h: int
    errors_total: int
    errors_24h: int
    finance: billing_metrics.FinanceSummary


def dashboard(db: Session, now: datetime | None = None) -> DashboardMetrics:
    now = now or utcnow()

    def users_where(*conds) -> int:
        return _scalar(db, select(func.count()).select_from(User).where(*conds))

    def activity_since(delta: timedelta) -> int:
        return users_where(col(User.last_activity_at) >= now - delta)

    def logins(event_type: AuditEventType) -> int:
        return _scalar(
            db,
            select(func.count()).select_from(LoginAuditEvent)
            .where(col(LoginAuditEvent.event_type) == event_type)
            .where(col(LoginAuditEvent.created_at) >= now - timedelta(hours=24)),
        )

    def dispatches(statuses, since: datetime | None = None, *, by: str = "updated") -> int:
        query = select(func.count()).select_from(Dispatch).where(col(Dispatch.status).in_(statuses))
        if since is not None:
            query = query.where((col(Dispatch.sent_at_utc) if by == "sent" else col(Dispatch.updated_at)) >= since)
        return _scalar(db, query)

    errors = [DispatchStatus.failed, DispatchStatus.skipped]
    return DashboardMetrics(
        total_users=users_where(),
        active_accounts=users_where(col(User.is_active).is_(True)),
        suspended_accounts=users_where(col(User.is_active).is_(False)),
        new_users_7d=users_where(col(User.created_at) >= now - timedelta(days=7)),
        new_users_30d=users_where(col(User.created_at) >= now - timedelta(days=30)),
        logins_24h=logins(AuditEventType.login_success),
        failed_logins_24h=logins(AuditEventType.login_failed),
        online=activity_since(ONLINE_WINDOW),
        active_24h=activity_since(timedelta(hours=24)),
        active_7d=activity_since(timedelta(days=7)),
        active_30d=activity_since(timedelta(days=30)),
        whatsapps_configured=_scalar(
            db, select(func.count()).select_from(WhatsAppSession).where(col(WhatsAppSession.disconnected_at).is_(None))
        ),
        scheduled_pending=_scalar(db, select(func.count()).select_from(Schedule).where(col(Schedule.enabled).is_(True))),
        sent_total=dispatches([DispatchStatus.sent]),
        sent_24h=dispatches([DispatchStatus.sent], now - timedelta(hours=24), by="sent"),
        errors_total=dispatches(errors),
        errors_24h=dispatches(errors, now - timedelta(hours=24)),
        finance=billing_metrics.summary(db, now),
    )


def active_session_names(db: Session) -> dict[str, str]:
    """session_name -> user_id das conexões WhatsApp não desconectadas."""
    return {
        name: user_id
        for name, user_id in db.exec(
            select(WhatsAppSession.session_name, WhatsAppSession.user_id).where(col(WhatsAppSession.disconnected_at).is_(None))
        ).all()
    }


async def live_whatsapp_status(waha, session_names: dict[str, str]) -> dict:
    """Quantas conexões estão WORKING agora. Usa só `name` e `status` da lista do
    WAHA — o campo `me` (número/nome do perfil) é descartado aqui."""
    from ..waha import WahaError

    try:
        sessions = await waha.list_sessions()
    except WahaError:
        return {"available": False, "working": 0, "by_user": {}}
    by_user: dict[str, int] = {}
    working = 0
    for item in sessions:
        name = str(item.get("name") or "")
        if name in session_names and str(item.get("status") or "").upper() == "WORKING":
            working += 1
            by_user[session_names[name]] = by_user.get(session_names[name], 0) + 1
    return {"available": True, "working": working, "by_user": by_user}


# --------------------------------------------------------------------------- #
# Usuários
# --------------------------------------------------------------------------- #
@dataclass
class UserRow:
    id: str
    name: str
    email: str
    phone: str | None
    created_at: datetime
    last_login_at: datetime | None
    last_activity_at: datetime | None
    is_active: bool
    role: str
    plan_name: str
    subscription_status: str | None
    whatsapp_count: int
    pending_count: int
    crm_status: str

    @property
    def online(self) -> bool:
        return bool(self.last_activity_at and self.last_activity_at >= utcnow() - ONLINE_WINDOW)


@dataclass
class UserFilters:
    q: str = ""
    plan: str = ""
    status: str = ""
    signup: str = ""
    activity: str = ""
    subscription: str = ""
    crm: str = ""
    tag: str = ""
    sort: str = "created"
    direction: str = "desc"
    page: int = 1

    def as_params(self, **overrides) -> dict:
        """Parâmetros de URL (com os nomes da query string: `dir`, não `direction`)."""
        data = {k: v for k, v in self.__dict__.items() if v not in ("", None)}
        data["dir"] = data.pop("direction", None)
        data.update(overrides)
        return {k: v for k, v in data.items() if v not in ("", None)}


SORTS = {
    "name": col(User.name),
    "email": col(User.email),
    "created": col(User.created_at),
    "login": col(User.last_login_at),
    "activity": col(User.last_activity_at),
}


def _entitled_subquery():
    return (
        select(
            Subscription.user_id.label("user_id"),
            Subscription.plan_id.label("plan_id"),
            Subscription.status.label("status"),
        )
        .where(col(Subscription.status).in_(list(ENTITLED_SUBSCRIPTION_STATUSES)))
        .subquery("ent")
    )


def list_users(db: Session, filters: UserFilters, now: datetime | None = None) -> tuple[list[UserRow], int]:
    now = now or utcnow()
    ent = _entitled_subquery()
    wa_count = (
        select(func.count(WhatsAppSession.id))
        .where(col(WhatsAppSession.user_id) == col(User.id), col(WhatsAppSession.disconnected_at).is_(None))
        .correlate(User)
        .scalar_subquery()
    )
    pending_count = (
        select(func.count(Schedule.id))
        .where(col(Schedule.user_id) == col(User.id), col(Schedule.enabled).is_(True))
        .correlate(User)
        .scalar_subquery()
    )
    incomplete = exists().where(
        col(Subscription.user_id) == col(User.id), col(Subscription.status) == SubscriptionStatus.incomplete
    )
    query = (
        select(
            User.id, User.name, User.email, User.phone, User.created_at, User.last_login_at, User.last_activity_at,
            User.is_active, User.role, Plan.name, ent.c.status, wa_count.label("wa"), pending_count.label("pending"),
            CrmProfile.status, incomplete.label("incomplete"),
        )
        .select_from(User)
        .outerjoin(ent, ent.c.user_id == col(User.id))
        .outerjoin(Plan, col(Plan.id) == ent.c.plan_id)
        .outerjoin(CrmProfile, col(CrmProfile.user_id) == col(User.id))
    )
    if filters.q.strip():
        like = _like(filters.q.strip())
        query = query.where(or_(col(User.name).ilike(like, escape="\\"), col(User.email).ilike(like, escape="\\")))
    default = plans.default_plan(db)
    if filters.plan:
        if default is not None and filters.plan == default.code:
            query = query.where(or_(ent.c.plan_id.is_(None), col(Plan.code) == filters.plan))
        else:
            query = query.where(col(Plan.code) == filters.plan)
    if filters.status == "active":
        query = query.where(col(User.is_active).is_(True))
    elif filters.status == "suspended":
        query = query.where(col(User.is_active).is_(False))
    elif filters.status == "admin":
        query = query.where(col(User.role) == "admin")
    signup_days = {"7d": 7, "30d": 30, "90d": 90}.get(filters.signup)
    if signup_days:
        query = query.where(col(User.created_at) >= now - timedelta(days=signup_days))
    activity = {
        "online": ONLINE_WINDOW, "24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)
    }.get(filters.activity)
    if activity is not None:
        query = query.where(col(User.last_activity_at) >= now - activity)
    elif filters.activity == "inactive":
        query = query.where(
            or_(col(User.last_activity_at).is_(None), col(User.last_activity_at) < now - timedelta(days=30))
        )
    if filters.subscription in ("active", "trialing", "past_due"):
        query = query.where(ent.c.status == filters.subscription)
    elif filters.subscription == "incomplete":
        query = query.where(ent.c.status.is_(None), incomplete)
    elif filters.subscription == "none":
        query = query.where(ent.c.status.is_(None), ~incomplete)
    if filters.crm in crm.CRM_STATUSES:
        if filters.crm == "lead":
            query = query.where(or_(col(CrmProfile.status).is_(None), col(CrmProfile.status) == "lead"))
        else:
            query = query.where(col(CrmProfile.status) == filters.crm)
    if filters.tag:
        query = query.where(
            exists().where(col(CrmUserTag.user_id) == col(User.id), col(CrmUserTag.tag_id) == filters.tag)
        )

    total = _count(db, query)
    order = pending_count if filters.sort == "pending" else SORTS.get(filters.sort, col(User.created_at))
    order = order.asc().nulls_last() if filters.direction == "asc" else order.desc().nulls_last()
    page = max(1, filters.page)
    rows = db.exec(query.order_by(order, col(User.id)).offset((page - 1) * PER_PAGE).limit(PER_PAGE)).all()
    out = []
    for r in rows:
        (uid, name, email, phone, created, last_login, last_activity, is_active, role, plan_name, sub_status, wa, pending,
         crm_status, has_incomplete) = r
        out.append(
            UserRow(
                id=uid, name=name, email=email, phone=phone, created_at=created, last_login_at=last_login,
                last_activity_at=last_activity, is_active=is_active, role=role,
                plan_name=plan_name or (default.name if default else "Gratuito"),
                subscription_status=str(sub_status) if sub_status else ("incomplete" if has_incomplete else None),
                whatsapp_count=int(wa or 0), pending_count=int(pending or 0), crm_status=crm_status or "lead",
            )
        )
    return out, total


# --------------------------------------------------------------------------- #
# Detalhe do cliente
# --------------------------------------------------------------------------- #
@dataclass
class UserDetail:
    id: str
    name: str
    email: str
    phone: str | None
    created_at: datetime
    last_login_at: datetime | None
    last_activity_at: datetime | None
    login_count: int
    is_active: bool
    role: str
    email_verified: bool
    plan_id: str | None
    plan_name: str
    subscription: dict | None
    pending_upgrade: dict | None
    whatsapp_sessions: list[dict]
    google_connected: bool
    automations: int
    pending_messages: int
    sent_messages: int
    error_messages: int
    billing: dict
    crm_status: str
    tags: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    recent_logins: list = field(default_factory=list)
    audit: list = field(default_factory=list)


def _subscription_dict(db: Session, sub: Subscription | None) -> dict | None:
    if sub is None:
        return None
    plan = db.get(Plan, sub.plan_id)
    return {
        "id": sub.id, "status": str(sub.status), "plan_name": plan.name if plan else "—", "provider": sub.provider,
        "manual": sub.provider == "manual", "amount_cents": sub.amount_cents, "currency": sub.currency,
        "started_at": sub.started_at, "current_period_end": sub.current_period_end, "created_at": sub.created_at,
    }


def user_detail(db: Session, user_id: str) -> UserDetail | None:
    row = db.exec(
        select(
            User.id, User.name, User.email, User.phone, User.created_at, User.last_login_at, User.last_activity_at,
            User.login_count, User.is_active, User.role, User.email_verified,
        ).where(col(User.id) == user_id)
    ).first()
    if row is None:
        return None
    (uid, name, email, phone, created, last_login, last_activity, login_count, is_active, role, verified) = row
    sub = plans.entitled_subscription(db, uid)
    plan = db.get(Plan, sub.plan_id) if sub else plans.default_plan(db)
    sessions = [
        {"id": sid, "label": label, "created_at": created_at}
        for sid, label, created_at in db.exec(
            select(WhatsAppSession.id, WhatsAppSession.name, WhatsAppSession.created_at)
            .where(col(WhatsAppSession.user_id) == uid)
            .where(col(WhatsAppSession.disconnected_at).is_(None))
            .order_by(col(WhatsAppSession.created_at))
        ).all()
    ]

    def dispatch_count(statuses) -> int:
        return _scalar(
            db,
            select(func.count()).select_from(Dispatch)
            .join(Schedule, col(Schedule.id) == col(Dispatch.schedule_id))
            .where(col(Schedule.user_id) == uid)
            .where(col(Dispatch.status).in_(statuses)),
        )

    return UserDetail(
        id=uid, name=name, email=email, phone=phone, created_at=created, last_login_at=last_login,
        last_activity_at=last_activity, login_count=login_count or 0, is_active=is_active, role=role,
        email_verified=verified, plan_id=plan.id if plan else None, plan_name=plan.name if plan else "Gratuito",
        subscription=_subscription_dict(db, sub),
        pending_upgrade=_subscription_dict(db, billing.pending_upgrade(db, uid)),
        whatsapp_sessions=sessions,
        google_connected=_scalar(
            db,
            select(func.count()).select_from(CalendarConnection)
            .where(col(CalendarConnection.user_id) == uid)
            .where(col(CalendarConnection.status) != CalendarConnectionStatus.disconnected),
        ) > 0,
        automations=_scalar(
            db, select(func.count(Automation.id)).join(Event, col(Event.id) == col(Automation.event_id)).where(col(Event.user_id) == uid)
        ),
        pending_messages=_scalar(
            db, select(func.count()).select_from(Schedule).where(col(Schedule.user_id) == uid).where(col(Schedule.enabled).is_(True))
        ),
        sent_messages=dispatch_count([DispatchStatus.sent]),
        error_messages=dispatch_count([DispatchStatus.failed, DispatchStatus.skipped]),
        billing=billing.masked_summary(billing.get_profile(db, uid)),
        crm_status=crm.status_of(db, uid),
        tags=crm.user_tags(db, uid),
        notes=crm.list_notes(db, uid),
        recent_logins=login_events(db, LoginFilters(user_id=uid), per_page=10)[0],
        audit=audit_entries(db, AuditFilters(target_id=uid), per_page=10)[0],
    )


# --------------------------------------------------------------------------- #
# Saúde operacional dos agendamentos (só metadados — nunca telefone/conteúdo)
# --------------------------------------------------------------------------- #
@dataclass
class DispatchRow:
    id: str
    scheduled_at: datetime
    status: str
    attempts: int
    failure_code: str | None
    failure_label: str | None
    error: str | None
    sent_at: datetime | None
    user_id: str | None
    user_name: str | None
    user_email: str | None
    whatsapp_id: str | None
    whatsapp_label: str | None


@dataclass
class DispatchFilters:
    status: str = ""
    q: str = ""
    date_from: str = ""
    date_to: str = ""
    page: int = 1

    def as_params(self, **overrides) -> dict:
        data = {k: v for k, v in self.__dict__.items() if v not in ("", None)}
        data["de"] = data.pop("date_from", None)
        data["ate"] = data.pop("date_to", None)
        data.update(overrides)
        return {k: v for k, v in data.items() if v not in ("", None)}


def _parse_day(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def dispatch_summary(db: Session) -> dict[str, int]:
    counts = {str(status): int(n) for status, n in db.exec(select(Dispatch.status, func.count()).group_by(col(Dispatch.status))).all()}
    return {
        "pending": counts.get("pending", 0) + counts.get("processing", 0),
        "sent": counts.get("sent", 0),
        "failed": counts.get("failed", 0) + counts.get("skipped", 0),
        "canceled": counts.get("canceled", 0),
    }


def list_dispatches(db: Session, filters: DispatchFilters) -> tuple[list[DispatchRow], int]:
    query = (
        select(
            Dispatch.id, Dispatch.scheduled_at_utc, Dispatch.status, Dispatch.attempts, Dispatch.failure_code,
            Dispatch.last_error, Dispatch.sent_at_utc, User.id, User.name, User.email, WhatsAppSession.id,
            WhatsAppSession.name,
        )
        .select_from(Dispatch)
        .join(Schedule, col(Schedule.id) == col(Dispatch.schedule_id))
        .outerjoin(User, col(User.id) == col(Schedule.user_id))
        .outerjoin(WhatsAppSession, col(WhatsAppSession.session_name) == col(Schedule.session))
    )
    status_map = {
        "pending": [DispatchStatus.pending, DispatchStatus.processing],
        "sent": [DispatchStatus.sent],
        "failed": [DispatchStatus.failed, DispatchStatus.skipped],
        "canceled": [DispatchStatus.canceled],
    }
    if filters.status in status_map:
        query = query.where(col(Dispatch.status).in_(status_map[filters.status]))
    if filters.q.strip():
        like = _like(filters.q.strip())
        query = query.where(or_(col(User.email).ilike(like, escape="\\"), col(User.name).ilike(like, escape="\\")))
    start = _parse_day(filters.date_from)
    end = _parse_day(filters.date_to)
    if start:
        query = query.where(col(Dispatch.scheduled_at_utc) >= start)
    if end:
        query = query.where(col(Dispatch.scheduled_at_utc) < end + timedelta(days=1))
    total = _count(db, query)
    page = max(1, filters.page)
    rows = db.exec(
        query.order_by(col(Dispatch.scheduled_at_utc).desc()).offset((page - 1) * PER_PAGE).limit(PER_PAGE)
    ).all()
    return [
        DispatchRow(
            id=r[0], scheduled_at=r[1], status=str(r[2]), attempts=r[3], failure_code=r[4],
            failure_label=failures.LABELS.get(r[4]) if r[4] else None,
            # Já é sanitizado ao gravar; passa de novo pelo filtro por garantia (dado antigo).
            error=failures.sanitize(r[5]), sent_at=r[6], user_id=r[7], user_name=r[8], user_email=r[9],
            whatsapp_id=r[10], whatsapp_label=r[11],
        )
        for r in rows
    ], total


# --------------------------------------------------------------------------- #
# Logins
# --------------------------------------------------------------------------- #
@dataclass
class LoginRow:
    at: datetime
    result: str
    user_id: str | None
    user_name: str | None
    user_email: str | None


@dataclass
class LoginFilters:
    result: str = ""
    q: str = ""
    user_id: str = ""
    page: int = 1

    def as_params(self, **overrides) -> dict:
        data = {k: v for k, v in self.__dict__.items() if v not in ("", None) and k != "user_id"}
        data.update(overrides)
        return {k: v for k, v in data.items() if v not in ("", None)}


def login_events(db: Session, filters: LoginFilters, *, per_page: int = PER_PAGE) -> tuple[list[LoginRow], int]:
    kinds = {"success": [AuditEventType.login_success], "failed": [AuditEventType.login_failed]}.get(
        filters.result, [AuditEventType.login_success, AuditEventType.login_failed]
    )
    query = (
        select(LoginAuditEvent.created_at, LoginAuditEvent.event_type, User.id, User.name, User.email)
        .select_from(LoginAuditEvent)
        .outerjoin(User, col(User.id) == col(LoginAuditEvent.user_id))
        .where(col(LoginAuditEvent.event_type).in_(kinds))
    )
    if filters.user_id:
        query = query.where(col(LoginAuditEvent.user_id) == filters.user_id)
    if filters.q.strip():
        like = _like(filters.q.strip())
        query = query.where(or_(col(User.email).ilike(like, escape="\\"), col(User.name).ilike(like, escape="\\")))
    total = _count(db, query)
    page = max(1, filters.page)
    rows = db.exec(query.order_by(col(LoginAuditEvent.created_at).desc()).offset((page - 1) * per_page).limit(per_page)).all()
    return [
        LoginRow(at=r[0], result="success" if str(r[1]) == "login_success" else "failed", user_id=r[2], user_name=r[3], user_email=r[4])
        for r in rows
    ], total


# --------------------------------------------------------------------------- #
# Auditoria administrativa
# --------------------------------------------------------------------------- #
@dataclass
class AuditRow:
    at: datetime
    admin_name: str | None
    action: str
    action_label: str
    target_type: str
    target_id: str | None
    target_label: str | None
    detail: dict | None


@dataclass
class AuditFilters:
    action: str = ""
    target_id: str = ""
    page: int = 1

    def as_params(self, **overrides) -> dict:
        data = {k: v for k, v in self.__dict__.items() if v not in ("", None) and k != "target_id"}
        data.update(overrides)
        return {k: v for k, v in data.items() if v not in ("", None)}


def audit_entries(db: Session, filters: AuditFilters, *, per_page: int = PER_PAGE) -> tuple[list[AuditRow], int]:
    target = User.__table__.alias("target_user")
    query = (
        select(
            AdminAuditLog.created_at, User.name, AdminAuditLog.action, AdminAuditLog.target_type,
            AdminAuditLog.target_id, target.c.email, AdminAuditLog.detail,
        )
        .select_from(AdminAuditLog)
        .outerjoin(User, col(User.id) == col(AdminAuditLog.admin_id))
        .outerjoin(target, and_(col(AdminAuditLog.target_type) == "user", target.c.id == col(AdminAuditLog.target_id)))
    )
    if filters.action:
        query = query.where(col(AdminAuditLog.action) == filters.action)
    if filters.target_id:
        query = query.where(col(AdminAuditLog.target_id) == filters.target_id)
    total = _count(db, query)
    page = max(1, filters.page)
    rows = db.exec(query.order_by(col(AdminAuditLog.created_at).desc()).offset((page - 1) * per_page).limit(per_page)).all()
    out = []
    for at, admin_name, action, target_type, target_id, target_email, detail in rows:
        try:
            parsed = json.loads(detail) if detail else None
        except ValueError:
            parsed = None
        out.append(
            AuditRow(
                at=at, admin_name=admin_name, action=action, action_label=ACTION_LABELS.get(action, action),
                target_type=target_type, target_id=target_id, target_label=target_email, detail=parsed,
            )
        )
    return out, total


# --------------------------------------------------------------------------- #
# Planos (visão admin)
# --------------------------------------------------------------------------- #
def plan_rows(db: Session) -> list[dict]:
    stats = billing_metrics.plan_stats(db)
    return [
        {
            "plan": p,
            "features": plans.features(p),
            "limits": plans.limits(p),
            "active": stats.get(p.id, {}).get("active", 0),
            "manual": stats.get(p.id, {}).get("manual", 0),
            "mrr_cents": stats.get(p.id, {}).get("mrr_cents", 0),
        }
        for p in plans.list_plans(db)
    ]


def recent_payments(db: Session, limit: int = 20) -> list[dict]:
    from ..models import Payment

    rows = db.exec(
        select(Payment.created_at, Payment.paid_at, Payment.amount_cents, Payment.currency, Payment.status, Payment.provider, User.email)
        .select_from(Payment)
        .outerjoin(User, col(User.id) == col(Payment.user_id))
        .order_by(col(Payment.created_at).desc())
        .limit(limit)
    ).all()
    return [
        {"created_at": r[0], "paid_at": r[1], "amount_cents": r[2], "currency": r[3], "status": str(r[4]), "provider": r[5], "email": r[6]}
        for r in rows
    ]


def recent_subscriptions(db: Session, limit: int = 20) -> list[dict]:
    rows = db.exec(
        select(Subscription.created_at, Subscription.status, Subscription.provider, Subscription.amount_cents, Subscription.currency, Plan.name, User.email)
        .select_from(Subscription)
        .outerjoin(Plan, col(Plan.id) == col(Subscription.plan_id))
        .outerjoin(User, col(User.id) == col(Subscription.user_id))
        .order_by(col(Subscription.created_at).desc())
        .limit(limit)
    ).all()
    return [
        {"created_at": r[0], "status": str(r[1]), "provider": r[2], "amount_cents": r[3], "currency": r[4], "plan": r[5], "email": r[6]}
        for r in rows
    ]
