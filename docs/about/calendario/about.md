# Calendário — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): integração com calendários externos (Google): provedores, conexão OAuth, tokens cifrados, sincronização periódica, eventos e automações que geram mensagens, e a página Calendário (grade mensal, dia, modais de evento/automação, eventos semelhantes, contatos).

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/calendar_service.py`](../../../app/whatsapp_scheduler/calendar_service.py) | Docstring do módulo (não verificada): “Regra de negócio de calendários externos — conexões/calendários/eventos/ automações. Não calcula horário nem cria mensagens por conta própria: o horário vem…” | 36 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/calendar_sync.py`](../../../app/whatsapp_scheduler/calendar_sync.py) | Docstring do módulo (não verificada): “Motor de sincronização com provedores de calendário externos (Google e futuros).” | 17 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/calendar_schemas.py`](../../../app/whatsapp_scheduler/calendar_schemas.py) | Docstring do módulo (não verificada): “DTOs de leitura para calendários externos — mesma convenção de `schemas.py` (`XRead.of(row)`). Nunca incluem token de acesso/atualização, nem cifrado.” | 4 função(ões)/método(s) e 4 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/calendar_providers/__init__.py`](../../../app/whatsapp_scheduler/calendar_providers/__init__.py) | Docstring do módulo (não verificada): “Registro de provedores de calendário por chave (`Calendar.provider`/`CalendarConnection.provider`).” | 3 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/calendar_providers/base.py`](../../../app/whatsapp_scheduler/calendar_providers/base.py) | Docstring do módulo (não verificada): “Interface comum de provedor de calendário.” | 11 função(ões)/método(s) e 7 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/calendar_providers/google.py`](../../../app/whatsapp_scheduler/calendar_providers/google.py) | Docstring do módulo (não verificada): “Provedor Google Calendar: chama a API REST direto via httpx (sem SDK), espelhando o mesmo padrão de `waha.py` (cliente HTTP fino + erro dedicado).” | 32 função(ões)/método(s) e 4 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/calendar_routes.py`](../../../app/whatsapp_scheduler/web/calendar_routes.py) | Docstring do módulo (não verificada): “UI web da página Calendário: grade mensal, modais de evento/automação.” | 42 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/calendario.html`](../../../app/whatsapp_scheduler/web/templates/calendario.html), [`app/whatsapp_scheduler/web/templates/calendario_dia.html`](../../../app/whatsapp_scheduler/web/templates/calendario_dia.html), [`app/whatsapp_scheduler/web/templates/_calendar_month_grid.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_month_grid.html), [`app/whatsapp_scheduler/web/templates/_calendar_day_view.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_day_view.html), [`app/whatsapp_scheduler/web/templates/_calendar_event_modal.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_event_modal.html), [`app/whatsapp_scheduler/web/templates/_calendar_event_detail_modal.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_event_detail_modal.html), [`app/whatsapp_scheduler/web/templates/_calendar_confirm_delete.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_confirm_delete.html), [`app/whatsapp_scheduler/web/templates/_calendar_automation_modal.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_automation_modal.html), [`app/whatsapp_scheduler/web/templates/_calendar_automation_preview.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_automation_preview.html), [`app/whatsapp_scheduler/web/templates/_similar_events_box.html`](../../../app/whatsapp_scheduler/web/templates/_similar_events_box.html), [`app/whatsapp_scheduler/web/templates/_similar_events_checklist.html`](../../../app/whatsapp_scheduler/web/templates/_similar_events_checklist.html), [`app/whatsapp_scheduler/web/templates/_contact_options.html`](../../../app/whatsapp_scheduler/web/templates/_contact_options.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (19; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /calendario` → `page_calendario` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/grid` → `ui_grid` | pendente | pendente | pendente | pendente |
| `GET /calendario/dia` → `page_calendario_dia` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/dia` → `ui_calendario_dia` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/events/new` → `ui_event_new` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/events/{event_id}` → `ui_event_detail` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/events/{event_id}/edit` → `ui_event_edit` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/events/{event_id}/delete-confirm` → `ui_event_delete_confirm` | pendente | pendente | pendente | pendente |
| `POST /ui/calendario/events` → `ui_event_create` | pendente | pendente | pendente | pendente |
| `POST /ui/calendario/events/{event_id}` → `ui_event_update` | pendente | pendente | pendente | pendente |
| `POST /ui/calendario/events/{event_id}/delete` → `ui_event_delete` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/contacts` → `ui_calendario_contacts` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/events/{event_id}/similar-events` → `ui_calendario_similar_events` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/events/{event_id}/automation/new` → `ui_automation_new` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/automations/{automation_id}/edit` → `ui_automation_edit` | pendente | pendente | pendente | pendente |
| `GET /ui/calendario/events/{event_id}/automation-preview` → `ui_automation_preview` | pendente | pendente | pendente | pendente |
| `POST /ui/calendario/events/{event_id}/automation` → `ui_automation_create` | pendente | pendente | pendente | pendente |
| `POST /ui/calendario/automations/{automation_id}` → `ui_automation_update` | pendente | pendente | pendente | pendente |
| `POST /ui/calendario/automations/{automation_id}/remove` → `ui_automation_remove` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Agendamentos](../agendamentos/about.md), [Configurações e Conexões](../configuracoes-conexoes/about.md), [Privacidade](../privacidade/about.md), [API REST](../api/about.md), [Onboarding e Dashboard](../onboarding-dashboard/about.md), [Operação](../operacao/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_calendar_service.py`](../../../app/tests/test_calendar_service.py) | pendente (sem docstring de módulo) (45 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_calendar_sync.py`](../../../app/tests/test_calendar_sync.py) | pendente (sem docstring de módulo) (15 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_calendar_providers.py`](../../../app/tests/test_calendar_providers.py) | pendente (sem docstring de módulo) (13 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_calendar_web.py`](../../../app/tests/test_calendar_web.py) | pendente (sem docstring de módulo) (19 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_calendar_api.py`](../../../app/tests/test_calendar_api.py) | pendente (sem docstring de módulo) (7 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum nesta etapa.
- Pendente: Fluxo OAuth completo (início em configurações, callback, state).
- Pendente: Ciclo de sincronização e tratamento de falha/expiração de token.
- Pendente: Como uma automação vira agendamento (ponte com agendamentos).

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Agendamentos](../agendamentos/about.md), [Configurações e Conexões](../configuracoes-conexoes/about.md), [Privacidade](../privacidade/about.md), [API REST](../api/about.md), [Onboarding e Dashboard](../onboarding-dashboard/about.md), [Operação](../operacao/about.md).
