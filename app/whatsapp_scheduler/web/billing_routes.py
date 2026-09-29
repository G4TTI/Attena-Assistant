"""UI de Planos e upgrade. Dados de faturamento são pedidos SÓ aqui, quando o
usuário escolhe um plano pago — nunca no cadastro."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlmodel import Session

from .. import auth, plans
from ..billing import gateway as billing_gateway
from ..billing import service as billing
from ..billing.validation import UF_NAMES, validate_form
from ..db import get_session
from ..errors import ValidationError
from ..models import User
from .routes import templates

router = APIRouter(tags=["ui-planos"])

templates.env.filters["brl"] = plans.format_price
templates.env.filters["subscription_status"] = lambda status: billing.SUBSCRIPTION_STATUS_LABELS.get(str(status), str(status))
templates.env.filters["payment_status"] = lambda status: billing.PAYMENT_STATUS_LABELS.get(str(status), str(status))

_FORM_FIELDS = (
    "full_name", "cpf", "phone", "postal_code", "address", "address_number", "address_complement", "city", "state",
)


def _plan_or_404(db: Session, code: str):
    plan = plans.get_plan(db, code)
    if plan is None or not plan.is_public:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")
    return plan


def _plans_ctx(request: Request, db: Session, user: User, **extra) -> dict:
    ent = plans.entitlements(db, user)
    subscription = plans.entitled_subscription(db, user.id)
    usage = plans.usage(db, user)
    catalog = [
        {"plan": p, "features": plans.features(p), "limits": plans.limits(p), "is_paid": plans.is_paid(p)}
        for p in plans.list_plans(db, public_only=True)
    ]
    pending = billing.pending_upgrade(db, user.id)
    pending_plan = db.get(plans.Plan, pending.plan_id) if pending else None
    return {
        "request": request,
        "nav": "planos",
        "current_user": user,
        "current_plan": ent.plan,
        "current_limits": ent.limits,
        "subscription": subscription,
        "usage": usage,
        "limit_labels": plans.LIMIT_LABELS,
        "period_labels": {str(k): v for k, v in plans.PERIOD_LABELS.items()},
        "catalog": catalog,
        "pending": pending,
        "pending_plan": pending_plan,
        "billing": billing.masked_summary(billing.get_profile(db, user.id)),
        "gateway_configured": billing_gateway.is_configured(),
        **extra,
    }


@router.get("/planos", response_class=HTMLResponse)
def page_planos(
    request: Request,
    ok: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    return templates.TemplateResponse("planos.html", _plans_ctx(request, db, current_user, ok=ok, error=error))


def _upgrade_ctx(request: Request, db: Session, user: User, plan, *, values: dict, error: str | None = None) -> dict:
    return {
        "request": request,
        "nav": "planos",
        "current_user": user,
        "plan": plan,
        "features": plans.features(plan),
        "limits": plans.limits(plan),
        "limit_labels": plans.LIMIT_LABELS,
        "period_label": plans.PERIOD_LABELS.get(plan.billing_period, "mês"),
        "values": values,
        "uf_names": UF_NAMES,
        "error": error,
    }


@router.get("/planos/{code}/upgrade", response_class=HTMLResponse)
def page_upgrade(
    request: Request,
    code: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> Response:
    plan = _plan_or_404(db, code)
    if not plans.is_paid(plan):
        return RedirectResponse(url="/planos", status_code=303)
    current = plans.current_plan(db, current_user)
    if current is not None and current.id == plan.id:
        return RedirectResponse(url="/planos?ok=" + quote(f"Você já está no plano {plan.name}."), status_code=303)
    values = billing.owner_form_values(billing.get_profile(db, current_user.id), current_user)
    return templates.TemplateResponse("planos_upgrade.html", _upgrade_ctx(request, db, current_user, plan, values=values))


@router.post("/planos/{code}/upgrade", response_class=HTMLResponse)
async def do_upgrade(
    request: Request,
    code: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> Response:
    plan = _plan_or_404(db, code)
    form = await request.form()
    data = {field: str(form.get(field) or "") for field in _FORM_FIELDS}
    profile = billing.get_profile(db, current_user.id)
    try:
        parsed = validate_form(data, has_saved_cpf=bool(profile and profile.cpf_encrypted))
        billing.save_profile(db, current_user, parsed)
        billing.start_upgrade(db, current_user, plan)
    except ValidationError as exc:
        values = {**data, "cpf": "", "cpf_masked": billing.owner_form_values(profile, current_user)["cpf_masked"]}
        return templates.TemplateResponse(
            "planos_upgrade.html",
            _upgrade_ctx(request, db, current_user, plan, values=values, error=str(exc)),
            status_code=422,
        )
    return RedirectResponse(url=f"/planos/{plan.code}/pagamento", status_code=303)


@router.get("/planos/{code}/pagamento", response_class=HTMLResponse)
async def page_payment(
    request: Request,
    code: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> Response:
    plan = _plan_or_404(db, code)
    pending = billing.pending_upgrade(db, current_user.id)
    if pending is None or pending.plan_id != plan.id:
        return RedirectResponse(url="/planos", status_code=303)
    gateway = billing_gateway.get_gateway()
    if gateway is not None:
        checkout = await gateway.create_checkout(
            subscription=pending, user=current_user, plan=plan, return_url=str(request.url_for("page_planos"))
        )
        if checkout.provider_subscription_id:
            pending.provider = gateway.key
            pending.provider_subscription_id = checkout.provider_subscription_id
            db.add(pending)
            db.commit()
        return RedirectResponse(url=checkout.url, status_code=303)
    current = plans.current_plan(db, current_user)
    return templates.TemplateResponse(
        "planos_pagamento.html",
        {
            "request": request, "nav": "planos", "current_user": current_user, "plan": plan, "pending": pending,
            "current_plan": current, "period_label": plans.PERIOD_LABELS.get(plan.billing_period, "mês"),
        },
    )


@router.post("/planos/solicitacao/cancelar")
def cancel_request(db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)) -> RedirectResponse:
    billing.cancel_pending_upgrade(db, current_user)
    return RedirectResponse(url="/planos?ok=" + quote("Solicitação de upgrade cancelada."), status_code=303)


@router.post("/planos/faturamento/remover")
def remove_billing(db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)) -> RedirectResponse:
    try:
        removed = billing.delete_profile(db, current_user)
    except ValidationError as exc:
        return RedirectResponse(url="/planos?error=" + quote(str(exc)), status_code=303)
    if removed:
        billing.cancel_pending_upgrade(db, current_user)
    msg = "Dados de faturamento removidos." if removed else "Não havia dados de faturamento salvos."
    return RedirectResponse(url="/planos?ok=" + quote(msg), status_code=303)


@router.post("/billing/webhook/{provider}")
async def billing_webhook(provider: str, request: Request, db: Session = Depends(get_session)) -> dict:
    """Webhook do gateway. Sem gateway configurado (ou outro provedor): 404."""
    gateway = billing_gateway.get_gateway()
    if gateway is None or gateway.key != provider:
        raise HTTPException(status_code=404, detail="Não encontrado.")
    try:
        events = await gateway.parse_webhook(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Assinatura do webhook inválida.") from exc
    for event in events:
        billing.apply_gateway_event(db, provider, event)
    return {"received": len(events)}
