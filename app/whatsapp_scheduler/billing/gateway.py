"""Interface DESACOPLADA de gateway de pagamento.

Nenhum gateway está implementado ainda — de propósito: o Attena não inventa
pagamento. Com `PAYMENT_PROVIDER` vazio (padrão), `get_gateway()` devolve None,
o fluxo de upgrade para em "Pagamento ainda não configurado" e nenhuma
assinatura é marcada como ativa/paga.

Para plugar um gateway (Stripe, Mercado Pago, Asaas, Pagar.me…):
  1. implemente `PaymentGateway` num módulo novo deste pacote;
  2. registre a classe em `_REGISTRY`;
  3. configure `PAYMENT_PROVIDER=<chave>` + as credenciais DELE no .env.
O checkout (cartão, Pix, boleto) acontece na página do gateway: número de
cartão, CVV e validade nunca passam pelo Attena. O webhook
(`POST /billing/webhook/<chave>`) valida a assinatura do gateway e chama
`service.apply_gateway_event`, o único caminho que ativa uma assinatura ou
registra um pagamento como pago.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from fastapi import Request

from ..config import settings


@dataclass
class CheckoutSession:
    url: str  # página de pagamento do gateway
    provider_subscription_id: str | None = None


@dataclass
class GatewayEvent:
    """Evento já VALIDADO (assinatura do webhook conferida) e normalizado."""

    kind: str  # "payment_paid" | "payment_failed" | "payment_refunded" | "subscription_cancelled" | "subscription_past_due"
    provider_subscription_id: str | None
    provider_payment_id: str | None = None
    amount_cents: int | None = None
    currency: str = "BRL"
    occurred_at: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None


class PaymentGateway(ABC):
    key: str

    @abstractmethod
    async def create_checkout(self, *, subscription, user, plan, return_url: str) -> CheckoutSession:
        """Cria a cobrança no gateway e devolve a URL para onde mandar o usuário."""

    @abstractmethod
    async def parse_webhook(self, request: Request) -> list[GatewayEvent]:
        """Valida a assinatura do webhook (levanta ValueError se inválida) e normaliza os eventos."""


_REGISTRY: dict[str, type[PaymentGateway]] = {}


def get_gateway() -> PaymentGateway | None:
    key = (settings.payment_provider or "").strip().lower()
    if not key:
        return None
    gateway_cls = _REGISTRY.get(key)
    return gateway_cls() if gateway_cls is not None else None


def is_configured() -> bool:
    return get_gateway() is not None
