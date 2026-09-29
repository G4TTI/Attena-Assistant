"""Regras de faturamento: perfil de cobrança (cifrado), upgrade, assinaturas e
pagamentos. Faturamento = soma de `Payment` com status "paid" vindo do gateway;
nada aqui marca algo como pago por conta própria."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, col, select

from .. import plans, privacy
from ..clock import utcnow
from ..errors import ValidationError
from ..models import (
    ENTITLED_SUBSCRIPTION_STATUSES,
    BillingProfile,
    Payment,
    PaymentStatus,
    Plan,
    Subscription,
    SubscriptionStatus,
    User,
)
from .validation import BillingForm, UF_NAMES, format_cep, mask_cpf

_T = "billing_profiles"
_ENCRYPTED_FIELDS = (
    "full_name", "cpf", "phone", "postal_code", "address", "address_number", "address_complement", "city",
)
# Provedores que NUNCA contam como receita (sem gateway, ou concedido pelo admin).
NON_REVENUE_PROVIDERS = ("none", "manual")

SUBSCRIPTION_STATUS_LABELS = {
    "incomplete": "aguardando pagamento",
    "trialing": "em período de teste",
    "active": "ativa",
    "past_due": "em atraso",
    "cancelled": "cancelada",
    "expired": "expirada",
}
PAYMENT_STATUS_LABELS = {"pending": "pendente", "paid": "pago", "failed": "falhou", "refunded": "estornado"}


# --------------------------------------------------------------------------- #
# Perfil de cobrança
# --------------------------------------------------------------------------- #
def get_profile(db: Session, user_id: str) -> BillingProfile | None:
    return db.exec(select(BillingProfile).where(col(BillingProfile.user_id) == user_id)).first()


def masked_summary(profile: BillingProfile | None) -> dict:
    """O que o ADMIN pode ver — sem decifrar nada (CPF mascarado, só a UF)."""
    if profile is None:
        return {"has_profile": False, "cpf_masked": "—", "state": ""}
    return {
        "has_profile": True,
        "cpf_masked": mask_cpf(profile.cpf_last2),
        "state": profile.state,
        "state_name": UF_NAMES.get(profile.state, ""),
        "updated_at": profile.updated_at,
    }


def _open(profile: BillingProfile, field: str) -> str:
    return privacy.open_field(_T, field, profile.id, getattr(profile, f"{field}_encrypted"), safe=True) or ""


def owner_form_values(profile: BillingProfile | None, user: User) -> dict:
    """Valores do formulário para o PRÓPRIO usuário (decifrados em memória).
    O CPF nunca volta inteiro: só o mascarado, e o campo fica vazio = "manter"."""
    if profile is None:
        return {
            "full_name": user.name, "cpf": "", "cpf_masked": None, "phone": user.phone or "", "postal_code": "",
            "address": "", "address_number": "", "address_complement": "", "city": "", "state": "",
        }
    cep = _open(profile, "postal_code")
    return {
        "full_name": _open(profile, "full_name") or user.name,
        "cpf": "",
        "cpf_masked": mask_cpf(profile.cpf_last2) if profile.cpf_encrypted else None,
        "phone": _open(profile, "phone") or user.phone or "",
        "postal_code": format_cep(cep) if len(cep) == 8 else cep,
        "address": _open(profile, "address"),
        "address_number": _open(profile, "address_number"),
        "address_complement": _open(profile, "address_complement"),
        "city": _open(profile, "city"),
        "state": profile.state,
    }


def save_profile(db: Session, user: User, form: BillingForm) -> BillingProfile:
    profile = get_profile(db, user.id) or BillingProfile(user_id=user.id)
    values = {
        "full_name": form.full_name, "phone": form.phone, "postal_code": form.postal_code, "address": form.address,
        "address_number": form.address_number, "address_complement": form.address_complement or None, "city": form.city,
    }
    for field, value in values.items():
        setattr(profile, f"{field}_encrypted", privacy.seal_field(_T, field, profile.id, value))
    if form.cpf is not None:
        profile.cpf_encrypted = privacy.seal_field(_T, "cpf", profile.id, form.cpf)
        profile.cpf_last2 = form.cpf[-2:]
    profile.state = form.state
    profile.country = "BR"
    profile.updated_at = utcnow()
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def delete_profile(db: Session, user: User) -> bool:
    """Direito de exclusão: apaga os dados de cobrança se não houver assinatura paga em curso."""
    profile = get_profile(db, user.id)
    if profile is None:
        return False
    sub = plans.entitled_subscription(db, user.id)
    if sub is not None and sub.provider not in NON_REVENUE_PROVIDERS:
        raise ValidationError("Há uma assinatura paga em andamento: cancele-a antes de remover os dados de faturamento.")
    db.delete(profile)
    db.commit()
    return True


# --------------------------------------------------------------------------- #
# Upgrade / assinaturas
# --------------------------------------------------------------------------- #
def pending_upgrade(db: Session, user_id: str) -> Subscription | None:
    return db.exec(
        select(Subscription)
        .where(col(Subscription.user_id) == user_id)
        .where(col(Subscription.status) == SubscriptionStatus.incomplete)
        .order_by(col(Subscription.created_at).desc())
    ).first()


def start_upgrade(db: Session, user: User, plan: Plan) -> Subscription:
    """Registra o PEDIDO de upgrade (status "incomplete"). Não dá acesso ao plano
    nem conta como receita — isso só acontece quando o gateway confirmar."""
    if not plan.is_active or not plans.is_paid(plan):
        raise ValidationError("Este plano não está disponível para contratação.")
    if get_profile(db, user.id) is None:
        raise ValidationError("Preencha os dados para faturamento antes de continuar.")
    now = utcnow()
    for other in db.exec(
        select(Subscription)
        .where(col(Subscription.user_id) == user.id)
        .where(col(Subscription.status) == SubscriptionStatus.incomplete)
    ).all():
        if other.plan_id == plan.id:
            return other
        other.status = SubscriptionStatus.cancelled
        other.cancelled_at = now
        other.updated_at = now
        db.add(other)
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=SubscriptionStatus.incomplete,
        billing_cycle=plan.billing_period,
        amount_cents=plan.price_cents,
        currency=plan.currency,
        provider="none",
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def cancel_pending_upgrade(db: Session, user: User) -> int:
    now = utcnow()
    rows = db.exec(
        select(Subscription)
        .where(col(Subscription.user_id) == user.id)
        .where(col(Subscription.status) == SubscriptionStatus.incomplete)
    ).all()
    for sub in rows:
        sub.status = SubscriptionStatus.cancelled
        sub.cancelled_at = now
        sub.updated_at = now
        db.add(sub)
    db.commit()
    return len(rows)


def _end_entitled(db: Session, user_id: str, now: datetime) -> None:
    for sub in db.exec(
        select(Subscription)
        .where(col(Subscription.user_id) == user_id)
        .where(col(Subscription.status).in_(list(ENTITLED_SUBSCRIPTION_STATUSES)))
    ).all():
        sub.status = SubscriptionStatus.cancelled
        sub.cancelled_at = now
        sub.updated_at = now
        db.add(sub)


def grant_plan_manually(db: Session, user: User, plan: Plan) -> Subscription | None:
    """Admin muda o plano à mão (cortesia/teste). Nunca conta como receita:
    provider "manual", valor 0. Plano gratuito = só encerra o que houver."""
    now = utcnow()
    _end_entitled(db, user.id, now)
    if not plans.is_paid(plan) and plan.is_default:
        db.commit()
        return None
    subscription = Subscription(
        user_id=user.id, plan_id=plan.id, status=SubscriptionStatus.active, billing_cycle=plan.billing_period,
        amount_cents=0, currency=plan.currency, started_at=now, current_period_start=now, provider="manual",
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


# --------------------------------------------------------------------------- #
# Eventos do gateway (o ÚNICO caminho que ativa/cobra)
# --------------------------------------------------------------------------- #
def record_payment(
    db: Session,
    *,
    user_id: str,
    subscription_id: str | None,
    amount_cents: int,
    status: PaymentStatus,
    provider: str,
    provider_payment_id: str | None,
    currency: str = "BRL",
    paid_at: datetime | None = None,
) -> Payment:
    """Idempotente por (provider, provider_payment_id): o mesmo webhook repetido
    atualiza o pagamento em vez de duplicar receita."""
    if provider in NON_REVENUE_PROVIDERS:
        raise ValueError("pagamento só pode vir de um gateway real")
    payment = None
    if provider_payment_id:
        payment = db.exec(
            select(Payment)
            .where(col(Payment.provider) == provider)
            .where(col(Payment.provider_payment_id) == provider_payment_id)
        ).first()
    payment = payment or Payment(
        user_id=user_id, subscription_id=subscription_id, amount_cents=amount_cents, provider=provider,
        provider_payment_id=provider_payment_id, currency=currency,
    )
    payment.status = status
    payment.amount_cents = amount_cents
    payment.paid_at = (paid_at or utcnow()) if status == PaymentStatus.paid else payment.paid_at
    payment.updated_at = utcnow()
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def apply_gateway_event(db: Session, provider: str, event) -> Subscription | None:
    """Aplica um evento JÁ VALIDADO pelo gateway (ver gateway.GatewayEvent)."""
    subscription = None
    if event.provider_subscription_id:
        subscription = db.exec(
            select(Subscription)
            .where(col(Subscription.provider) == provider)
            .where(col(Subscription.provider_subscription_id) == event.provider_subscription_id)
        ).first()
    if subscription is None:
        return None
    now = event.occurred_at or utcnow()
    if event.kind == "payment_paid":
        record_payment(
            db, user_id=subscription.user_id, subscription_id=subscription.id,
            amount_cents=event.amount_cents if event.amount_cents is not None else subscription.amount_cents,
            status=PaymentStatus.paid, provider=provider, provider_payment_id=event.provider_payment_id,
            currency=event.currency, paid_at=now,
        )
        if subscription.status != SubscriptionStatus.active:
            _end_entitled(db, subscription.user_id, now)
            subscription.status = SubscriptionStatus.active
            subscription.started_at = subscription.started_at or now
        subscription.current_period_start = event.period_start or subscription.current_period_start or now
        subscription.current_period_end = event.period_end or subscription.current_period_end
    elif event.kind == "payment_failed":
        record_payment(
            db, user_id=subscription.user_id, subscription_id=subscription.id,
            amount_cents=event.amount_cents or subscription.amount_cents, status=PaymentStatus.failed,
            provider=provider, provider_payment_id=event.provider_payment_id, currency=event.currency,
        )
        if subscription.status == SubscriptionStatus.active:
            subscription.status = SubscriptionStatus.past_due
    elif event.kind == "payment_refunded" and event.provider_payment_id:
        record_payment(
            db, user_id=subscription.user_id, subscription_id=subscription.id,
            amount_cents=event.amount_cents or subscription.amount_cents, status=PaymentStatus.refunded,
            provider=provider, provider_payment_id=event.provider_payment_id, currency=event.currency,
        )
    elif event.kind == "subscription_past_due":
        subscription.status = SubscriptionStatus.past_due
    elif event.kind == "subscription_cancelled":
        subscription.status = SubscriptionStatus.cancelled
        subscription.cancelled_at = now
    subscription.updated_at = utcnow()
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription
