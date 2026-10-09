# Onboarding e Dashboard — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): primeiros passos (conectar WhatsApp, fuso, concluir/pular), o bloqueio que redireciona usuários ainda em onboarding e a página inicial (Dashboard) com resumo operacional e cartões de WhatsApp/calendário.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/onboarding_service.py`](../../../app/whatsapp_scheduler/onboarding_service.py) | Docstring do módulo (não verificada): “Progresso do onboarding de primeiros passos (v1.3, itens 20-26).” | 4 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/dashboard_service.py`](../../../app/whatsapp_scheduler/dashboard_service.py) | Docstring do módulo (não verificada): “Agregações de dados reais para o Dashboard.” | 14 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/onboarding_routes.py`](../../../app/whatsapp_scheduler/web/onboarding_routes.py) | Docstring do módulo (não verificada): “UI web do onboarding de primeiros passos (v1.3, itens 20-26): WhatsApp -> Google Agenda -> fuso horário -> concluído. Nenhuma etapa bloqueia o uso do app (`m…” | 8 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/dashboard_routes.py`](../../../app/whatsapp_scheduler/web/dashboard_routes.py) | Docstring do módulo (não verificada): “UI web da página Dashboard: resumo operacional (eventos, disparos, status do WhatsApp/Google Agenda, atividade recente). Só leitura + ações que já existem em…” | 7 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/main.py`](../../../app/whatsapp_scheduler/main.py) | Docstring do módulo (não verificada): “Ponto de entrada: FastAPI + poller de agendamento no ciclo de vida do app.” | 9 função(ões)/método(s) e 0 classe(s) no inventário (arquivo inteiro); compartilhado: só `_needs_onboarding` e `_onboarding_gate`; ver arquitetura; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/onboarding.html`](../../../app/whatsapp_scheduler/web/templates/onboarding.html), [`app/whatsapp_scheduler/web/templates/_onboarding_whatsapp_step.html`](../../../app/whatsapp_scheduler/web/templates/_onboarding_whatsapp_step.html), [`app/whatsapp_scheduler/web/templates/dashboard.html`](../../../app/whatsapp_scheduler/web/templates/dashboard.html), [`app/whatsapp_scheduler/web/templates/_dashboard_summary.html`](../../../app/whatsapp_scheduler/web/templates/_dashboard_summary.html), [`app/whatsapp_scheduler/web/templates/_dashboard_whatsapp_card.html`](../../../app/whatsapp_scheduler/web/templates/_dashboard_whatsapp_card.html), [`app/whatsapp_scheduler/web/templates/_dashboard_calendar_card.html`](../../../app/whatsapp_scheduler/web/templates/_dashboard_calendar_card.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (9; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /` → `page_dashboard` | pendente | pendente | pendente | pendente |
| `GET /ui/dashboard/summary` → `ui_dashboard_summary` | pendente | pendente | pendente | pendente |
| `POST /ui/dashboard/calendar-card/sync` → `ui_dashboard_calendar_sync` | pendente | pendente | pendente | pendente |
| `GET /onboarding` → `page_onboarding` | pendente | pendente | pendente | pendente |
| `GET /ui/onboarding/whatsapp` → `ui_onboarding_whatsapp` | pendente | pendente | pendente | pendente |
| `POST /onboarding/whatsapp/start` → `ui_onboarding_whatsapp_start` | pendente | pendente | pendente | pendente |
| `POST /onboarding/timezone` → `ui_onboarding_timezone` | pendente | pendente | pendente | pendente |
| `GET /onboarding/pular` → `ui_onboarding_skip` | pendente | pendente | pendente | pendente |
| `POST /onboarding/finish` → `ui_onboarding_finish` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [WhatsApp e Conversas](../whatsapp-conversas/about.md), [Calendário](../calendario/about.md), [Configurações e Conexões](../configuracoes-conexoes/about.md), [Agendamentos](../agendamentos/about.md), [Interface](../interface/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_onboarding.py`](../../../app/tests/test_onboarding.py) | pendente (sem docstring de módulo) (24 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum nesta etapa.
- Pendente: Quais rotas ficam liberadas durante o onboarding.
- Pendente: Origem e cálculo de cada número do resumo do Dashboard.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [WhatsApp e Conversas](../whatsapp-conversas/about.md), [Calendário](../calendario/about.md), [Configurações e Conexões](../configuracoes-conexoes/about.md), [Agendamentos](../agendamentos/about.md), [Interface](../interface/about.md).
