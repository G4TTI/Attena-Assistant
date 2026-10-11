# WhatsApp e Conversas — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/chatsvc.py`](../../../app/whatsapp_scheduler/chatsvc.py) | 203 |
| [`app/whatsapp_scheduler/recipients.py`](../../../app/whatsapp_scheduler/recipients.py) | 48 |
| [`app/whatsapp_scheduler/waha.py`](../../../app/whatsapp_scheduler/waha.py) | 287 |
| [`app/whatsapp_scheduler/whatsapp_service.py`](../../../app/whatsapp_scheduler/whatsapp_service.py) | 321 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_chats.py`](../../../app/tests/test_chats.py), [`app/tests/test_recipients.py`](../../../app/tests/test_recipients.py), [`app/tests/test_scheduled_panel.py`](../../../app/tests/test_scheduled_panel.py), [`app/tests/test_waha.py`](../../../app/tests/test_waha.py), [`app/tests/test_whatsapp_service.py`](../../../app/tests/test_whatsapp_service.py), [`app/whatsapp_scheduler/web/routes.py`](../../../app/whatsapp_scheduler/web/routes.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/conversas` | `page_chats` | [routes.py:222](../../../app/whatsapp_scheduler/web/routes.py#L222) |
| GET | `/conversas/{session_id}` | `page_chats_session` | [routes.py:234](../../../app/whatsapp_scheduler/web/routes.py#L234) |
| GET | `/ui/chats/{session_id}` | `ui_chats` | [routes.py:622](../../../app/whatsapp_scheduler/web/routes.py#L622) |
| GET | `/ui/chats/{session_id}/view` | `ui_chat_view` | [routes.py:675](../../../app/whatsapp_scheduler/web/routes.py#L675) |
| GET | `/ui/chats/{session_id}/messages` | `ui_chat_messages` | [routes.py:687](../../../app/whatsapp_scheduler/web/routes.py#L687) |
| GET | `/ui/chats/{session_id}/scheduled` | `ui_chat_scheduled` | [routes.py:716](../../../app/whatsapp_scheduler/web/routes.py#L716) |
| POST | `/ui/chats/{session_id}/scheduled/{schedule_id}/cancel` | `ui_chat_scheduled_cancel` | [routes.py:733](../../../app/whatsapp_scheduler/web/routes.py#L733) |
| GET | `/ui/chats/{session_id}/scheduled/panel` | `ui_chat_scheduled_panel` | [routes.py:787](../../../app/whatsapp_scheduler/web/routes.py#L787) |
| GET | `/ui/chats/{session_id}/scheduled/panel/list` | `ui_chat_scheduled_panel_list` | [routes.py:809](../../../app/whatsapp_scheduler/web/routes.py#L809) |
| POST | `/ui/chats/{session_id}/scheduled/panel/messages/{schedule_id}/cancel` | `ui_chat_panel_cancel_message` | [routes.py:829](../../../app/whatsapp_scheduler/web/routes.py#L829) |
| POST | `/ui/chats/{session_id}/scheduled/panel/cancel-selected` | `ui_chat_panel_cancel_selected` | [routes.py:852](../../../app/whatsapp_scheduler/web/routes.py#L852) |
| POST | `/ui/chats/{session_id}/scheduled/panel/groups/{group_id}/cancel` | `ui_chat_panel_cancel_group` | [routes.py:888](../../../app/whatsapp_scheduler/web/routes.py#L888) |
| POST | `/ui/chats/{session_id}/send` | `ui_chat_send` | [routes.py:915](../../../app/whatsapp_scheduler/web/routes.py#L915) |
| POST | `/ui/chats/{session_id}/schedule` | `ui_chat_schedule` | [routes.py:938](../../../app/whatsapp_scheduler/web/routes.py#L938) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `ChatHistory` |  | [chatsvc.py:151](../../../app/whatsapp_scheduler/chatsvc.py#L151) |
| `RecipientError` | ValueError | [recipients.py:16](../../../app/whatsapp_scheduler/recipients.py#L16) |
| `WahaError` | RuntimeError | [waha.py:19](../../../app/whatsapp_scheduler/waha.py#L19) |
| `WahaClient` |  | [waha.py:70](../../../app/whatsapp_scheduler/waha.py#L70) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `purge_expired` |  | [chatsvc.py:49](../../../app/whatsapp_scheduler/chatsvc.py#L49) | Remove da memória toda entrada vencida. Retorna quantas saíram. |
| `forget_session` |  | [chatsvc.py:62](../../../app/whatsapp_scheduler/chatsvc.py#L62) | Descarta tudo em memória de uma sessão (ex.: WhatsApp desconectado). |
| `_fresh_chats` |  | [chatsvc.py:69](../../../app/whatsapp_scheduler/chatsvc.py#L69) |  |
| `cached_chat_name` |  | [chatsvc.py:75](../../../app/whatsapp_scheduler/chatsvc.py#L75) | Nome do contato na lista de conversas AINDA em cache (nunca vai à rede). |
| `_fmt_ts` |  | [chatsvc.py:84](../../../app/whatsapp_scheduler/chatsvc.py#L84) |  |
| `_preview` |  | [chatsvc.py:94](../../../app/whatsapp_scheduler/chatsvc.py#L94) |  |
| `_normalize_chat` |  | [chatsvc.py:103](../../../app/whatsapp_scheduler/chatsvc.py#L103) |  |
| `list_chats` | async | [chatsvc.py:118](../../../app/whatsapp_scheduler/chatsvc.py#L118) |  |
| `_normalize_message` |  | [chatsvc.py:129](../../../app/whatsapp_scheduler/chatsvc.py#L129) |  |
| `get_history` | async | [chatsvc.py:158](../../../app/whatsapp_scheduler/chatsvc.py#L158) | Histórico de uma conversa, direto do WAHA (ou do cache em memória, se ainda fresco). Nunca grava nada. |
| `cached_message_ids` |  | [chatsvc.py:182](../../../app/whatsapp_scheduler/chatsvc.py#L182) |  |
| `send_now` | async | [chatsvc.py:187](../../../app/whatsapp_scheduler/chatsvc.py#L187) | Envio imediato. Nada é gravado: só invalida os caches em memória para a próxima leitura trazer a mensagem do próprio Wha |
| `_msg_id` |  | [chatsvc.py:197](../../../app/whatsapp_scheduler/chatsvc.py#L197) |  |
| `normalize_recipient` |  | [recipients.py:20](../../../app/whatsapp_scheduler/recipients.py#L20) |  |
| `WahaError.__init__` |  | [waha.py:24](../../../app/whatsapp_scheduler/waha.py#L24) |  |
| `_error_reason` |  | [waha.py:33](../../../app/whatsapp_scheduler/waha.py#L33) | Só a 1ª linha do campo de erro da resposta (`exception.message`, `message` ou `error`). O 500 do WAHA ecoa o corpo intei |
| `extract_message_id` |  | [waha.py:52](../../../app/whatsapp_scheduler/waha.py#L52) | O formato do id varia conforme o engine (WEBJS/NOWEB/GOWS). |
| `_video_unsupported` |  | [waha.py:64](../../../app/whatsapp_scheduler/waha.py#L64) | O WAHA recusou o vídeo por limitação do engine/navegador (não por erro do pedido). |
| `WahaClient.__init__` |  | [waha.py:71](../../../app/whatsapp_scheduler/waha.py#L71) |  |
| `WahaClient.aclose` | async | [waha.py:81](../../../app/whatsapp_scheduler/waha.py#L81) |  |
| `WahaClient._request` | async | [waha.py:84](../../../app/whatsapp_scheduler/waha.py#L84) |  |
| `WahaClient.get_session_status` | async | [waha.py:104](../../../app/whatsapp_scheduler/waha.py#L104) |  |
| `WahaClient.get_qr` | async | [waha.py:109](../../../app/whatsapp_scheduler/waha.py#L109) | Retorna (conteúdo, content-type) da imagem de QR. |
| `WahaClient.create_session` | async | [waha.py:114](../../../app/whatsapp_scheduler/waha.py#L114) | Cria (e já inicia) uma sessão que ainda não existe no WAHA. |
| `WahaClient.start_session` | async | [waha.py:133](../../../app/whatsapp_scheduler/waha.py#L133) |  |
| `WahaClient.ensure_session` | async | [waha.py:142](../../../app/whatsapp_scheduler/waha.py#L142) | Status da sessão, criando-a no WAHA se ela ainda não existir (404). |
| `WahaClient.restart_session` | async | [waha.py:165](../../../app/whatsapp_scheduler/waha.py#L165) | Recupera uma sessão travada (ex: status FAILED após o WhatsApp desconectar). |
| `WahaClient.logout_session` | async | [waha.py:186](../../../app/whatsapp_scheduler/waha.py#L186) | Desvincula o aparelho (o WhatsApp do usuário deixa de listar esta sessão). |
| `WahaClient.delete_session` | async | [waha.py:190](../../../app/whatsapp_scheduler/waha.py#L190) | Apaga a sessão no WAHA, incluindo credenciais e os dados locais do engine. |
| `WahaClient.list_sessions` | async | [waha.py:194](../../../app/whatsapp_scheduler/waha.py#L194) | Todas as sessões do WAHA (nome + status). Quem chama NÃO deve repassar o campo `me` (número/nome do perfil) para telas a |
| `WahaClient.send_text` | async | [waha.py:201](../../../app/whatsapp_scheduler/waha.py#L201) |  |
| `WahaClient.send_media` | async | [waha.py:213](../../../app/whatsapp_scheduler/waha.py#L213) | Foto, vídeo, áudio (mensagem de voz) ou documento, com o arquivo em base64 no corpo (nada de URL: o arquivo nunca fica e |
| `WahaClient.get_chats_overview` | async | [waha.py:263](../../../app/whatsapp_scheduler/waha.py#L263) | Lista de conversas com nome, foto e última mensagem. |
| `WahaClient.get_messages` | async | [waha.py:276](../../../app/whatsapp_scheduler/waha.py#L276) | Histórico de uma conversa (mais recentes primeiro no WAHA). |
| `page_chats` | rota, async | [routes.py:223](../../../app/whatsapp_scheduler/web/routes.py#L223) |  |
| `page_chats_session` | rota, async | [routes.py:235](../../../app/whatsapp_scheduler/web/routes.py#L235) |  |
| `_owned_wa_session` |  | [routes.py:589](../../../app/whatsapp_scheduler/web/routes.py#L589) |  |
| `_owned_chat_schedule` |  | [routes.py:596](../../../app/whatsapp_scheduler/web/routes.py#L596) | 404 se a mensagem não for desta conversa (usuário + WhatsApp + chat). |
| `_chats_ctx` | async | [routes.py:604](../../../app/whatsapp_scheduler/web/routes.py#L604) |  |
| `_find_chat` |  | [routes.py:615](../../../app/whatsapp_scheduler/web/routes.py#L615) |  |
| `ui_chats` | rota, async | [routes.py:623](../../../app/whatsapp_scheduler/web/routes.py#L623) |  |
| `_scheduled_ctx` |  | [routes.py:633](../../../app/whatsapp_scheduler/web/routes.py#L633) |  |
| `_chat_schedule_form` |  | [routes.py:640](../../../app/whatsapp_scheduler/web/routes.py#L640) |  |
| `_render_chat_view` | async | [routes.py:646](../../../app/whatsapp_scheduler/web/routes.py#L646) |  |
| `ui_chat_view` | rota, async | [routes.py:676](../../../app/whatsapp_scheduler/web/routes.py#L676) |  |
| `ui_chat_messages` | rota, async | [routes.py:688](../../../app/whatsapp_scheduler/web/routes.py#L688) |  |
| `ui_chat_scheduled` | rota, async | [routes.py:717](../../../app/whatsapp_scheduler/web/routes.py#L717) | Só as mensagens agendadas da conversa (atualizadas sozinhas a cada poucos segundos) — vêm do banco, então aparecem na ho |
| `ui_chat_scheduled_cancel` | rota, async | [routes.py:734](../../../app/whatsapp_scheduler/web/routes.py#L734) | Cancela UMA mensagem agendada (pelo mecanismo de sempre, `service.cancel_schedule`): ela não é enviada e sai da conversa |
| `_chat_label` |  | [routes.py:755](../../../app/whatsapp_scheduler/web/routes.py#L755) | Nome do contato sem ir ao WhatsApp: a lista de conversas em cache, o nome gravado no último agendamento, ou o número. |
| `_panel_ctx` |  | [routes.py:767](../../../app/whatsapp_scheduler/web/routes.py#L767) |  |
| `ui_chat_scheduled_panel` | rota, async | [routes.py:788](../../../app/whatsapp_scheduler/web/routes.py#L788) | Abre o painel (modal). Sem filtro explícito: só as programadas. |
| `ui_chat_scheduled_panel_list` | rota, async | [routes.py:810](../../../app/whatsapp_scheduler/web/routes.py#L810) | Só a lista do painel: troca de filtro, "carregar mais" e a atualização periódica. |
| `ui_chat_panel_cancel_message` | rota, async | [routes.py:830](../../../app/whatsapp_scheduler/web/routes.py#L830) | Cancela UMA mensagem pelo painel — o mesmo `service.cancel_schedule` da conversa. |
| `ui_chat_panel_cancel_selected` | rota, async | [routes.py:853](../../../app/whatsapp_scheduler/web/routes.py#L853) | "Cancelar selecionadas" do painel: as mensagens marcadas, numa transação só (`service.cancel_messages` — as não marcadas |
| `ui_chat_panel_cancel_group` | rota, async | [routes.py:889](../../../app/whatsapp_scheduler/web/routes.py#L889) | "Cancelar todas" de uma sequência — o mesmo `service.cancel_group` da tela Agendamentos. |
| `ui_chat_send` | rota, async | [routes.py:916](../../../app/whatsapp_scheduler/web/routes.py#L916) |  |
| `ui_chat_schedule` | rota, async | [routes.py:939](../../../app/whatsapp_scheduler/web/routes.py#L939) | Agenda UMA sequência de mensagens para esta conversa. Data e horário são o INÍCIO da sequência e são preservados: depois |
| `_sync_label` |  | [routes.py:1005](../../../app/whatsapp_scheduler/web/routes.py#L1005) |  |
| `ensure_first_session` |  | [whatsapp_service.py:20](../../../app/whatsapp_scheduler/whatsapp_service.py#L20) | Cria a primeira `WhatsAppSession` de um usuário reaproveitando `User.waha_session` (nunca gera um `session_name` novo aq |
| `migrate_legacy_sessions` |  | [whatsapp_service.py:39](../../../app/whatsapp_scheduler/whatsapp_service.py#L39) | Idempotente, chamada no boot (main.py lifespan) — mesmo padrão de `calendar_service.migrate_legacy_automations`. Cria, p |
| `list_sessions` |  | [whatsapp_service.py:54](../../../app/whatsapp_scheduler/whatsapp_service.py#L54) |  |
| `primary_session` |  | [whatsapp_service.py:65](../../../app/whatsapp_scheduler/whatsapp_service.py#L65) | A conexão mais antiga ainda ativa do usuário — só um valor-padrão de conveniência pra pré-selecionar em formulários (ex. |
| `get_session` |  | [whatsapp_service.py:76](../../../app/whatsapp_scheduler/whatsapp_service.py#L76) | Sempre valida o dono — nunca retorna a sessão de outro usuário mesmo que o `session_id` exista no banco (proteção contra |
| `session_by_name` |  | [whatsapp_service.py:85](../../../app/whatsapp_scheduler/whatsapp_service.py#L85) | Usada para validar, antes de gravar em `Schedule.session`, que um `session_name` recebido do cliente (formulário/API) re |
| `create_session` |  | [whatsapp_service.py:97](../../../app/whatsapp_scheduler/whatsapp_service.py#L97) |  |
| `rename_session` |  | [whatsapp_service.py:106](../../../app/whatsapp_scheduler/whatsapp_service.py#L106) |  |
| `disconnect_session` |  | [whatsapp_service.py:121](../../../app/whatsapp_scheduler/whatsapp_service.py#L121) | Para novos disparos por esta conexão e cancela mensagens futuras ainda pendentes que a usavam — preserva histórico e men |
| `disconnect_and_purge` | async | [whatsapp_service.py:147](../../../app/whatsapp_scheduler/whatsapp_service.py#L147) | Desconecta no Attena e, em seguida, desloga + apaga a sessão no WAHA (credenciais e dados locais do WhatsApp Web deixam  |
| `status_signature` |  | [whatsapp_service.py:163](../../../app/whatsapp_scheduler/whatsapp_service.py#L163) | Impressão digital curta do que a tela de conexão (onboarding / Configurações → Conexões) MOSTRA: cada WhatsApp, o nome,  |
| `status_rows` | async | [whatsapp_service.py:196](../../../app/whatsapp_scheduler/whatsapp_service.py#L196) | Status ao vivo (nunca cacheado — mesma escolha da sessão única antes) de cada conexão, uma chamada ao WAHA por sessão. U |
| `status_rows._one` | async, aninhada | [whatsapp_service.py:212](../../../app/whatsapp_scheduler/whatsapp_service.py#L212) |  |
| `overall_status` | async | [whatsapp_service.py:223](../../../app/whatsapp_scheduler/whatsapp_service.py#L223) | "ok" \| "pending" \| "error" \| "none" — resumo de todas as conexões num indicador só (dot da sidebar). "ok" se qualquer um |
| `labels_by_session_name` |  | [whatsapp_service.py:237](../../../app/whatsapp_scheduler/whatsapp_service.py#L237) | `Schedule.session` -> nome de exibição, incluindo conexões já desconectadas (histórico antigo ainda precisa mostrar qual |
| `_phone_of` |  | [whatsapp_service.py:261](../../../app/whatsapp_scheduler/whatsapp_service.py#L261) |  |
| `picker_options` | async | [whatsapp_service.py:267](../../../app/whatsapp_scheduler/whatsapp_service.py#L267) | Uma entrada por WhatsApp do usuário, com status pra o seletor. Nunca demora mais que `timeout`: se o WAHA não respondeu, |
| `require_session_ready` | async | [whatsapp_service.py:302](../../../app/whatsapp_scheduler/whatsapp_service.py#L302) | Impede agendar por um WhatsApp desconectado — o erro aparece AGORA, no formulário, e não só quando o envio falhar horas  |

## Templates desta funcionalidade

Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).

| Template | hx-* | Listeners JS | Handlers inline | Polling |
|---|---|---|---|---|
| [`_chat_list.html`](../../../app/whatsapp_scheduler/web/templates/_chat_list.html) | 3 | 0 | 1 | 0 |
| [`_chat_messages.html`](../../../app/whatsapp_scheduler/web/templates/_chat_messages.html) | 0 | 0 | 0 | 0 |
| [`_chat_scheduled.html`](../../../app/whatsapp_scheduler/web/templates/_chat_scheduled.html) | 11 | 0 | 0 | 0 |
| [`_chat_view.html`](../../../app/whatsapp_scheduler/web/templates/_chat_view.html) | 18 | 0 | 8 | 1 |
| [`_scheduled_panel.html`](../../../app/whatsapp_scheduler/web/templates/_scheduled_panel.html) | 8 | 0 | 1 | 0 |
| [`_scheduled_panel_list.html`](../../../app/whatsapp_scheduler/web/templates/_scheduled_panel_list.html) | 20 | 0 | 2 | 1 |
| [`conversas.html`](../../../app/whatsapp_scheduler/web/templates/conversas.html) | 5 | 0 | 2 | 0 |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_chats.py`](../../../app/tests/test_chats.py) — 13 funções: `test_list_chats_normalizes_and_sorts`, `test_get_history_caches_only_in_memory`, `test_history_cache_expires_and_is_removed`, `test_get_history_falls_back_to_memory_on_error`, `test_send_now_persists_nothing`, `test_api_list_chats`, `test_api_messages`, `test_api_chats_404_for_unowned_session`, `test_api_send`, `test_api_send_rejects_empty`, `test_conversas_page_and_partials`, `test_stale_or_foreign_whatsapp_link_opens_own_conversations`, `test_schedule_from_chat_view`
- [`app/tests/test_recipients.py`](../../../app/tests/test_recipients.py) — 2 funções (2 parametrizadas): `test_normalize_recipient`, `test_normalize_recipient_invalid`
- [`app/tests/test_scheduled_panel.py`](../../../app/tests/test_scheduled_panel.py) — 33 funções: `test_1_one_scheduled_message_shows_normally`, `test_2_four_scheduled_messages_show_normally`, `test_3_five_scheduled_messages_become_one_button`, `test_4_ten_scheduled_messages`, `test_5_ten_scheduled_plus_twenty_canceled_do_not_pollute`, `test_6_zero_scheduled_ten_canceled_do_not_pollute`, `test_few_scheduled_plus_many_canceled`, `test_failed_messages_stay_in_the_conversation_even_when_collapsed`, `test_7_button_opens_the_panel`, `test_8_default_filter_shows_only_scheduled`, `test_9_both_filters_show_both`, `test_10_only_canceled_and_no_filter`, `test_11_cancel_one_message_from_the_panel_updates_counters_and_conversation`, `test_cancel_all_from_the_panel_uses_the_existing_group_cancel`, `test_cancel_all_only_for_sequences_with_more_than_one_pending`, `test_12_sent_message_leaves_the_count_and_appears_in_history`, `test_13_new_schedule_increases_the_counter`, `test_14_sequence_order_and_real_times_in_the_panel`, `test_canceled_message_keeps_its_place_and_time_in_the_sequence`, `test_panel_orders_pending_first_then_canceled_most_recent_first`, `test_panel_pages_whole_sequences_and_keeps_the_state_on_refresh`, `test_calendar_automation_messages_follow_the_same_rule`, `test_manual_schedules_follow_the_same_rule`, `test_sql_status_clauses_match_message_status`, `test_panel_never_shows_or_cancels_another_users_messages`, `test_panel_cancel_is_scoped_to_the_open_conversation`, `test_base_pauses_the_panel_refresh_while_a_confirmation_is_open`, `test_panel_offers_selection_only_for_messages_that_can_still_be_canceled`, `test_bulk_cancel_from_the_panel_cancels_only_the_selected`, `test_bulk_cancel_keeps_the_rest_of_each_sequence_sending_in_order`, `test_bulk_cancel_ignores_other_conversations_and_other_users`, `test_agendamentos_bulk_cancel_selected_schedules`, `test_base_keeps_the_selection_across_list_refreshes`
- [`app/tests/test_waha.py`](../../../app/tests/test_waha.py) — 14 funções: `test_send_text_ok`, `test_error_status_becomes_waha_error`, `test_connection_error_becomes_waha_error`, `test_restart_session_uses_restart_endpoint_when_available`, `test_restart_session_falls_back_to_stop_then_start`, `test_restart_session_recovers_even_if_stop_fails`, `test_error_carries_http_status_code`, `test_ensure_session_creates_it_when_missing`, `test_ensure_session_leaves_an_existing_session_alone`, `test_ensure_session_does_not_restart_failed_sessions`, `test_ensure_session_starts_a_stopped_session`, `test_ensure_session_propagates_non_404_errors`, `test_ensure_session_concurrent_calls_create_only_once`, `test_create_session_keeps_noweb_store_off_by_default`
- [`app/tests/test_whatsapp_service.py`](../../../app/tests/test_whatsapp_service.py) — 5 funções: `test_migrate_legacy_sessions_preserves_pairing_and_is_idempotent`, `test_create_list_rename_disconnect`, `test_disconnect_cancels_open_schedules_for_that_session`, `test_ownership_is_enforced_across_users`, `test_status_rows_shows_a_friendly_message_for_a_session_not_created_yet`
