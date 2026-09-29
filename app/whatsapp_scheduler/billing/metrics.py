"""Números financeiros REAIS para o admin.

- Faturamento = soma de `Payment.status == "paid"` (confirmado pelo gateway).
- MRR = valor mensal equivalente das assinaturas `active`/`past_due` de um
  gateway real (provider fora de "none"/"manual"). Assinatura só fica ativa
  quando o gateway confirma um pagamento (service.apply_gateway_event).
- Nunca "usuários x preço do plano". Sem gateway = tudo zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from .. import plans
from ..clock import utcnow
from ..models import Payment, PaymentStatus, Plan, Subscription, SubscriptionStatus
from .service import NON_REVENUE_PROVIDERS

_MRR_STATUSES = (SubscriptionStatus.active, SubscriptionStatus.past_due)


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(dt: datetime, months: int) -> datetime:
    month = dt.month - 1 + months
    return dt.replace(year=dt.year + month // 12, month=month % 12 + 1)


def _paid_subscriptions(db: Session) -> list[Subscription]:
    return list(
        db.exec(
            select(Subscription)
            .where(col(Subscription.status).in_(list(_MRR_STATUSES)))
            .where(col(Subscription.provider).not_in(list(NON_REVENUE_PROVIDERS)))
        ).all()
    )


def mrr_cents(db: Session) -> int:
    return sum(plans.monthly_cents(s.amount_cents, s.billing_cycle) for s in _paid_subscriptions(db))


def _paid_sum(db: Session, *, since: datetime | None = None, until: datetime | None = None) -> int:
    query = select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(col(Payment.status) == PaymentStatus.paid)
    if since is not None:
        query = query.where(col(Payment.paid_at) >= since)
    if until is not None:
        query = query.where(col(Payment.paid_at) < until)
    return int(db.exec(query).one() or 0)


def _count_payments(db: Session, status: PaymentStatus) -> int:
    return int(db.exec(select(func.count()).select_from(Payment).where(col(Payment.status) == status)).one())


@dataclass
class FinanceSummary:
    mrr_cents: int
    revenue_total_cents: int
    revenue_month_cents: int
    active_subscriptions: int
    manual_subscriptions: int
    pending_payments: int
    failed_payments: int
    cancellations_month: int
    upgrade_requests: int
    has_payments: bool
    gateway_configured: bool


def summary(db: Session, now: datetime | None = None) -> FinanceSummary:
    from .gateway import is_configured

    now = now or utcnow()
    month = _month_start(now)
    paid = _paid_subscriptions(db)
    manual = int(
        db.exec(
            select(func.count()).select_from(Subscription)
            .where(col(Subscription.status).in_(list(_MRR_STATUSES)))
            .where(col(Subscription.provider) == "manual")
        ).one()
    )
    cancellations = int(
        db.exec(
            select(func.count()).select_from(Subscription)
            .where(col(Subscription.status) == SubscriptionStatus.cancelled)
            .where(col(Subscription.provider).not_in(list(NON_REVENUE_PROVIDERS)))
            .where(col(Subscription.cancelled_at) >= month)
        ).one()
    )
    upgrade_requests = int(
        db.exec(select(func.count()).select_from(Subscription).where(col(Subscription.status) == SubscriptionStatus.incomplete)).one()
    )
    total_payments = int(db.exec(select(func.count()).select_from(Payment)).one())
    return FinanceSummary(
        mrr_cents=sum(plans.monthly_cents(s.amount_cents, s.billing_cycle) for s in paid),
        revenue_total_cents=_paid_sum(db),
        revenue_month_cents=_paid_sum(db, since=month),
        active_subscriptions=len(paid),
        manual_subscriptions=manual,
        pending_payments=_count_payments(db, PaymentStatus.pending),
        failed_payments=_count_payments(db, PaymentStatus.failed),
        cancellations_month=cancellations,
        upgrade_requests=upgrade_requests,
        has_payments=total_payments > 0,
        gateway_configured=is_configured(),
    )


def monthly_revenue(db: Session, *, months: int = 12, now: datetime | None = None) -> list[dict]:
    """Faturamento pago por mês (mais antigo primeiro), para o gráfico."""
    now = now or utcnow()
    current = _month_start(now)
    out = []
    for offset in range(months - 1, -1, -1):
        start = _add_months(current, -offset)
        end = _add_months(start, 1)
        out.append({"month": start, "cents": _paid_sum(db, since=start, until=end)})
    return out


def plan_stats(db: Session) -> dict[str, dict]:
    """Por plano: assinantes ativos pagos, cortesias e MRR associado (só pago)."""
    stats: dict[str, dict] = {p.id: {"active": 0, "manual": 0, "mrr_cents": 0} for p in db.exec(select(Plan)).all()}
    rows = db.exec(select(Subscription).where(col(Subscription.status).in_(list(_MRR_STATUSES)))).all()
    for sub in rows:
        entry = stats.setdefault(sub.plan_id, {"active": 0, "manual": 0, "mrr_cents": 0})
        if sub.provider in NON_REVENUE_PROVIDERS:
            entry["manual"] += 1
        else:
            entry["active"] += 1
            entry["mrr_cents"] += plans.monthly_cents(sub.amount_cents, sub.billing_cycle)
    return stats
