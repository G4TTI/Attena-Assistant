# API REST — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): contratos da API REST em `/api/*` (agendamentos, conexões WhatsApp, conversas, calendário) e os DTOs de resposta. As regras de negócio chamadas pela API são descritas nos domínios correspondentes; não presumir equivalência com as rotas `/ui/*`.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/api/__init__.py`](../../../app/whatsapp_scheduler/api/__init__.py) | pendente | 0 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/api/schedules.py`](../../../app/whatsapp_scheduler/api/schedules.py) | Docstring do módulo (não verificada): “API REST de agendamentos — sempre filtrada pelo dono autenticado.” | 7 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/api/session.py`](../../../app/whatsapp_scheduler/api/session.py) | Docstring do módulo (não verificada): “API REST das conexões WhatsApp do usuário autenticado (v1.3: N por usuário, nunca a de outro — todo id é validado contra o dono antes de qualquer chamada ao…” | 9 função(ões)/método(s) e 2 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/api/chats.py`](../../../app/whatsapp_scheduler/api/chats.py) | Docstring do módulo (não verificada): “API REST de conversas do WhatsApp — sempre de uma conexão (`WhatsAppSession`) do usuário autenticado, nunca a de outro. Só leitura ao vivo: nada do que passa…” | 5 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/api/calendar.py`](../../../app/whatsapp_scheduler/api/calendar.py) | Docstring do módulo (não verificada): “API REST de calendários externos (conexões, calendários, eventos, automações) — sempre filtrada pelo dono autenticado.” | 8 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/schemas.py`](../../../app/whatsapp_scheduler/schemas.py) | Docstring do módulo (não verificada): “DTOs da API REST — sempre campos explícitos, nunca o objeto do ORM inteiro (que carrega ciphertext, hashes etc.). Conteúdo e destinatário só aparecem decifra…” | 2 função(ões)/método(s) e 4 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/calendar_schemas.py`](../../../app/whatsapp_scheduler/calendar_schemas.py) | Docstring do módulo (não verificada): “DTOs de leitura para calendários externos — mesma convenção de `schemas.py` (`XRead.of(row)`). Nunca incluem token de acesso/atualização, nem cifrado.” | 4 função(ões)/método(s) e 4 classe(s) no inventário; pertence a calendario; usado pela API; relações: pendente |

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (23; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /api/calendar/connections` → `list_connections` | pendente | pendente | pendente | pendente |
| `DELETE /api/calendar/connections/{connection_id}` → `disconnect` | pendente | pendente | pendente | pendente |
| `POST /api/calendar/connections/{connection_id}/sync` → `sync_now` | pendente | pendente | pendente | pendente |
| `GET /api/calendar/connections/{connection_id}/calendars` → `list_calendars` | pendente | pendente | pendente | pendente |
| `POST /api/calendar/calendars/{calendar_id}/toggle` → `toggle_calendar` | pendente | pendente | pendente | pendente |
| `GET /api/calendar/events` → `list_events` | pendente | pendente | pendente | pendente |
| `POST /api/calendar/events/{event_id}/automations` → `create_automation` | pendente | pendente | pendente | pendente |
| `DELETE /api/calendar/automations/{automation_id}` → `delete_automation` | pendente | pendente | pendente | pendente |
| `GET /api/whatsapp-sessions/{session_id}/chats` → `chats` | pendente | pendente | pendente | pendente |
| `GET /api/whatsapp-sessions/{session_id}/chats/messages` → `messages` | pendente | pendente | pendente | pendente |
| `POST /api/whatsapp-sessions/{session_id}/chats/send` → `send` | pendente | pendente | pendente | pendente |
| `POST /api/schedules` → `create` | pendente | pendente | pendente | pendente |
| `GET /api/schedules` → `list_schedules` | pendente | pendente | pendente | pendente |
| `GET /api/schedules/{schedule_id}` → `get_schedule` | pendente | pendente | pendente | pendente |
| `DELETE /api/schedules/{schedule_id}` → `delete_schedule` | pendente | pendente | pendente | pendente |
| `POST /api/schedules/{schedule_id}/run-now` → `trigger_now` | pendente | pendente | pendente | pendente |
| `GET /api/whatsapp-sessions` → `list_sessions` | pendente | pendente | pendente | pendente |
| `POST /api/whatsapp-sessions` → `create_session` | pendente | pendente | pendente | pendente |
| `GET /api/whatsapp-sessions/{session_id}` → `session_status` | pendente | pendente | pendente | pendente |
| `GET /api/whatsapp-sessions/{session_id}/qr` → `session_qr` | pendente | pendente | pendente | pendente |
| `POST /api/whatsapp-sessions/{session_id}/start` → `session_start` | pendente | pendente | pendente | pendente |
| `POST /api/whatsapp-sessions/{session_id}/rename` → `rename_session` | pendente | pendente | pendente | pendente |
| `DELETE /api/whatsapp-sessions/{session_id}` → `disconnect_session` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Agendamentos](../agendamentos/about.md), [WhatsApp e Conversas](../whatsapp-conversas/about.md), [Calendário](../calendario/about.md), [Autenticação](../autenticacao/about.md), [Privacidade](../privacidade/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_api.py`](../../../app/tests/test_api.py) | pendente (sem docstring de módulo) (18 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_calendar_api.py`](../../../app/tests/test_calendar_api.py) | pendente (sem docstring de módulo) (7 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum nesta etapa.
- Pendente: Autenticação da API (`auth.require_user_api`) e respostas de erro.
- Pendente: Se a API envia anexos de mídia ou só texto.
- Pendente: Diferenças entre o que a API e a UI permitem.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Agendamentos](../agendamentos/about.md), [WhatsApp e Conversas](../whatsapp-conversas/about.md), [Calendário](../calendario/about.md), [Autenticação](../autenticacao/about.md), [Privacidade](../privacidade/about.md).
