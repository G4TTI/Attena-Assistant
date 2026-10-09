# WhatsApp e Conversas — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): conexões WhatsApp do usuário (várias por conta) sobre o WAHA — criar, iniciar, QR, renomear, desconectar —, cliente HTTP do WAHA, normalização de destinatário e a tela Conversas (somente visualização), incluindo envio a partir da conversa e o painel "Mensagens programadas". As regras de agendamento usadas pela conversa ficam em agendamentos.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/waha.py`](../../../app/whatsapp_scheduler/waha.py) | Docstring do módulo (não verificada): “Cliente HTTP do WAHA (https://waha.devlike.pro).” | 19 função(ões)/método(s) e 2 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/whatsapp_service.py`](../../../app/whatsapp_scheduler/whatsapp_service.py) | Docstring do módulo (não verificada): “Regra de negócio de conexões WhatsApp (v1.3: um usuário pode ter várias). Equivalente a `calendar_service.py`, mas para `WhatsAppSession` — o cliente WAHA em…” | 18 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/chatsvc.py`](../../../app/whatsapp_scheduler/chatsvc.py) | Docstring do módulo (não verificada): “Conversas do WhatsApp: lista de chats + histórico — SÓ PARA VISUALIZAÇÃO.” | 13 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/recipients.py`](../../../app/whatsapp_scheduler/recipients.py) | Docstring do módulo (não verificada): “Normalização do destinatário para o formato de chatId do WhatsApp/WAHA.” | 1 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/whatsapp_routes.py`](../../../app/whatsapp_scheduler/web/whatsapp_routes.py) | Docstring do módulo (não verificada): “UI web da página WhatsApps: um usuário pode conectar várias sessões (v1.3, item 9-14). O cliente WAHA em si (start/restart/QR/status) é sempre o mesmo `WahaC…” | 10 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/routes.py`](../../../app/whatsapp_scheduler/web/routes.py) | Docstring do módulo (não verificada): “UI web (Jinja2 + htmx, sem build step).” | 56 função(ões)/método(s) e 0 classe(s) no inventário (arquivo inteiro); compartilhado: páginas `/conversas*` e seções "Conversas" e "Conversas: painel “Mensagens programadas”"; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/conversas.html`](../../../app/whatsapp_scheduler/web/templates/conversas.html), [`app/whatsapp_scheduler/web/templates/_chat_list.html`](../../../app/whatsapp_scheduler/web/templates/_chat_list.html), [`app/whatsapp_scheduler/web/templates/_chat_view.html`](../../../app/whatsapp_scheduler/web/templates/_chat_view.html), [`app/whatsapp_scheduler/web/templates/_chat_messages.html`](../../../app/whatsapp_scheduler/web/templates/_chat_messages.html), [`app/whatsapp_scheduler/web/templates/_chat_scheduled.html`](../../../app/whatsapp_scheduler/web/templates/_chat_scheduled.html), [`app/whatsapp_scheduler/web/templates/_scheduled_panel.html`](../../../app/whatsapp_scheduler/web/templates/_scheduled_panel.html), [`app/whatsapp_scheduler/web/templates/_scheduled_panel_list.html`](../../../app/whatsapp_scheduler/web/templates/_scheduled_panel_list.html), [`app/whatsapp_scheduler/web/templates/_whatsapp_list.html`](../../../app/whatsapp_scheduler/web/templates/_whatsapp_list.html), [`app/whatsapp_scheduler/web/templates/_whatsapp_picker_options.html`](../../../app/whatsapp_scheduler/web/templates/_whatsapp_picker_options.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (22; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /conversas` → `page_chats` | pendente | pendente | pendente | pendente |
| `GET /conversas/{session_id}` → `page_chats_session` | pendente | pendente | pendente | pendente |
| `GET /ui/chats/{session_id}` → `ui_chats` | pendente | pendente | pendente | pendente |
| `GET /ui/chats/{session_id}/view` → `ui_chat_view` | pendente | pendente | pendente | pendente |
| `GET /ui/chats/{session_id}/messages` → `ui_chat_messages` | pendente | pendente | pendente | pendente |
| `GET /ui/chats/{session_id}/scheduled` → `ui_chat_scheduled` | pendente | pendente | pendente | pendente |
| `POST /ui/chats/{session_id}/scheduled/{schedule_id}/cancel` → `ui_chat_scheduled_cancel` | pendente | pendente | pendente | pendente |
| `GET /ui/chats/{session_id}/scheduled/panel` → `ui_chat_scheduled_panel` | pendente | pendente | pendente | pendente |
| `GET /ui/chats/{session_id}/scheduled/panel/list` → `ui_chat_scheduled_panel_list` | pendente | pendente | pendente | pendente |
| `POST /ui/chats/{session_id}/scheduled/panel/messages/{schedule_id}/cancel` → `ui_chat_panel_cancel_message` | pendente | pendente | pendente | pendente |
| `POST /ui/chats/{session_id}/scheduled/panel/cancel-selected` → `ui_chat_panel_cancel_selected` | pendente | pendente | pendente | pendente |
| `POST /ui/chats/{session_id}/scheduled/panel/groups/{group_id}/cancel` → `ui_chat_panel_cancel_group` | pendente | pendente | pendente | pendente |
| `POST /ui/chats/{session_id}/send` → `ui_chat_send` | pendente | pendente | pendente | pendente |
| `POST /ui/chats/{session_id}/schedule` → `ui_chat_schedule` | pendente | pendente | pendente | pendente |
| `GET /whatsapps` → `page_whatsapps` | pendente | pendente | pendente | pendente |
| `GET /ui/whatsapps` → `ui_whatsapps` | pendente | pendente | pendente | pendente |
| `GET /ui/whatsapp-picker-options` → `ui_whatsapp_picker_options` | pendente | pendente | pendente | pendente |
| `POST /whatsapps` → `ui_whatsapp_create` | pendente | pendente | pendente | pendente |
| `POST /whatsapps/{session_id}/start` → `ui_whatsapp_start` | pendente | pendente | pendente | pendente |
| `POST /whatsapps/{session_id}/rename` → `ui_whatsapp_rename` | pendente | pendente | pendente | pendente |
| `POST /whatsapps/{session_id}/disconnect` → `ui_whatsapp_disconnect` | pendente | pendente | pendente | pendente |
| `GET /ui/whatsapps/{session_id}/qr` → `ui_whatsapp_qr` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [Agendamentos](../agendamentos/about.md), [API REST](../api/about.md), [Privacidade](../privacidade/about.md), [Onboarding e Dashboard](../onboarding-dashboard/about.md), [Interface](../interface/about.md), [Operação](../operacao/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_waha.py`](../../../app/tests/test_waha.py) | pendente (sem docstring de módulo) (14 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_whatsapp_service.py`](../../../app/tests/test_whatsapp_service.py) | pendente (sem docstring de módulo) (5 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_chats.py`](../../../app/tests/test_chats.py) | pendente (sem docstring de módulo) (13 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_recipients.py`](../../../app/tests/test_recipients.py) | pendente (sem docstring de módulo) (2 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_scheduled_panel.py`](../../../app/tests/test_scheduled_panel.py) | Docstring: “Conversas com muitas mensagens programadas: até 4 aparecem uma a uma, 5 ou mais viram um botão ("Ver mensagens programadas"), canceladas não poluem a convers…” (33 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum nesta etapa.
- Pendente: Contratos HTMX da tela Conversas (polling, targets, seleção em massa).
- Pendente: Cache em memória de conversas e o que o WAHA guarda (ver privacidade).
- Pendente: Estados de sessão WAHA e transições.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [Agendamentos](../agendamentos/about.md), [API REST](../api/about.md), [Privacidade](../privacidade/about.md), [Onboarding e Dashboard](../onboarding-dashboard/about.md), [Interface](../interface/about.md), [Operação](../operacao/about.md).
