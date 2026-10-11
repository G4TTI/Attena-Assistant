# Planos e Faturamento — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/billing/__init__.py`](../../../app/whatsapp_scheduler/billing/__init__.py) | 2 |
| [`app/whatsapp_scheduler/billing/gateway.py`](../../../app/whatsapp_scheduler/billing/gateway.py) | 74 |
| [`app/whatsapp_scheduler/billing/metrics.py`](../../../app/whatsapp_scheduler/billing/metrics.py) | 140 |
| [`app/whatsapp_scheduler/billing/service.py`](../../../app/whatsapp_scheduler/billing/service.py) | 304 |
| [`app/whatsapp_scheduler/billing/validation.py`](../../../app/whatsapp_scheduler/billing/validation.py) | 133 |
| [`app/whatsapp_scheduler/plans.py`](../../../app/whatsapp_scheduler/plans.py) | 320 |
| [`app/whatsapp_scheduler/web/billing_routes.py`](../../../app/whatsapp_scheduler/web/billing_routes.py) | 199 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_billing_plans.py`](../../../app/tests/test_billing_plans.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/planos` | `page_planos` | [billing_routes.py:68](../../../app/whatsapp_scheduler/web/billing_routes.py#L68) |
| GET | `/planos/{code}/upgrade` | `page_upgrade` | [billing_routes.py:95](../../../app/whatsapp_scheduler/web/billing_routes.py#L95) |
| POST | `/planos/{code}/upgrade` | `do_upgrade` | [billing_routes.py:112](../../../app/whatsapp_scheduler/web/billing_routes.py#L112) |
| GET | `/planos/{code}/pagamento` | `page_payment` | [billing_routes.py:137](../../../app/whatsapp_scheduler/web/billing_routes.py#L137) |
| POST | `/planos/solicitacao/cancelar` | `cancel_request` | [billing_routes.py:169](../../../app/whatsapp_scheduler/web/billing_routes.py#L169) |
| POST | `/planos/faturamento/remover` | `remove_billing` | [billing_routes.py:175](../../../app/whatsapp_scheduler/web/billing_routes.py#L175) |
| POST | `/billing/webhook/{provider}` | `billing_webhook` | [billing_routes.py:187](../../../app/whatsapp_scheduler/web/billing_routes.py#L187) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `CheckoutSession` |  | [gateway.py:31](../../../app/whatsapp_scheduler/billing/gateway.py#L31) |
| `GatewayEvent` |  | [gateway.py:37](../../../app/whatsapp_scheduler/billing/gateway.py#L37) |
| `PaymentGateway` | ABC | [gateway.py:50](../../../app/whatsapp_scheduler/billing/gateway.py#L50) |
| `FinanceSummary` |  | [metrics.py:63](../../../app/whatsapp_scheduler/billing/metrics.py#L63) |
| `BillingForm` |  | [validation.py:79](../../../app/whatsapp_scheduler/billing/validation.py#L79) |
| `PlanLimitReached` | ValidationError | [plans.py:98](../../../app/whatsapp_scheduler/plans.py#L98) |
| `PlanFeatureUnavailable` | ValidationError | [plans.py:102](../../../app/whatsapp_scheduler/plans.py#L102) |
| `Entitlements` |  | [plans.py:233](../../../app/whatsapp_scheduler/plans.py#L233) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `PaymentGateway.create_checkout` | async | [gateway.py:54](../../../app/whatsapp_scheduler/billing/gateway.py#L54) | Cria a cobrança no gateway e devolve a URL para onde mandar o usuário. |
| `PaymentGateway.parse_webhook` | async | [gateway.py:58](../../../app/whatsapp_scheduler/billing/gateway.py#L58) | Valida a assinatura do webhook (levanta ValueError se inválida) e normaliza os eventos. |
| `get_gateway` |  | [gateway.py:65](../../../app/whatsapp_scheduler/billing/gateway.py#L65) |  |
| `is_configured` |  | [gateway.py:73](../../../app/whatsapp_scheduler/billing/gateway.py#L73) |  |
| `_month_start` |  | [metrics.py:26](../../../app/whatsapp_scheduler/billing/metrics.py#L26) |  |
| `_add_months` |  | [metrics.py:30](../../../app/whatsapp_scheduler/billing/metrics.py#L30) |  |
| `_paid_subscriptions` |  | [metrics.py:35](../../../app/whatsapp_scheduler/billing/metrics.py#L35) |  |
| `mrr_cents` |  | [metrics.py:45](../../../app/whatsapp_scheduler/billing/metrics.py#L45) |  |
| `_paid_sum` |  | [metrics.py:49](../../../app/whatsapp_scheduler/billing/metrics.py#L49) |  |
| `_count_payments` |  | [metrics.py:58](../../../app/whatsapp_scheduler/billing/metrics.py#L58) |  |
| `summary` |  | [metrics.py:77](../../../app/whatsapp_scheduler/billing/metrics.py#L77) |  |
| `monthly_revenue` |  | [metrics.py:117](../../../app/whatsapp_scheduler/billing/metrics.py#L117) | Faturamento pago por mês (mais antigo primeiro), para o gráfico. |
| `plan_stats` |  | [metrics.py:129](../../../app/whatsapp_scheduler/billing/metrics.py#L129) | Por plano: assinantes ativos pagos, cortesias e MRR associado (só pago). |
| `get_profile` |  | [service.py:47](../../../app/whatsapp_scheduler/billing/service.py#L47) |  |
| `masked_summary` |  | [service.py:51](../../../app/whatsapp_scheduler/billing/service.py#L51) | O que o ADMIN pode ver — sem decifrar nada (CPF mascarado, só a UF). |
| `_open` |  | [service.py:64](../../../app/whatsapp_scheduler/billing/service.py#L64) |  |
| `owner_form_values` |  | [service.py:68](../../../app/whatsapp_scheduler/billing/service.py#L68) | Valores do formulário para o PRÓPRIO usuário (decifrados em memória). O CPF nunca volta inteiro: só o mascarado, e o cam |
| `save_profile` |  | [service.py:91](../../../app/whatsapp_scheduler/billing/service.py#L91) |  |
| `delete_profile` |  | [service.py:111](../../../app/whatsapp_scheduler/billing/service.py#L111) | Direito de exclusão: apaga os dados de cobrança se não houver assinatura paga em curso. |
| `pending_upgrade` |  | [service.py:127](../../../app/whatsapp_scheduler/billing/service.py#L127) |  |
| `start_upgrade` |  | [service.py:136](../../../app/whatsapp_scheduler/billing/service.py#L136) | Registra o PEDIDO de upgrade (status "incomplete"). Não dá acesso ao plano nem conta como receita — isso só acontece qua |
| `cancel_pending_upgrade` |  | [service.py:170](../../../app/whatsapp_scheduler/billing/service.py#L170) |  |
| `_end_entitled` |  | [service.py:186](../../../app/whatsapp_scheduler/billing/service.py#L186) |  |
| `grant_plan_manually` |  | [service.py:198](../../../app/whatsapp_scheduler/billing/service.py#L198) | Admin muda o plano à mão (cortesia/teste). Nunca conta como receita: provider "manual", valor 0. Plano gratuito = só enc |
| `record_payment` |  | [service.py:219](../../../app/whatsapp_scheduler/billing/service.py#L219) | Idempotente por (provider, provider_payment_id): o mesmo webhook repetido atualiza o pagamento em vez de duplicar receit |
| `apply_gateway_event` |  | [service.py:256](../../../app/whatsapp_scheduler/billing/service.py#L256) | Aplica um evento JÁ VALIDADO pelo gateway (ver gateway.GatewayEvent). |
| `digits` |  | [validation.py:24](../../../app/whatsapp_scheduler/billing/validation.py#L24) |  |
| `is_valid_cpf` |  | [validation.py:28](../../../app/whatsapp_scheduler/billing/validation.py#L28) | Formato + dígitos verificadores (módulo 11). Rejeita sequências repetidas. |
| `format_cpf` |  | [validation.py:41](../../../app/whatsapp_scheduler/billing/validation.py#L41) |  |
| `mask_cpf` |  | [validation.py:46](../../../app/whatsapp_scheduler/billing/validation.py#L46) |  |
| `format_cep` |  | [validation.py:50](../../../app/whatsapp_scheduler/billing/validation.py#L50) |  |
| `normalize_phone` |  | [validation.py:55](../../../app/whatsapp_scheduler/billing/validation.py#L55) |  |
| `display_phone` |  | [validation.py:66](../../../app/whatsapp_scheduler/billing/validation.py#L66) | "+5511988887777" -> "(11) 98888-7777" (formato nacional, só para exibir ao dono). |
| `_required` |  | [validation.py:91](../../../app/whatsapp_scheduler/billing/validation.py#L91) |  |
| `validate_form` |  | [validation.py:100](../../../app/whatsapp_scheduler/billing/validation.py#L100) |  |
| `seed_default_plans` |  | [plans.py:106](../../../app/whatsapp_scheduler/plans.py#L106) | Idempotente: só cria o catálogo se ainda não existe nenhum plano. |
| `ensure_admin_plan` |  | [plans.py:129](../../../app/whatsapp_scheduler/plans.py#L129) | Idempotente: garante o plano interno "Administrador" (também em bancos que já tinham catálogo). Sempre inativo, oculto e |
| `is_admin_plan` |  | [plans.py:147](../../../app/whatsapp_scheduler/plans.py#L147) |  |
| `features` |  | [plans.py:154](../../../app/whatsapp_scheduler/plans.py#L154) |  |
| `limits` |  | [plans.py:162](../../../app/whatsapp_scheduler/plans.py#L162) |  |
| `capabilities` |  | [plans.py:172](../../../app/whatsapp_scheduler/plans.py#L172) |  |
| `format_price` |  | [plans.py:180](../../../app/whatsapp_scheduler/plans.py#L180) |  |
| `monthly_cents` |  | [plans.py:185](../../../app/whatsapp_scheduler/plans.py#L185) | Valor mensal equivalente (para MRR). |
| `list_plans` |  | [plans.py:190](../../../app/whatsapp_scheduler/plans.py#L190) |  |
| `get_plan` |  | [plans.py:197](../../../app/whatsapp_scheduler/plans.py#L197) |  |
| `default_plan` |  | [plans.py:201](../../../app/whatsapp_scheduler/plans.py#L201) |  |
| `is_paid` |  | [plans.py:206](../../../app/whatsapp_scheduler/plans.py#L206) |  |
| `entitled_subscription` |  | [plans.py:213](../../../app/whatsapp_scheduler/plans.py#L213) | A assinatura que hoje dá direito a um plano (a mais recente, se houver). |
| `current_plan` |  | [plans.py:223](../../../app/whatsapp_scheduler/plans.py#L223) |  |
| `Entitlements.limit` |  | [plans.py:239](../../../app/whatsapp_scheduler/plans.py#L239) |  |
| `entitlements` |  | [plans.py:243](../../../app/whatsapp_scheduler/plans.py#L243) |  |
| `has_capability` |  | [plans.py:253](../../../app/whatsapp_scheduler/plans.py#L253) | O plano atual do usuário libera o recurso `key`? Admins sempre podem. |
| `upgrade_plan_for` |  | [plans.py:261](../../../app/whatsapp_scheduler/plans.py#L261) | O plano mais barato, à venda e visível, que libera `key` (o "assine o X"). |
| `require_capability` |  | [plans.py:269](../../../app/whatsapp_scheduler/plans.py#L269) |  |
| `usage` |  | [plans.py:279](../../../app/whatsapp_scheduler/plans.py#L279) |  |
| `check_limit` |  | [plans.py:301](../../../app/whatsapp_scheduler/plans.py#L301) | Levanta `PlanLimitReached` se `adding` itens a mais estourariam o limite do plano. Com ENFORCE_PLAN_LIMITS=false (padrão |
| `touch` |  | [plans.py:319](../../../app/whatsapp_scheduler/plans.py#L319) |  |
| `_plan_or_404` |  | [billing_routes.py:32](../../../app/whatsapp_scheduler/web/billing_routes.py#L32) |  |
| `_plans_ctx` |  | [billing_routes.py:39](../../../app/whatsapp_scheduler/web/billing_routes.py#L39) |  |
| `page_planos` | rota | [billing_routes.py:69](../../../app/whatsapp_scheduler/web/billing_routes.py#L69) |  |
| `_upgrade_ctx` |  | [billing_routes.py:79](../../../app/whatsapp_scheduler/web/billing_routes.py#L79) |  |
| `page_upgrade` | rota | [billing_routes.py:96](../../../app/whatsapp_scheduler/web/billing_routes.py#L96) |  |
| `do_upgrade` | rota, async | [billing_routes.py:113](../../../app/whatsapp_scheduler/web/billing_routes.py#L113) |  |
| `page_payment` | rota, async | [billing_routes.py:138](../../../app/whatsapp_scheduler/web/billing_routes.py#L138) |  |
| `cancel_request` | rota | [billing_routes.py:170](../../../app/whatsapp_scheduler/web/billing_routes.py#L170) |  |
| `remove_billing` | rota | [billing_routes.py:176](../../../app/whatsapp_scheduler/web/billing_routes.py#L176) |  |
| `billing_webhook` | rota, async | [billing_routes.py:188](../../../app/whatsapp_scheduler/web/billing_routes.py#L188) | Webhook do gateway. Sem gateway configurado (ou outro provedor): 404. |

## Templates desta funcionalidade

Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).

| Template | hx-* | Listeners JS | Handlers inline | Polling |
|---|---|---|---|---|
| [`planos.html`](../../../app/whatsapp_scheduler/web/templates/planos.html) | 0 | 0 | 1 | 0 |
| [`planos_pagamento.html`](../../../app/whatsapp_scheduler/web/templates/planos_pagamento.html) | 0 | 0 | 0 | 0 |
| [`planos_upgrade.html`](../../../app/whatsapp_scheduler/web/templates/planos_upgrade.html) | 0 | 0 | 2 | 0 |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_billing_plans.py`](../../../app/tests/test_billing_plans.py) — 14 funções (2 parametrizadas): `test_cpf_validation`, `test_billing_form_rejects_invalid_values`, `test_mask_cpf`, `test_signup_does_not_ask_for_billing_data`, `test_plans_page_shows_current_plan_catalog_and_upgrade`, `test_upgrade_form_is_prefilled_and_payment_is_not_configured`, `test_billing_data_is_encrypted_and_cpf_is_masked`, `test_invalid_upgrade_form_keeps_values_and_creates_nothing`, `test_cancel_request_and_remove_billing_data`, `test_other_user_never_sees_my_billing_data`, `test_webhook_is_404_without_a_gateway`, `test_revenue_counts_only_confirmed_payments`, `test_record_payment_refuses_non_gateway_providers`, `test_plan_limits_are_central_and_off_by_default`
