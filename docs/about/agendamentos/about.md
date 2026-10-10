# Agendamentos — about.md

> **Estado: pendente.** Estrutura inicial (etapa 1). Foram conferidos só a existência dos arquivos abaixo no commit-base, as docstrings de módulo e a extração estática de rotas/funções do inventário; itens marcados "Lido" foram confirmados por leitura pontual. Responsabilidades, contratos, regras, dados e testes ainda **não** foram analisados: o escopo é uma proposta de divisão, não um fato sobre o sistema.

## Base e verificação

- Repositório: G4TTI/Attena-Assistant.
- Commit/ref revisado: `ab4ce63a72b8ef1f4cf127a7c5f0ee36b05f4fdc` (`feature/v1.4-criptografia`, commit local ainda sem push). Release de referência `1.4-criptografia` = `ca99e374f3ad2368eb4bd0366ab7fb13a7516d34`; diferença descrita no [índice](../../../about.md).
- Data da revisão: 2026-10-09.
- Método: lista de arquivos do Git, docstrings de módulo e [inventário estático](../INVENTARIO.json) (AST, sem importar o app). Nenhum teste executado.
- Mudanças locais incluídas: nenhuma (árvore de trabalho limpa).
- Estado: pendente — levantamento completo na etapa 2.

## Responsabilidade

Proposta de escopo (a confirmar): modelo único de agendamento (grupo + sequência de mensagens), criação/edição/cancelamento/remarcação, regras de tempo e recorrência, materialização e disparo pelo scheduler, leitura para as telas, códigos de falha e anexos de mídia (foto/vídeo/áudio/PDF, recurso de plano). Inclui a página Agendamentos; Conversas e Calendário usam estas regras.

## Fontes e pontos de entrada

| Arquivo / símbolo | Responsabilidade | Relações |
|---|---|---|
| [`app/whatsapp_scheduler/service.py`](../../../app/whatsapp_scheduler/service.py) | Docstring do módulo (não verificada): “Regras de negócio de AGENDAMENTO — o modelo único usado por Conversas, Agendamentos e Calendário (automações).” | 28 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/schedule_views.py`](../../../app/whatsapp_scheduler/schedule_views.py) | Docstring do módulo (não verificada): “Modelo de LEITURA dos agendamentos — o que as telas mostram.” | 57 função(ões)/método(s) e 5 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/scheduler.py`](../../../app/whatsapp_scheduler/scheduler.py) | Docstring do módulo (não verificada): “O núcleo: comparar "horário agendado <= agora" e disparar via WAHA.” | 17 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/timing.py`](../../../app/whatsapp_scheduler/timing.py) | Docstring do módulo (não verificada): “Regras de TEMPO do agendamento — a única fonte de cálculo de horário.” | 27 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/recurrence.py`](../../../app/whatsapp_scheduler/recurrence.py) | Docstring do módulo (não verificada): “Recorrência: presets amigáveis + cron, e cálculo da próxima ocorrência.” | 5 função(ões)/método(s) e 1 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/failures.py`](../../../app/whatsapp_scheduler/failures.py) | Docstring do módulo (não verificada): “Códigos estáveis de falha de envio + mensagens de erro SANITIZADAS.” | 2 função(ões)/método(s) e 0 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/media.py`](../../../app/whatsapp_scheduler/media.py) | Docstring do módulo (não verificada): “Anexos de mensagens programadas: foto, vídeo, áudio e PDF (recurso de plano).” | 18 função(ões)/método(s) e 2 classe(s) no inventário; relações: pendente |
| [`app/whatsapp_scheduler/web/routes.py`](../../../app/whatsapp_scheduler/web/routes.py) | Docstring do módulo (não verificada): “UI web (Jinja2 + htmx, sem build step).” | 56 função(ões)/método(s) e 0 classe(s) no inventário (arquivo inteiro); compartilhado: página `/agendamentos` e seções "Agendamentos" e "Anexos"; a seção "Contextos e entradas compartilhados" ainda precisa ser dividida; relações: pendente |

Templates: [`app/whatsapp_scheduler/web/templates/schedules.html`](../../../app/whatsapp_scheduler/web/templates/schedules.html), [`app/whatsapp_scheduler/web/templates/_table.html`](../../../app/whatsapp_scheduler/web/templates/_table.html), [`app/whatsapp_scheduler/web/templates/_bulk_bar.html`](../../../app/whatsapp_scheduler/web/templates/_bulk_bar.html), [`app/whatsapp_scheduler/web/templates/_schedule_form.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_form.html), [`app/whatsapp_scheduler/web/templates/_schedule_fields.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_fields.html), [`app/whatsapp_scheduler/web/templates/_schedule_form_response.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_form_response.html), [`app/whatsapp_scheduler/web/templates/_schedule_detail_modal.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_detail_modal.html), [`app/whatsapp_scheduler/web/templates/_schedule_edit_modal.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_edit_modal.html).

## Contratos de telas e APIs

Rotas declaradas atribuídas a este domínio (11; extração estática — arquivo e linha em [ROTAS.md](../ROTAS.md)). Autorização, entrada, saída e efeitos ainda não foram analisados.

| Método / rota ou ação | Autorização | Entrada / validação | Saída / erro | Efeito colateral |
|---|---|---|---|---|
| `GET /agendamentos` → `page_schedules` | pendente | pendente | pendente | pendente |
| `GET /ui/schedules` → `ui_schedules` | pendente | pendente | pendente | pendente |
| `POST /ui/schedules` → `ui_create` | pendente | pendente | pendente | pendente |
| `GET /ui/schedules/{group_id}` → `ui_schedule_detail` | pendente | pendente | pendente | pendente |
| `GET /ui/schedules/{group_id}/edit` → `ui_schedule_edit` | pendente | pendente | pendente | pendente |
| `POST /ui/schedules/{group_id}/edit` → `ui_schedule_update` | pendente | pendente | pendente | pendente |
| `POST /ui/schedules/{group_id}/cancel` → `ui_cancel` | pendente | pendente | pendente | pendente |
| `POST /ui/schedules/cancel-selected` → `ui_cancel_selected` | pendente | pendente | pendente | pendente |
| `POST /ui/schedules/{group_id}/run-now` → `ui_run_now` | pendente | pendente | pendente | pendente |
| `POST /ui/media` → `ui_media_upload` | pendente | pendente | pendente | pendente |
| `GET /ui/media/{media_id}` → `ui_media_file` | pendente | pendente | pendente | pendente |

Contratos HTMX/JavaScript: pendente.

## Funções, fluxo e regras

Pendente. Funções e métodos de cada arquivo estão em [INVENTARIO.json](../INVENTARIO.json) (`functions[]`, filtrar por `file`); na etapa 2, as principais recebem descrição aqui e as auxiliares ficam em tabela com fonte.

## Dados, autorização e dependências

- Tabelas/campos lidos e gravados: pendente.
- Isolamento e papéis: pendente.
- Criptografia/retenção: pendente.
- Integrações/configuração: pendente.
- Dependências compartilhadas (proposta): [WhatsApp e Conversas](../whatsapp-conversas/about.md), [Calendário](../calendario/about.md), [Privacidade](../privacidade/about.md), [Planos e Faturamento](../planos-faturamento/about.md), [Dados e Migrações](../dados-migracoes/about.md), [API REST](../api/about.md), [Interface](../interface/about.md).

## Testes e evidência

| Arquivo / teste | Cenário | Evidência disponível |
|---|---|---|
| [`app/tests/test_scheduling_service.py`](../../../app/tests/test_scheduling_service.py) | Docstring: “Modelo único de agendamento (`ScheduleGroup` + sequência de mensagens): criação, horário preservado, edição, cancelamento, isolamento entre usuários e envio…” (30 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_scheduling_ui.py`](../../../app/tests/test_scheduling_ui.py) | Docstring: “Telas de Agendamentos, Conversas e Calendário sobre o modelo único: formulário limpo, seletores compartilhados, horário preservado, mensagens dentro da conve…” (36 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_scheduler.py`](../../../app/tests/test_scheduler.py) | pendente (sem docstring de módulo) (11 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_timing.py`](../../../app/tests/test_timing.py) | Docstring: “Regras de tempo (`timing.py`) — a única fonte de cálculo de horário do agendamento.” (20 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_recurrence.py`](../../../app/tests/test_recurrence.py) | pendente (sem docstring de módulo) (5 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_media_messages.py`](../../../app/tests/test_media_messages.py) | Docstring: “Agendamento de fotos, vídeos, áudios e PDFs — recurso exclusivo do plano mais caro.” (31 funções `test_*`) | somente listado; não lido nem executado |
| [`app/tests/test_multi_whatsapp_dispatch.py`](../../../app/tests/test_multi_whatsapp_dispatch.py) | Docstring: “v1.3 — prova de que o scheduler nunca mistura sessões WAHA quando um usuário tem múltiplos WhatsApps, e que duas automações do mesmo evento podem sair por nú…” (2 funções `test_*`) | somente listado; não lido nem executado |

Não foi executado: nenhum teste nesta etapa. Pendências de validação: todos os cenários.

## Cuidados e lacunas

- Comportamento confirmado: nenhum além dos itens "Lido" abaixo.
- Lido no diff `ca99e37..ab4ce63`: o único commit posterior à release de referência acrescenta os anexos de mídia (`media.py`, tabela `media_attachments`, `Schedule.media_id`, rotas `/ui/media*`, envio de mídia em `waha.py`, expurgo em `retention.py`, cifra em `privacy.py`).
- Pendente: Estados de `ScheduleGroup`/`Schedule`/`Dispatch` e transições.
- Pendente: Concorrência entre scheduler, edição e cancelamento.
- Validado em ambiente (2026-10-10, WAHA de teste `devlikeapro/waha:chrome-2026.9.2`, engine WEBJS, sessão da conta principal, destinatário = o próprio número): agendamento criado por `service.create_sequence` com foto, PDF, áudio + texto e vídeo (anexos enviados por `media.store_upload`) saiu inteiro pelo scheduler do app na 1ª tentativa, na ordem: foto com legenda, PDF com legenda, áudio, o texto logo depois e o vídeo (todas `sent`, confirmadas pelo WAHA). Antes disso, chamando `WahaClient.send_media` direto para o mesmo número, cada tipo respondeu 201 no endpoint próprio (`sendImage`, `sendFile`, `sendVoice`, `sendVideo` — vídeo sem cair no plano B de documento). Como o arquivo chegou no aparelho (balão de vídeo, mensagem de voz) não foi conferido por mim. O formulário HTTP não foi usado nesse envio (a conta com WhatsApp conectado não tem senha disponível para o teste); upload/formulário/expurgo foram exercitados no navegador em 2026-10-09 com outra conta.
- Validado em ambiente (2026-10-10): com WAHA 2026.8.2 (Chromium) toda mídia falhava com HTTP 500 `Data passed to getter must include an id property` (texto funcionava); a correção é do WAHA (2026.9.1). Requisito: WAHA ≥ 2026.9.1; vídeo no WEBJS exige a variante `:chrome`. Detalhe em [SECURITY_AND_PRIVACY.md §8](../../SECURITY_AND_PRIVACY.md).
- Lido (`waha.py` `_error_reason`/`WahaError.reason`, `failures.classify_waha_error`): falha do WAHA grava em `Dispatch.last_error` o motivo curto dado por ele (só o campo de erro, 1ª linha, sanitizado; o corpo ecoado pelo 500 do WAHA nunca entra). Testado: `tests/test_media_messages.py` (`test_waha_500_keeps_only_the_reason_never_the_echoed_request`, `test_waha_reason_of_a_rejection_is_sanitized`, `test_failed_media_send_records_the_reason`).
- Pendente: envio de mídia para contatos endereçados por LID (problema aberto no WAHA, issue #2273); não exercitado.

## Quando atualizar

Mudanças nos arquivos, símbolos, rotas, templates ou testes listados acima; inclusão/remoção de funções, campos, regras, estados, jobs ou dependências deste domínio; divergência encontrada entre este documento e o código. Siga a [política de documentação](../../DOCUMENTATION_POLICY.md).

Documentos relacionados: [índice](../../../about.md), [WhatsApp e Conversas](../whatsapp-conversas/about.md), [Calendário](../calendario/about.md), [Privacidade](../privacidade/about.md), [Planos e Faturamento](../planos-faturamento/about.md), [Dados e Migrações](../dados-migracoes/about.md), [API REST](../api/about.md), [Interface](../interface/about.md).
