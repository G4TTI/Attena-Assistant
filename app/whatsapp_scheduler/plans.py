"""Camada central de planos: preço, período, recursos e limites.

Regra: nenhum outro módulo compara código de plano ("if plan == 'plus'"). Quem
precisa saber o que o usuário pode fazer pergunta aqui (`entitlements`,
`check_limit`). O catálogo vive na tabela `plans` e é editável em Admin >
Planos; `seed_default_plans` só cria um catálogo inicial quando a tabela está
vazia — os preços semeados são PROVISÓRIOS e devem ser revistos pelo dono.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import func
from sqlmodel import Session, col, select

from .clock import utcnow
from .config import settings
from .errors import ValidationError
from .models import (
    ENTITLED_SUBSCRIPTION_STATUSES,
    BillingPeriod,
    Plan,
    Schedule,
    Subscription,
    User,
    WhatsAppSession,
)

# Limites conhecidos (chave -> rótulo). None num plano = ilimitado.
LIMIT_LABELS: dict[str, str] = {
    "whatsapp_connections": "WhatsApps conectados",
    "pending_messages": "Mensagens programadas ativas",
    "calendar_connections": "Contas do Google Agenda",
}

PERIOD_LABELS = {BillingPeriod.monthly: "mês", BillingPeriod.yearly: "ano"}

_DEFAULT_CATALOG = [
    {
        "code": "free",
        "name": "Gratuito",
        "description": "Para começar a automatizar suas mensagens.",
        "price_cents": 0,
        "features": ["Agendamento de mensagens", "Automações a partir do Google Agenda", "Conversas (somente visualização)"],
        "limits": {"whatsapp_connections": 1, "pending_messages": 100, "calendar_connections": 1},
        "is_default": True,
        "sort_order": 0,
    },
    {
        "code": "plus",
        "name": "Plus",
        "description": "Para profissionais com agenda cheia.",
        "price_cents": 2990,
        "features": ["Tudo do Gratuito", "Mais WhatsApps conectados", "Mais mensagens programadas", "Suporte prioritário"],
        "limits": {"whatsapp_connections": 3, "pending_messages": 2000, "calendar_connections": 3},
        "sort_order": 10,
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Para equipes, clínicas e academias.",
        "price_cents": 5990,
        "features": ["Tudo do Plus", "WhatsApps e mensagens sem limite prático", "Atendimento dedicado"],
        "limits": {"whatsapp_connections": 10, "pending_messages": None, "calendar_connections": 10},
        "sort_order": 20,
    },
]


class PlanLimitReached(ValidationError):
    """Limite do plano atingido (só levantado com ENFORCE_PLAN_LIMITS=true)."""


def seed_default_plans(db: Session) -> int:
    """Idempotente: só cria o catálogo se ainda não existe nenhum plano."""
    if db.exec(select(func.count()).select_from(Plan)).one():
        return 0
    for item in _DEFAULT_CATALOG:
        db.add(
            Plan(
                code=item["code"],
                name=item["name"],
                description=item["description"],
                price_cents=item["price_cents"],
                features_json=json.dumps(item["features"], ensure_ascii=False),
                limits_json=json.dumps(item["limits"]),
                is_default=item.get("is_default", False),
                sort_order=item["sort_order"],
            )
        )
    db.commit()
    return len(_DEFAULT_CATALOG)


# --------------------------------------------------------------------------- #
# Leitura do catálogo
# --------------------------------------------------------------------------- #
def features(plan: Plan) -> list[str]:
    try:
        data = json.loads(plan.features_json or "[]")
    except ValueError:
        return []
    return [str(x) for x in data] if isinstance(data, list) else []


def limits(plan: Plan) -> dict[str, int | None]:
    try:
        data = json.loads(plan.limits_json or "{}")
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: (int(v) if v is not None else None) for k, v in data.items() if k in LIMIT_LABELS}


def format_price(cents: int, currency: str = "BRL") -> str:
    value = f"{cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {value}" if currency == "BRL" else f"{currency} {value}"


def monthly_cents(amount_cents: int, period: BillingPeriod | str) -> int:
    """Valor mensal equivalente (para MRR)."""
    return round(amount_cents / 12) if str(period) == BillingPeriod.yearly.value else amount_cents


def list_plans(db: Session, *, public_only: bool = False) -> list[Plan]:
    query = select(Plan).order_by(col(Plan.sort_order), col(Plan.price_cents))
    if public_only:
        query = query.where(col(Plan.is_public).is_(True))
    return list(db.exec(query).all())


def get_plan(db: Session, code: str) -> Plan | None:
    return db.exec(select(Plan).where(col(Plan.code) == code)).first()


def default_plan(db: Session) -> Plan | None:
    plan = db.exec(select(Plan).where(col(Plan.is_default).is_(True)).order_by(col(Plan.sort_order))).first()
    return plan or db.exec(select(Plan).order_by(col(Plan.price_cents), col(Plan.sort_order))).first()


def is_paid(plan: Plan) -> bool:
    return plan.price_cents > 0


# --------------------------------------------------------------------------- #
# Plano do usuário
# --------------------------------------------------------------------------- #
def entitled_subscription(db: Session, user_id: str) -> Subscription | None:
    """A assinatura que hoje dá direito a um plano (a mais recente, se houver)."""
    return db.exec(
        select(Subscription)
        .where(col(Subscription.user_id) == user_id)
        .where(col(Subscription.status).in_(list(ENTITLED_SUBSCRIPTION_STATUSES)))
        .order_by(col(Subscription.created_at).desc())
    ).first()


def current_plan(db: Session, user: User) -> Plan | None:
    subscription = entitled_subscription(db, user.id)
    if subscription is not None:
        plan = db.get(Plan, subscription.plan_id)
        if plan is not None:
            return plan
    return default_plan(db)


@dataclass
class Entitlements:
    plan: Plan | None
    limits: dict[str, int | None]
    features: list[str]

    def limit(self, key: str) -> int | None:
        return self.limits.get(key)


def entitlements(db: Session, user: User) -> Entitlements:
    plan = current_plan(db, user)
    return Entitlements(plan=plan, limits=limits(plan) if plan else {}, features=features(plan) if plan else [])


def usage(db: Session, user: User) -> dict[str, int]:
    from .models import CalendarConnection, CalendarConnectionStatus

    return {
        "whatsapp_connections": db.exec(
            select(func.count()).select_from(WhatsAppSession)
            .where(col(WhatsAppSession.user_id) == user.id)
            .where(col(WhatsAppSession.disconnected_at).is_(None))
        ).one(),
        "pending_messages": db.exec(
            select(func.count()).select_from(Schedule)
            .where(col(Schedule.user_id) == user.id)
            .where(col(Schedule.enabled).is_(True))
        ).one(),
        "calendar_connections": db.exec(
            select(func.count()).select_from(CalendarConnection)
            .where(col(CalendarConnection.user_id) == user.id)
            .where(col(CalendarConnection.status) != CalendarConnectionStatus.disconnected)
        ).one(),
    }


def check_limit(db: Session, user: User, key: str, *, adding: int = 1) -> None:
    """Levanta `PlanLimitReached` se `adding` itens a mais estourariam o limite
    do plano. Com ENFORCE_PLAN_LIMITS=false (padrão) nunca bloqueia; admins
    também não são limitados."""
    if not settings.enforce_plan_limits or user.role == "admin":
        return
    ent = entitlements(db, user)
    limit = ent.limit(key)
    if limit is None:
        return
    if usage(db, user).get(key, 0) + adding > limit:
        plan_name = ent.plan.name if ent.plan else "atual"
        raise PlanLimitReached(
            f"Seu plano {plan_name} permite até {limit} {LIMIT_LABELS.get(key, key).lower()}. "
            "Veja as opções em Planos para aumentar o limite."
        )


def touch(plan: Plan) -> None:
    plan.updated_at = utcnow()
