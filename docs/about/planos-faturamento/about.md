# Planos e Faturamento — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): catálogo de planos (preço, período, recursos/capacidades e limites), página Planos e upgrade, dados de faturamento cifrados pedidos só no upgrade, assinaturas/pagamentos, interface de gateway e webhook de pagamento, métricas financeiras usadas pelo admin.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/plans.py`](../../../app/whatsapp_scheduler/plans.py) | Docstring do módulo (não verificada): “Camada central de planos: preço, período, recursos e limites.” | 22 função(ões)/método(s) e 3 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/billing/__init__.py`](../../../app/whatsapp_scheduler/billing/__init__.py) | Docstring do módulo (não verificada): “Faturamento: dados de cobrança (cifrados), assinaturas, pagamentos e a interface desacoplada de gateway. Nenhum dado de cartão passa pelo Attena.” | 0 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/billing/service.py`](../../../app/whatsapp_scheduler/billing/service.py) | Docstring do módulo (não verificada): “Regras de faturamento: perfil de cobrança (cifrado), upgrade, assinaturas e pagamentos. Faturamento = soma de `Payment` com status "paid" vindo do gateway; n…” | 13 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/billing/validation.py`](../../../app/whatsapp_scheduler/billing/validation.py) | Docstring do módulo (não verificada): “Validação dos "Dados para faturamento" (pedidos só no upgrade).” | 9 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/billing/gateway.py`](../../../app/whatsapp_scheduler/billing/gateway.py) | Docstring do módulo (não verificada): “Interface DESACOPLADA de gateway de pagamento.” | 4 função(ões)/método(s) e 3 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/billing/metrics.py`](../../../app/whatsapp_scheduler/billing/metrics.py) | Docstring do módulo (não verificada): “Números financeiros REAIS para o admin.” | 9 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/billing_routes.py`](../../../app/whatsapp_scheduler/web/billing_routes.py) | Docstring do módulo (não verificada): “UI de Planos e upgrade. Dados de faturamento são pedidos SÓ aqui, quando o usuário escolhe um plano pago — nunca no cadastro.” | 10 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/planos.html`](../../../app/whatsapp_scheduler/web/templates/planos.html), [`app/whatsapp_scheduler/web/templates/planos_upgrade.html`](../../../app/whatsapp_scheduler/web/templates/planos_upgrade.html), [`app/whatsapp_scheduler/web/templates/planos_pagamento.html`](../../../app/whatsapp_scheduler/web/templates/planos_pagamento.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (7; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /planos` → `page_planos` | pendente | pendente | pendente | pendente |
| `GET /planos/{code}/upgrade` → `page_upgrade` | pendente | pendente | pendente | pendente |
| `POST /planos/{code}/upgrade` → `do_upgrade` | pendente | pendente | pendente | pendente |
| `GET /planos/{code}/pagamento` → `page_payment` | pendente | pendente | pendente | pendente |
| `POST /planos/solicitacao/cancelar` → `cancel_request` | pendente | pendente | pendente | pendente |
| `POST /planos/faturamento/remover` → `remove_billing` | pendente | pendente | pendente | pendente |
| `POST /billing/webhook/{provider}` → `billing_webhook` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Administração](../administracao/about.md), [Agendamentos](../agendamentos/about.md), [Privacidade](../privacidade/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Interface](../interface/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_billing_plans.py`](../../../app/tests/test_billing_plans.py) | Docstring: “Planos (camada central), upgrade com dados de faturamento pedidos só no upgrade, faturamento baseado apenas em pagamentos reais.” (14 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum nesta etapa.
- Pendente: Qual gateway existe de fato e como o webhook autentica o chamador.
- Pendente: Onde cada limite de plano é aplicado.
- Pendente: Plano interno "Administrador" (ver administracao).

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Administração](../administracao/about.md), [Agendamentos](../agendamentos/about.md), [Privacidade](../privacidade/about.md), [Dados e Migrações](../dados-migracoes/about.md), [Interface](../interface/about.md).
