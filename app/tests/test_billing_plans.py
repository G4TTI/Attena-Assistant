"""Planos (camada central), upgrade com dados de faturamento pedidos só no
upgrade, faturamento baseado apenas em pagamentos reais."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.conftest import FakeWaha, db_locations_containing, register_and_login, whatsapp_session_id
from whatsapp_scheduler import plans
from whatsapp_scheduler.billing import metrics
from whatsapp_scheduler.billing import service as billing
from whatsapp_scheduler.billing.gateway import GatewayEvent
from whatsapp_scheduler.billing.validation import is_valid_cpf, mask_cpf, validate_form
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.config import settings
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.errors import ValidationError
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import BillingProfile, Payment, PaymentStatus, Subscription, SubscriptionStatus, User

FORM = {
    "full_name": "Maria Oliveira Souza", "cpf": "529.982.247-25", "phone": "(11) 98888-7777",
    "postal_code": "01310-100", "address": "Avenida Paulista", "address_number": "1578",
    "address_complement": "Conj. 42", "city": "São Paulo", "state": "SP",
}


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.user = register_and_login(c, name="Maria", email="maria@example.com")
        yield c


# --------------------------------------------------------------------------- #
# Validações
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cpf,ok", [
    ("529.982.247-25", True), ("52998224725", True), ("111.111.111-11", False), ("529.982.247-24", False),
    ("123", False), ("", False),
])
def test_cpf_validation(cpf, ok):
    assert is_valid_cpf(cpf) is ok


@pytest.mark.parametrize("field,value,message", [
    ("cpf", "111.111.111-11", "CPF inválido"),
    ("postal_code", "123", "CEP inválido"),
    ("state", "XX", "UF"),
    ("full_name", "Maria", "nome completo"),
    ("phone", "123", "Telefone inválido"),
    ("address", "", "endereço"),
])
def test_billing_form_rejects_invalid_values(field, value, message):
    with pytest.raises(ValidationError, match=message):
        validate_form({**FORM, field: value}, has_saved_cpf=False)


def test_mask_cpf():
    assert mask_cpf("25") == "***.***.***-25"


# --------------------------------------------------------------------------- #
# Cadastro continua simples
# --------------------------------------------------------------------------- #
def test_signup_does_not_ask_for_billing_data(client):
    client.cookies.clear()
    page = client.get("/cadastro").text
    for field in ("cpf", "postal_code", "address", "city", "state", "CEP", "CPF"):
        assert f'name="{field}"' not in page
    with Session(get_engine()) as db:
        assert db.exec(select(BillingProfile)).all() == []  # nada é criado no cadastro


# --------------------------------------------------------------------------- #
# Página de planos e upgrade
# --------------------------------------------------------------------------- #
def test_plans_page_shows_current_plan_catalog_and_upgrade(client):
    html = client.get("/planos").text
    assert "Seu plano" in html and "Gratuito" in html and "Plus" in html and "Pro" in html
    assert "Fazer upgrade" in html and "/planos/plus/upgrade" in html
    assert "WhatsApps conectados" in html  # limites vindos da camada central
    assert 'href="/planos"' in html  # item "Planos" na navegação


def test_upgrade_form_is_prefilled_and_payment_is_not_configured(client):
    with Session(get_engine()) as db:
        user = db.get(User, client.user.id)
        user.phone = "(11) 97777-6666"
        db.add(user)
        db.commit()
    form = client.get("/planos/plus/upgrade").text
    assert 'value="Maria"' in form and "(11) 97777-6666" in form and "maria@example.com" in form
    assert 'name="cpf"' in form and 'name="postal_code"' in form and 'name="state"' in form
    assert 'name="password"' not in form  # não pede senha de novo

    r = client.post("/planos/plus/upgrade", data=FORM)
    assert r.status_code == 200 and "Pagamento ainda não configurado" in r.text
    assert "Nada foi cobrado" in r.text
    with Session(get_engine()) as db:
        sub = db.exec(select(Subscription)).one()
        assert sub.status == SubscriptionStatus.incomplete and sub.provider == "none"
        assert plans.current_plan(db, db.get(User, client.user.id)).code == "free"  # continua gratuito
        assert metrics.summary(db).mrr_cents == 0 and metrics.summary(db).upgrade_requests == 1


def test_billing_data_is_encrypted_and_cpf_is_masked(client):
    client.post("/planos/plus/upgrade", data=FORM)
    for needle in ("529.982.247-25", "52998224725", "Avenida Paulista", "01310100", "01310-100", "Conj. 42", "Oliveira Souza"):
        assert db_locations_containing(needle) == [], needle
    with Session(get_engine()) as db:
        profile = db.exec(select(BillingProfile)).one()
        assert profile.cpf_last2 == "25" and profile.state == "SP"
    html = client.get("/planos").text
    assert "***.***.***-25" in html and "529.982.247-25" not in html
    # ao voltar ao formulário, o CPF nunca é reexibido inteiro
    form = client.get("/planos/pro/upgrade").text
    assert "***.***.***-25" in form and "529.982.247-25" not in form and "Avenida Paulista" in form


def test_invalid_upgrade_form_keeps_values_and_creates_nothing(client):
    r = client.post("/planos/plus/upgrade", data={**FORM, "cpf": "000.000.000-00"})
    assert r.status_code == 422 and "CPF inválido" in r.text and "Avenida Paulista" in r.text
    with Session(get_engine()) as db:
        assert db.exec(select(Subscription)).all() == [] and db.exec(select(BillingProfile)).all() == []


def test_cancel_request_and_remove_billing_data(client):
    client.post("/planos/plus/upgrade", data=FORM)
    assert "cancelada" in client.post("/planos/solicitacao/cancelar").text
    r = client.post("/planos/faturamento/remover")
    assert "removidos" in r.text
    with Session(get_engine()) as db:
        assert db.exec(select(BillingProfile)).all() == []
        assert {s.status for s in db.exec(select(Subscription)).all()} == {SubscriptionStatus.cancelled}


def test_other_user_never_sees_my_billing_data(client):
    client.post("/planos/plus/upgrade", data=FORM)
    client.cookies.clear()
    register_and_login(client, name="Outro", email="outro@example.com")
    html = client.get("/planos").text + client.get("/planos/plus/upgrade").text
    assert "***.***.***-25" not in html and "Avenida Paulista" not in html and "Maria Oliveira" not in html
    assert client.get("/planos/plus/pagamento", follow_redirects=False).status_code == 303


def test_webhook_is_404_without_a_gateway(client):
    assert client.post("/billing/webhook/stripe", json={"type": "invoice.paid"}).status_code == 404


# --------------------------------------------------------------------------- #
# Faturamento só com pagamento real
# --------------------------------------------------------------------------- #
def test_revenue_counts_only_confirmed_payments(client):
    with Session(get_engine()) as db:
        user = db.get(User, client.user.id)
        plus = plans.get_plan(db, "plus")
        # 10 usuários no gratuito e nenhum pagamento: faturamento zero (nunca usuários x preço)
        assert metrics.summary(db).revenue_total_cents == 0 and metrics.mrr_cents(db) == 0
        sub = Subscription(user_id=user.id, plan_id=plus.id, amount_cents=2990, provider="gatewayx",
                           provider_subscription_id="sub_1", status=SubscriptionStatus.incomplete)
        db.add(sub)
        db.commit()
        # pagamento pendente/falho não é receita
        billing.apply_gateway_event(db, "gatewayx", GatewayEvent(kind="payment_failed", provider_subscription_id="sub_1",
                                                                 provider_payment_id="pay_0", amount_cents=2990))
        assert metrics.summary(db).revenue_total_cents == 0 and metrics.summary(db).failed_payments == 1
        # confirmado pelo gateway: vira receita e ativa a assinatura
        billing.apply_gateway_event(db, "gatewayx", GatewayEvent(kind="payment_paid", provider_subscription_id="sub_1",
                                                                 provider_payment_id="pay_1", amount_cents=2990))
        billing.apply_gateway_event(db, "gatewayx", GatewayEvent(kind="payment_paid", provider_subscription_id="sub_1",
                                                                 provider_payment_id="pay_1", amount_cents=2990))  # webhook repetido
        summary = metrics.summary(db)
        assert summary.revenue_total_cents == 2990 and summary.mrr_cents == 2990 and summary.active_subscriptions == 1
        assert len(db.exec(select(Payment).where(Payment.status == PaymentStatus.paid)).all()) == 1
        assert plans.current_plan(db, user).code == "plus"
        series = metrics.monthly_revenue(db)
        assert series[-1]["cents"] == 2990 and len(series) == 12


def test_record_payment_refuses_non_gateway_providers(client):
    with Session(get_engine()) as db:
        with pytest.raises(ValueError):
            billing.record_payment(db, user_id=client.user.id, subscription_id=None, amount_cents=100,
                                   status=PaymentStatus.paid, provider="manual", provider_payment_id="x")


# --------------------------------------------------------------------------- #
# Camada central de limites
# --------------------------------------------------------------------------- #
def test_plan_limits_are_central_and_off_by_default(client, monkeypatch):
    sid = whatsapp_session_id(client)
    r = client.post("/whatsapps", data={"name": "Segundo"})
    assert r.status_code == 200 and "permite até" not in r.text  # ENFORCE_PLAN_LIMITS=false: não bloqueia
    monkeypatch.setattr(settings, "enforce_plan_limits", True)
    r = client.post("/whatsapps", data={"name": "Terceiro"})
    assert "permite até 1 whatsapps conectados" in r.text.lower()
    with Session(get_engine()) as db:
        ent = plans.entitlements(db, db.get(User, client.user.id))
        assert ent.plan.code == "free" and ent.limit("whatsapp_connections") == 1
    assert sid
