# Agendamentos — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/failures.py`](../../../app/whatsapp_scheduler/failures.py) | 68 |
| [`app/whatsapp_scheduler/media.py`](../../../app/whatsapp_scheduler/media.py) | 317 |
| [`app/whatsapp_scheduler/recurrence.py`](../../../app/whatsapp_scheduler/recurrence.py) | 110 |
| [`app/whatsapp_scheduler/schedule_views.py`](../../../app/whatsapp_scheduler/schedule_views.py) | 732 |
| [`app/whatsapp_scheduler/scheduler.py`](../../../app/whatsapp_scheduler/scheduler.py) | 505 |
| [`app/whatsapp_scheduler/schemas.py`](../../../app/whatsapp_scheduler/schemas.py) | 95 |
| [`app/whatsapp_scheduler/service.py`](../../../app/whatsapp_scheduler/service.py) | 802 |
| [`app/whatsapp_scheduler/timing.py`](../../../app/whatsapp_scheduler/timing.py) | 366 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_media_messages.py`](../../../app/tests/test_media_messages.py), [`app/tests/test_multi_whatsapp_dispatch.py`](../../../app/tests/test_multi_whatsapp_dispatch.py), [`app/tests/test_recurrence.py`](../../../app/tests/test_recurrence.py), [`app/tests/test_scheduler.py`](../../../app/tests/test_scheduler.py), [`app/tests/test_scheduling_service.py`](../../../app/tests/test_scheduling_service.py), [`app/tests/test_scheduling_ui.py`](../../../app/tests/test_scheduling_ui.py), [`app/tests/test_timing.py`](../../../app/tests/test_timing.py), [`app/whatsapp_scheduler/web/routes.py`](../../../app/whatsapp_scheduler/web/routes.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/agendamentos` | `page_schedules` | [routes.py:209](../../../app/whatsapp_scheduler/web/routes.py#L209) |
| GET | `/ui/schedules` | `ui_schedules` | [routes.py:280](../../../app/whatsapp_scheduler/web/routes.py#L280) |
| POST | `/ui/schedules` | `ui_create` | [routes.py:303](../../../app/whatsapp_scheduler/web/routes.py#L303) |
| GET | `/ui/schedules/{group_id}` | `ui_schedule_detail` | [routes.py:383](../../../app/whatsapp_scheduler/web/routes.py#L383) |
| GET | `/ui/schedules/{group_id}/edit` | `ui_schedule_edit` | [routes.py:418](../../../app/whatsapp_scheduler/web/routes.py#L418) |
| POST | `/ui/schedules/{group_id}/edit` | `ui_schedule_update` | [routes.py:439](../../../app/whatsapp_scheduler/web/routes.py#L439) |
| POST | `/ui/schedules/{group_id}/cancel` | `ui_cancel` | [routes.py:476](../../../app/whatsapp_scheduler/web/routes.py#L476) |
| POST | `/ui/schedules/cancel-selected` | `ui_cancel_selected` | [routes.py:487](../../../app/whatsapp_scheduler/web/routes.py#L487) |
| POST | `/ui/schedules/{group_id}/run-now` | `ui_run_now` | [routes.py:507](../../../app/whatsapp_scheduler/web/routes.py#L507) |
| POST | `/ui/media` | `ui_media_upload` | [routes.py:525](../../../app/whatsapp_scheduler/web/routes.py#L525) |
| GET | `/ui/media/{media_id}` | `ui_media_file` | [routes.py:568](../../../app/whatsapp_scheduler/web/routes.py#L568) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `MediaUnavailable` | RuntimeError | [media.py:76](../../../app/whatsapp_scheduler/media.py#L76) |
| `MediaInfo` |  | [media.py:268](../../../app/whatsapp_scheduler/media.py#L268) |
| `RecurrenceError` | ValueError | [recurrence.py:30](../../../app/whatsapp_scheduler/recurrence.py#L30) |
| `MessageView` |  | [schedule_views.py:88](../../../app/whatsapp_scheduler/schedule_views.py#L88) |
| `GroupView` |  | [schedule_views.py:141](../../../app/whatsapp_scheduler/schedule_views.py#L141) |
| `ConversationScheduled` |  | [schedule_views.py:438](../../../app/whatsapp_scheduler/schedule_views.py#L438) |
| `PanelGroup` |  | [schedule_views.py:548](../../../app/whatsapp_scheduler/schedule_views.py#L548) |
| `ScheduledPanel` |  | [schedule_views.py:576](../../../app/whatsapp_scheduler/schedule_views.py#L576) |
| `SchedulerService` |  | [scheduler.py:451](../../../app/whatsapp_scheduler/scheduler.py#L451) |
| `ScheduleCreate` | BaseModel | [schemas.py:15](../../../app/whatsapp_scheduler/schemas.py#L15) |
| `DispatchRead` | BaseModel | [schemas.py:25](../../../app/whatsapp_scheduler/schemas.py#L25) |
| `ScheduleRead` | BaseModel | [schemas.py:49](../../../app/whatsapp_scheduler/schemas.py#L49) |
| `SessionInfo` | BaseModel | [schemas.py:92](../../../app/whatsapp_scheduler/schemas.py#L92) |
| `MessageItem` |  | [service.py:93](../../../app/whatsapp_scheduler/service.py#L93) |
| `OffsetRule` |  | [timing.py:212](../../../app/whatsapp_scheduler/timing.py#L212) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `sanitize` |  | [failures.py:49](../../../app/whatsapp_scheduler/failures.py#L49) |  |
| `classify_waha_error` |  | [failures.py:55](../../../app/whatsapp_scheduler/failures.py#L55) | (código, mensagem segura) de uma falha ao enviar pelo WAHA. |
| `sniff` |  | [media.py:83](../../../app/whatsapp_scheduler/media.py#L83) | (tipo, mimetype) a partir da assinatura do arquivo; None = não aceito. `declared` (o que o navegador disse) só desempata |
| `clean_filename` |  | [media.py:118](../../../app/whatsapp_scheduler/media.py#L118) | Só o nome (sem pasta), sem caracteres de controle, com a extensão do tipo REAL. |
| `size_label` |  | [media.py:127](../../../app/whatsapp_scheduler/media.py#L127) |  |
| `max_size_label` |  | [media.py:133](../../../app/whatsapp_scheduler/media.py#L133) |  |
| `media_root` |  | [media.py:140](../../../app/whatsapp_scheduler/media.py#L140) |  |
| `_path` |  | [media.py:146](../../../app/whatsapp_scheduler/media.py#L146) |  |
| `_write` |  | [media.py:153](../../../app/whatsapp_scheduler/media.py#L153) |  |
| `delete_file` |  | [media.py:164](../../../app/whatsapp_scheduler/media.py#L164) |  |
| `load_bytes` |  | [media.py:173](../../../app/whatsapp_scheduler/media.py#L173) | Conteúdo DECIFRADO do anexo — só para enviar ao WAHA ou mostrar ao dono. |
| `rotate_file` |  | [media.py:184](../../../app/whatsapp_scheduler/media.py#L184) | Recifra arquivo + nome com a chave ativa (`cli rotate-keys`). O arquivo novo vai para OUTRO nome e a linha passa a apont |
| `_draft_count` |  | [media.py:206](../../../app/whatsapp_scheduler/media.py#L206) |  |
| `store_upload` |  | [media.py:219](../../../app/whatsapp_scheduler/media.py#L219) | Valida, cifra e grava um anexo novo (ainda sem mensagem). Levanta `ValidationError` com o texto que vai pra tela. |
| `resolve_for_user` |  | [media.py:248](../../../app/whatsapp_scheduler/media.py#L248) | Os anexos pedidos, conferindo dono e se ainda existem. Id de outro usuário responde igual a id inexistente. |
| `MediaInfo.available` |  | [media.py:277](../../../app/whatsapp_scheduler/media.py#L277) |  |
| `MediaInfo.is_image` |  | [media.py:281](../../../app/whatsapp_scheduler/media.py#L281) |  |
| `info` |  | [media.py:285](../../../app/whatsapp_scheduler/media.py#L285) |  |
| `infos` |  | [media.py:297](../../../app/whatsapp_scheduler/media.py#L297) |  |
| `attach_config` |  | [media.py:307](../../../app/whatsapp_scheduler/media.py#L307) | O que o formulário precisa pra mostrar o botão de anexo (ou o convite pro plano). |
| `parse_hhmm` |  | [recurrence.py:34](../../../app/whatsapp_scheduler/recurrence.py#L34) | "HH:MM" -> (hora, minuto), validado. Reaproveitado fora deste módulo (ex.: horário personalizado de automação em calenda |
| `normalize_recurrence` |  | [recurrence.py:46](../../../app/whatsapp_scheduler/recurrence.py#L46) | Converte presets em uma expressão cron de 5 campos. Cron entra e sai igual. |
| `local_to_utc` |  | [recurrence.py:95](../../../app/whatsapp_scheduler/recurrence.py#L95) |  |
| `utc_to_local` |  | [recurrence.py:100](../../../app/whatsapp_scheduler/recurrence.py#L100) |  |
| `next_run_utc` |  | [recurrence.py:105](../../../app/whatsapp_scheduler/recurrence.py#L105) | Próxima ocorrência do cron estritamente após `after_utc` (naive UTC). |
| `MessageView.position` |  | [schedule_views.py:98](../../../app/whatsapp_scheduler/schedule_views.py#L98) |  |
| `MessageView.text` |  | [schedule_views.py:102](../../../app/whatsapp_scheduler/schedule_views.py#L102) | Decifrado em memória só para o dono ver; None = já expurgado (retenção). |
| `MessageView.content_removed` |  | [schedule_views.py:107](../../../app/whatsapp_scheduler/schedule_views.py#L107) |  |
| `MessageView.summary` |  | [schedule_views.py:111](../../../app/whatsapp_scheduler/schedule_views.py#L111) | Uma linha pra rótulos/aria: o texto, ou "Foto: nome.jpg" sem texto. |
| `MessageView.error` |  | [schedule_views.py:120](../../../app/whatsapp_scheduler/schedule_views.py#L120) |  |
| `MessageView.attempts` |  | [schedule_views.py:124](../../../app/whatsapp_scheduler/schedule_views.py#L124) |  |
| `MessageView.label` |  | [schedule_views.py:128](../../../app/whatsapp_scheduler/schedule_views.py#L128) |  |
| `MessageView.icon` |  | [schedule_views.py:132](../../../app/whatsapp_scheduler/schedule_views.py#L132) |  |
| `MessageView.can_cancel` |  | [schedule_views.py:136](../../../app/whatsapp_scheduler/schedule_views.py#L136) |  |
| `GroupView.id` |  | [schedule_views.py:154](../../../app/whatsapp_scheduler/schedule_views.py#L154) |  |
| `GroupView.recipient_info` |  | [schedule_views.py:158](../../../app/whatsapp_scheduler/schedule_views.py#L158) |  |
| `GroupView.recipient` |  | [schedule_views.py:162](../../../app/whatsapp_scheduler/schedule_views.py#L162) | Nome do contato; sem nome, o número formatado ("5511999998888@c.us" -> "+5511999998888"). Depois que o agendamento termi |
| `GroupView.chat_id` |  | [schedule_views.py:169](../../../app/whatsapp_scheduler/schedule_views.py#L169) |  |
| `GroupView.is_group_chat` |  | [schedule_views.py:174](../../../app/whatsapp_scheduler/schedule_views.py#L174) |  |
| `GroupView.recipient_phone` |  | [schedule_views.py:178](../../../app/whatsapp_scheduler/schedule_views.py#L178) |  |
| `GroupView.label` |  | [schedule_views.py:183](../../../app/whatsapp_scheduler/schedule_views.py#L183) |  |
| `GroupView.pill` |  | [schedule_views.py:187](../../../app/whatsapp_scheduler/schedule_views.py#L187) | Classe CSS de `.pill` (já existentes em base.html). |
| `GroupView.is_open` |  | [schedule_views.py:194](../../../app/whatsapp_scheduler/schedule_views.py#L194) |  |
| `GroupView.message_count` |  | [schedule_views.py:198](../../../app/whatsapp_scheduler/schedule_views.py#L198) |  |
| `GroupView.is_recurring` |  | [schedule_views.py:202](../../../app/whatsapp_scheduler/schedule_views.py#L202) |  |
| `GroupView.can_cancel` |  | [schedule_views.py:206](../../../app/whatsapp_scheduler/schedule_views.py#L206) |  |
| `message_status` |  | [schedule_views.py:213](../../../app/whatsapp_scheduler/schedule_views.py#L213) | (status, dispatch que o representa). Uma dispatch aberta (pending/ processing) sempre manda — é o que vai acontecer; sen |
| `_dispatch_exists` |  | [schedule_views.py:232](../../../app/whatsapp_scheduler/schedule_views.py#L232) |  |
| `open_clause` |  | [schedule_views.py:236](../../../app/whatsapp_scheduler/schedule_views.py#L236) | `message_status(...) in ("scheduled", "sending")` em SQL, pra contar sem carregar as linhas: tem dispatch aberta, ou ain |
| `canceled_clause` |  | [schedule_views.py:245](../../../app/whatsapp_scheduler/schedule_views.py#L245) | `message_status(...) == "canceled"` em SQL: nenhuma dispatch aberta e (desativada sem nunca ter tido dispatch, ou a ÚLTI |
| `group_status` |  | [schedule_views.py:266](../../../app/whatsapp_scheduler/schedule_views.py#L266) | Status do agendamento inteiro a partir das mensagens dele. |
| `_attach_media` |  | [schedule_views.py:282](../../../app/whatsapp_scheduler/schedule_views.py#L282) | Uma consulta para os anexos de todas as mensagens listadas. |
| `_message_view` |  | [schedule_views.py:290](../../../app/whatsapp_scheduler/schedule_views.py#L290) |  |
| `_is_editable` |  | [schedule_views.py:303](../../../app/whatsapp_scheduler/schedule_views.py#L303) | Mesma regra de `service.update_sequence`: só antes de qualquer envio. |
| `_chunks` |  | [schedule_views.py:317](../../../app/whatsapp_scheduler/schedule_views.py#L317) |  |
| `_load_schedules` |  | [schedule_views.py:322](../../../app/whatsapp_scheduler/schedule_views.py#L322) |  |
| `_load_dispatches` |  | [schedule_views.py:332](../../../app/whatsapp_scheduler/schedule_views.py#L332) |  |
| `_build_group_views` |  | [schedule_views.py:340](../../../app/whatsapp_scheduler/schedule_views.py#L340) |  |
| `list_group_views` |  | [schedule_views.py:376](../../../app/whatsapp_scheduler/schedule_views.py#L376) | Agendamentos do usuário: os abertos primeiro (o mais próximo no topo), depois os últimos encerrados (o mais recente prim |
| `get_group_view` |  | [schedule_views.py:408](../../../app/whatsapp_scheduler/schedule_views.py#L408) |  |
| `_chat_scope` |  | [schedule_views.py:419](../../../app/whatsapp_scheduler/schedule_views.py#L419) | Uma conversa = (usuário, WhatsApp, chat). Toda consulta daqui passa por isso — pelo HASH do destinatário, o número não e |
| `_count` |  | [schedule_views.py:429](../../../app/whatsapp_scheduler/schedule_views.py#L429) |  |
| `_by_time` |  | [schedule_views.py:433](../../../app/whatsapp_scheduler/schedule_views.py#L433) |  |
| `ConversationScheduled.open_count` |  | [schedule_views.py:462](../../../app/whatsapp_scheduler/schedule_views.py#L462) |  |
| `ConversationScheduled.collapsed` |  | [schedule_views.py:466](../../../app/whatsapp_scheduler/schedule_views.py#L466) |  |
| `ConversationScheduled.inline_items` |  | [schedule_views.py:470](../../../app/whatsapp_scheduler/schedule_views.py#L470) |  |
| `ConversationScheduled.next_open` |  | [schedule_views.py:475](../../../app/whatsapp_scheduler/schedule_views.py#L475) |  |
| `ConversationScheduled.show_canceled_link` |  | [schedule_views.py:479](../../../app/whatsapp_scheduler/schedule_views.py#L479) |  |
| `conversation_scheduled` |  | [schedule_views.py:483](../../../app/whatsapp_scheduler/schedule_views.py#L483) | Mensagens agendadas desta conversa, para aparecerem DENTRO dela (ver `ConversationScheduled`). Roda a cada poucos segund |
| `chat_recipient_name` |  | [schedule_views.py:529](../../../app/whatsapp_scheduler/schedule_views.py#L529) | Nome do contato como ficou num agendamento ainda ativo desta conversa (sem ir ao WhatsApp). |
| `PanelGroup.id` |  | [schedule_views.py:558](../../../app/whatsapp_scheduler/schedule_views.py#L558) |  |
| `PanelGroup.source_label` |  | [schedule_views.py:562](../../../app/whatsapp_scheduler/schedule_views.py#L562) |  |
| `PanelGroup.can_cancel_all` |  | [schedule_views.py:566](../../../app/whatsapp_scheduler/schedule_views.py#L566) |  |
| `PanelGroup.time_format` |  | [schedule_views.py:570](../../../app/whatsapp_scheduler/schedule_views.py#L570) | As mensagens de uma sequência saem com segundos de diferença: aí os segundos aparecem. |
| `ScheduledPanel.no_filter` |  | [schedule_views.py:589](../../../app/whatsapp_scheduler/schedule_views.py#L589) |  |
| `ScheduledPanel.selectable` |  | [schedule_views.py:593](../../../app/whatsapp_scheduler/schedule_views.py#L593) | Alguma mensagem da página pode ser marcada pra cancelar em massa. |
| `ScheduledPanel.can_load_more` |  | [schedule_views.py:598](../../../app/whatsapp_scheduler/schedule_views.py#L598) |  |
| `ScheduledPanel.next_limit` |  | [schedule_views.py:602](../../../app/whatsapp_scheduler/schedule_views.py#L602) |  |
| `ScheduledPanel.params` |  | [schedule_views.py:605](../../../app/whatsapp_scheduler/schedule_views.py#L605) | Estado do painel (filtros + quanto já carregou) — acompanha toda requisição dele. |
| `_event_titles` |  | [schedule_views.py:617](../../../app/whatsapp_scheduler/schedule_views.py#L617) | Título do evento de cada agendamento criado por uma automação do Calendário. |
| `scheduled_panel` |  | [schedule_views.py:636](../../../app/whatsapp_scheduler/schedule_views.py#L636) | Mensagens programadas e/ou canceladas de UMA conversa, agrupadas por agendamento (cada sequência na sua ordem). O filtro |
| `scheduled_panel.next_open` | aninhada | [schedule_views.py:680](../../../app/whatsapp_scheduler/schedule_views.py#L680) |  |
| `_dependency_gate` |  | [scheduler.py:37](../../../app/whatsapp_scheduler/scheduler.py#L37) | "wait" \| "proceed" \| "abort" — trava genérica de ordem entre schedules encadeados (mensagens de uma automação). Sem depe |
| `_compute_next_utc` |  | [scheduler.py:75](../../../app/whatsapp_scheduler/scheduler.py#L75) | Quando deve acontecer a próxima ocorrência desta regra? None = nunca mais. |
| `_materialize_schedule` |  | [scheduler.py:90](../../../app/whatsapp_scheduler/scheduler.py#L90) | `known_open`: ids de schedules que o chamador já sabe (numa consulta só) terem dispatch aberta — evita 1 consulta por re |
| `_recover_stuck` |  | [scheduler.py:139](../../../app/whatsapp_scheduler/scheduler.py#L139) |  |
| `_waiting_on_open_chain` |  | [scheduler.py:156](../../../app/whatsapp_scheduler/scheduler.py#L156) | True se a cadeia desta mensagem está travada numa antecessora ATIVA que ainda tem dispatch aberta (direta ou mais atrás  |
| `materialize_due` |  | [scheduler.py:171](../../../app/whatsapp_scheduler/scheduler.py#L171) | Sync — roda em thread separada a partir do loop. |
| `materialize_one` |  | [scheduler.py:199](../../../app/whatsapp_scheduler/scheduler.py#L199) | Materializa uma única regra usando uma sessão já aberta (usado pela API). |
| `_backoff_seconds` |  | [scheduler.py:209](../../../app/whatsapp_scheduler/scheduler.py#L209) |  |
| `dispatch_due` | async | [scheduler.py:214](../../../app/whatsapp_scheduler/scheduler.py#L214) | Envia todas as dispatches vencidas. Retorna quantas foram efetivamente enviadas. |
| `_end_if_one_shot` |  | [scheduler.py:255](../../../app/whatsapp_scheduler/scheduler.py#L255) | Uma mensagem de disparo único chegou a um estado final: a regra termina agora (não no próximo tick) e o conteúdo cifrado |
| `_finish_without_sending` |  | [scheduler.py:270](../../../app/whatsapp_scheduler/scheduler.py#L270) |  |
| `_send_one` | async | [scheduler.py:285](../../../app/whatsapp_scheduler/scheduler.py#L285) |  |
| `SchedulerService.__init__` |  | [scheduler.py:452](../../../app/whatsapp_scheduler/scheduler.py#L452) |  |
| `SchedulerService.start` | async | [scheduler.py:457](../../../app/whatsapp_scheduler/scheduler.py#L457) |  |
| `SchedulerService.stop` | async | [scheduler.py:463](../../../app/whatsapp_scheduler/scheduler.py#L463) |  |
| `SchedulerService.run_once` | async | [scheduler.py:472](../../../app/whatsapp_scheduler/scheduler.py#L472) | Um tick. Repete enquanto algo foi enviado: a mensagem N+1 de uma sequência só materializa depois que a N é confirmada co |
| `SchedulerService._run` | async | [scheduler.py:490](../../../app/whatsapp_scheduler/scheduler.py#L490) |  |
| `DispatchRead.of` |  | [schemas.py:36](../../../app/whatsapp_scheduler/schemas.py#L36) |  |
| `ScheduleRead.of` |  | [schemas.py:68](../../../app/whatsapp_scheduler/schemas.py#L68) |  |
| `clean_messages` |  | [service.py:79](../../../app/whatsapp_scheduler/service.py#L79) | Tira espaços, descarta vazias e valida quantidade/tamanho. |
| `clean_items` |  | [service.py:100](../../../app/whatsapp_scheduler/service.py#L100) | Como `clean_messages`, com o anexo de cada mensagem (`media_ids[i]` é o da `messages[i]`; vazio = sem anexo). Mensagem s |
| `_resolve_media` |  | [service.py:119](../../../app/whatsapp_scheduler/service.py#L119) | Confere os anexos (dono, ainda existem, plano libera) e devolve a sequência final + se algum áudio com texto foi dividid |
| `_prepare_items` |  | [service.py:141](../../../app/whatsapp_scheduler/service.py#L141) |  |
| `_normalize_cron` |  | [service.py:153](../../../app/whatsapp_scheduler/service.py#L153) |  |
| `_normalize_chat` |  | [service.py:167](../../../app/whatsapp_scheduler/service.py#L167) |  |
| `_check_attempts` |  | [service.py:174](../../../app/whatsapp_scheduler/service.py#L174) |  |
| `_resolve_start` |  | [service.py:179](../../../app/whatsapp_scheduler/service.py#L179) | (horário de parede, UTC) do início — datas extremas viram erro de validação, não 500. |
| `_recent_identical_group` |  | [service.py:194](../../../app/whatsapp_scheduler/service.py#L194) |  |
| `_chain_dependencies` |  | [service.py:216](../../../app/whatsapp_scheduler/service.py#L216) |  |
| `create_sequence` |  | [service.py:221](../../../app/whatsapp_scheduler/service.py#L221) | Cria UM agendamento (grupo) com a sequência inteira, numa transação só. |
| `create_schedule` |  | [service.py:318](../../../app/whatsapp_scheduler/service.py#L318) | Agendamento de UMA mensagem (API REST e chamadas simples): um grupo de 1. |
| `get_group` |  | [service.py:350](../../../app/whatsapp_scheduler/service.py#L350) | Sempre valida o dono — nunca devolve o agendamento de outro usuário. |
| `group_schedules` |  | [service.py:358](../../../app/whatsapp_scheduler/service.py#L358) |  |
| `_apply_cancel` |  | [service.py:369](../../../app/whatsapp_scheduler/service.py#L369) | Cancela a mensagem. Quem chama expurga o conteúdo com `retention.finalize_schedules` antes do commit (cancelada = não pr |
| `_rewire_dependents` |  | [service.py:388](../../../app/whatsapp_scheduler/service.py#L388) | Uma mensagem do MEIO da sequência foi cancelada de propósito pelo usuário: as seguintes passam a esperar a anterior à ca |
| `cancel_schedule` |  | [service.py:404](../../../app/whatsapp_scheduler/service.py#L404) | Cancela UMA mensagem agendada (a de uma conversa, a da API). As mensagens seguintes da mesma sequência continuam valendo |
| `cancel_schedules` |  | [service.py:424](../../../app/whatsapp_scheduler/service.py#L424) | Cancela VÁRIAS mensagens numa transação só (grupo inteiro, cascata de desconexão/exclusão). Sem religar dependências: tu |
| `cancel_group` |  | [service.py:445](../../../app/whatsapp_scheduler/service.py#L445) |  |
| `cancel_messages` |  | [service.py:456](../../../app/whatsapp_scheduler/service.py#L456) | Cancela VÁRIAS mensagens escolhidas uma a uma (seleção em massa), numa transação só — o mesmo efeito de `cancel_schedule |
| `cancel_groups` |  | [service.py:480](../../../app/whatsapp_scheduler/service.py#L480) | "Cancelar selecionados" da tela Agendamentos: cada agendamento inteiro (o que ainda não saiu), numa transação só. Devolv |
| `reschedule_group` |  | [service.py:502](../../../app/whatsapp_scheduler/service.py#L502) | Muda o INÍCIO da sequência (evento remarcado, ou edição do horário): a mensagem N passa a sair em `novo_início + N*gap`. |
| `run_group_now` |  | [service.py:535](../../../app/whatsapp_scheduler/service.py#L535) | "Enviar agora" de um agendamento: a sequência INTEIRA passa a começar agora (mensagem 0 já, as seguintes com o intervalo |
| `_delete_schedule_rows` |  | [service.py:546](../../../app/whatsapp_scheduler/service.py#L546) | Apaga mensagens que NUNCA foram enviadas (edição de um agendamento ainda intacto) — sem histórico a preservar. Ordem por |
| `update_sequence` |  | [service.py:561](../../../app/whatsapp_scheduler/service.py#L561) | Edita um agendamento que AINDA NÃO começou a ser enviado (Conversas e Agendamentos). Muda horário, WhatsApp, textos, qua |
| `run_now` |  | [service.py:682](../../../app/whatsapp_scheduler/service.py#L682) | Antecipa o envio para agora (para testar ponta a ponta). |
| `_chunks` |  | [service.py:725](../../../app/whatsapp_scheduler/service.py#L725) |  |
| `backfill_groups` |  | [service.py:730](../../../app/whatsapp_scheduler/service.py#L730) | Idempotente. Dá um `ScheduleGroup` a cada `Schedule` que ainda não tem: - mensagens de uma automação do Calendário viram |
| `validate_timezone` |  | [timing.py:65](../../../app/whatsapp_scheduler/timing.py#L65) |  |
| `to_utc` |  | [timing.py:74](../../../app/whatsapp_scheduler/timing.py#L74) | Horário de parede no fuso `tz_name` -> UTC naive. |
| `to_local` |  | [timing.py:79](../../../app/whatsapp_scheduler/timing.py#L79) | UTC naive -> horário de parede naive no fuso `tz_name`. |
| `resolve_local` |  | [timing.py:84](../../../app/whatsapp_scheduler/timing.py#L84) | Normaliza o "quando" recebido: com offset (ISO com Z/+03:00) é convertido pro fuso `tz_name`; sem offset já é o horário  |
| `tz_label` |  | [timing.py:101](../../../app/whatsapp_scheduler/timing.py#L101) | "America/Sao_Paulo" -> "São Paulo" (só pra exibição discreta). |
| `check_year` |  | [timing.py:110](../../../app/whatsapp_scheduler/timing.py#L110) |  |
| `parse_local_input` |  | [timing.py:116](../../../app/whatsapp_scheduler/timing.py#L116) | `<input type=date>` ("2026-09-20") + `<input type=time>` ("18:00") -> horário de parede naive. Aceita segundos ("18:00:0 |
| `suggest_start_local` |  | [timing.py:132](../../../app/whatsapp_scheduler/timing.py#L132) | Sugestão de horário para um formulário novo: agora + 30 min, arredondado pra cima em múltiplos de 5 min, no fuso do usuá |
| `parse_send_at` |  | [timing.py:141](../../../app/whatsapp_scheduler/timing.py#L141) | ISO 8601 ("2026-09-20T18:00" do antigo `datetime-local`, com ou sem offset). |
| `sequence_times_utc` |  | [timing.py:152](../../../app/whatsapp_scheduler/timing.py#L152) | Horário (UTC) de cada mensagem: a 1ª é EXATAMENTE `start_utc`; as seguintes só somam o intervalo entre mensagens. Nunca  |
| `parse_interval` |  | [timing.py:161](../../../app/whatsapp_scheduler/timing.py#L161) | "1:45" -> 105 (minutos). Aceita H:MM, HH:MM e HHH:MM; minutos sempre com 2 dígitos. Recusa vazio, negativo, minutos >= 6 |
| `format_interval` |  | [timing.py:183](../../../app/whatsapp_scheduler/timing.py#L183) | 105 -> "1:45" (forma canônica que fica guardada e volta no formulário). |
| `describe_interval` |  | [timing.py:189](../../../app/whatsapp_scheduler/timing.py#L189) | 105 -> "1h45", 120 -> "2h", 15 -> "15min" (texto de resumo). |
| `offset_minutes` |  | [timing.py:199](../../../app/whatsapp_scheduler/timing.py#L199) |  |
| `_offset_timedelta` |  | [timing.py:205](../../../app/whatsapp_scheduler/timing.py#L205) |  |
| `OffsetRule.minutes` |  | [timing.py:222](../../../app/whatsapp_scheduler/timing.py#L222) |  |
| `build_offset_rule` |  | [timing.py:226](../../../app/whatsapp_scheduler/timing.py#L226) | Converte o que o formulário manda ("before", "2:hours" \| "custom" + "1:45") numa regra validada. É o ÚNICO lugar que int |
| `interval_form_values` |  | [timing.py:259](../../../app/whatsapp_scheduler/timing.py#L259) | (valor do <select> "Intervalo", texto do campo "Personalizado") para pré-preencher a edição: uma automação com "Personal |
| `_describe_amount` |  | [timing.py:272](../../../app/whatsapp_scheduler/timing.py#L272) |  |
| `describe_rule` |  | [timing.py:280](../../../app/whatsapp_scheduler/timing.py#L280) |  |
| `_custom_target_utc` |  | [timing.py:292](../../../app/whatsapp_scheduler/timing.py#L292) | Horário FIXO do dia: pega a data local do evento (no fuso do próprio evento) e combina com o horário escolhido. Recalcul |
| `target_utc_for_offset` |  | [timing.py:301](../../../app/whatsapp_scheduler/timing.py#L301) | Instante (UTC naive) do 1º disparo de uma automação. `before`/`after` são relativos ao INÍCIO do evento; `at` é o própri |
| `target_utc_for_rule` |  | [timing.py:325](../../../app/whatsapp_scheduler/timing.py#L325) |  |
| `target_utc_for_message` |  | [timing.py:332](../../../app/whatsapp_scheduler/timing.py#L332) | `target_utc_for_offset` + o intervalo acumulado até a mensagem `position`. |
| `format_when` |  | [timing.py:353](../../../app/whatsapp_scheduler/timing.py#L353) | "20/09/2026 · 18:00". |
| `format_when_at` |  | [timing.py:360](../../../app/whatsapp_scheduler/timing.py#L360) | "20/09/2026 às 18:00" (recebe horário de parede). |
| `as_utc_aware` |  | [timing.py:365](../../../app/whatsapp_scheduler/timing.py#L365) |  |
| `_recipient_key` |  | [routes.py:93](../../../app/whatsapp_scheduler/web/routes.py#L93) | Mesmo critério do JS do ContactPicker (`rcKey`): dígitos do número, senão o texto — só pra não repetir na tela; a valida |
| `pair_recipients` |  | [routes.py:101](../../../app/whatsapp_scheduler/web/routes.py#L101) | `recipients` + `recipient_names` (campos gêmeos do ContactPicker, mesma ordem) -> [{value, label}] sem repetir o mesmo d |
| `unique_chats` |  | [routes.py:118](../../../app/whatsapp_scheduler/web/routes.py#L118) | Valida TODOS os destinatários antes de criar qualquer agendamento e junta os que resolvem pro mesmo chat (ex.: um contat |
| `_start_from_form` |  | [routes.py:133](../../../app/whatsapp_scheduler/web/routes.py#L133) | Data + horário digitados (`send_date` + `send_time`), ou o antigo `send_at` ISO — sempre o horário de parede do usuário. |
| `_form_start_values` |  | [routes.py:141](../../../app/whatsapp_scheduler/web/routes.py#L141) |  |
| `_schedule_form_ctx` |  | [routes.py:146](../../../app/whatsapp_scheduler/web/routes.py#L146) | Estado do formulário de agendamento (criar ou editar). O horário vem do que o usuário já digitou (`overrides`) e só cai  |
| `_media_list` |  | [routes.py:180](../../../app/whatsapp_scheduler/web/routes.py#L180) | Anexos já enviados de um formulário reexibido (erro de validação), na ordem das mensagens — o usuário não precisa mandar |
| `_table_ctx` |  | [routes.py:187](../../../app/whatsapp_scheduler/web/routes.py#L187) |  |
| `_bulk_notice` |  | [routes.py:199](../../../app/whatsapp_scheduler/web/routes.py#L199) | Aviso depois de um cancelamento em massa ("3 mensagens canceladas."). |
| `page_schedules` | rota, async | [routes.py:210](../../../app/whatsapp_scheduler/web/routes.py#L210) |  |
| `_table_response` |  | [routes.py:271](../../../app/whatsapp_scheduler/web/routes.py#L271) | A lista de agendamentos. Quando o pedido veio de um modal (`#modal-root`), a resposta é o trecho "fora de banda": o htmx |
| `ui_schedules` | rota, async | [routes.py:281](../../../app/whatsapp_scheduler/web/routes.py#L281) |  |
| `_form_state_from_input` |  | [routes.py:287](../../../app/whatsapp_scheduler/web/routes.py#L287) |  |
| `_message_count` |  | [routes.py:298](../../../app/whatsapp_scheduler/web/routes.py#L298) | Quantas mensagens o formulário tem (texto e/ou anexo) — pro limite do plano. |
| `ui_create` | rota, async | [routes.py:304](../../../app/whatsapp_scheduler/web/routes.py#L304) |  |
| `ui_create._create_all` | aninhada | [routes.py:336](../../../app/whatsapp_scheduler/web/routes.py#L336) |  |
| `_owned_group_view` |  | [routes.py:376](../../../app/whatsapp_scheduler/web/routes.py#L376) |  |
| `ui_schedule_detail` | rota, async | [routes.py:384](../../../app/whatsapp_scheduler/web/routes.py#L384) |  |
| `_edit_form_ctx` |  | [routes.py:397](../../../app/whatsapp_scheduler/web/routes.py#L397) |  |
| `ui_schedule_edit` | rota, async | [routes.py:419](../../../app/whatsapp_scheduler/web/routes.py#L419) |  |
| `ui_schedule_update` | rota, async | [routes.py:440](../../../app/whatsapp_scheduler/web/routes.py#L440) |  |
| `ui_cancel` | rota, async | [routes.py:477](../../../app/whatsapp_scheduler/web/routes.py#L477) |  |
| `ui_cancel_selected` | rota, async | [routes.py:488](../../../app/whatsapp_scheduler/web/routes.py#L488) | "Cancelar selecionados" (seleção em massa): cada agendamento marcado inteiro, numa transação só (`service.cancel_groups` |
| `ui_run_now` | rota, async | [routes.py:508](../../../app/whatsapp_scheduler/web/routes.py#L508) | Antecipa o envio (teste ponta a ponta): a sequência inteira passa a começar agora. |
| `_media_error` |  | [routes.py:521](../../../app/whatsapp_scheduler/web/routes.py#L521) |  |
| `ui_media_upload` | rota, async | [routes.py:526](../../../app/whatsapp_scheduler/web/routes.py#L526) | Recebe UM arquivo assim que o usuário o escolhe no formulário (o agendamento manda depois só o id). Recurso de plano: se |
| `ui_media_file` | rota, async | [routes.py:569](../../../app/whatsapp_scheduler/web/routes.py#L569) | O anexo decifrado, só para o DONO (miniatura/pré-visualização). Depois que a mensagem termina o arquivo não existe mais: |

## Templates desta funcionalidade

Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).

| Template | hx-* | Listeners JS | Handlers inline | Polling |
|---|---|---|---|---|
| [`_bulk_bar.html`](../../../app/whatsapp_scheduler/web/templates/_bulk_bar.html) | 0 | 0 | 2 | 0 |
| [`_schedule_detail_modal.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_detail_modal.html) | 9 | 0 | 1 | 0 |
| [`_schedule_edit_modal.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_edit_modal.html) | 4 | 0 | 4 | 0 |
| [`_schedule_fields.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_fields.html) | 0 | 0 | 0 | 0 |
| [`_schedule_form.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_form.html) | 4 | 1 | 2 | 0 |
| [`_schedule_form_response.html`](../../../app/whatsapp_scheduler/web/templates/_schedule_form_response.html) | 0 | 0 | 0 | 0 |
| [`_table.html`](../../../app/whatsapp_scheduler/web/templates/_table.html) | 7 | 0 | 2 | 0 |
| [`schedules.html`](../../../app/whatsapp_scheduler/web/templates/schedules.html) | 8 | 1 | 0 | 1 |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_media_messages.py`](../../../app/tests/test_media_messages.py) — 36 funções: `test_only_the_most_expensive_plan_has_media_in_the_seeded_catalog`, `test_free_plan_sees_the_locked_button_and_cannot_upload`, `test_plus_plan_is_not_enough_but_pro_is`, `test_capability_is_enforced_even_without_enforce_plan_limits`, `test_migration_turns_media_on_in_the_most_expensive_plan_only`, `test_upload_is_encrypted_on_disk_and_the_name_is_not_in_the_database`, `test_type_comes_from_the_bytes_not_from_the_name`, `test_upload_size_limit`, `test_preview_is_only_for_the_owner`, `test_photo_with_caption_is_sent_and_then_purged`, `test_media_only_message_needs_no_text`, `test_empty_block_without_media_is_still_rejected`, `test_audio_with_text_becomes_voice_then_text`, `test_audio_with_text_and_recurrence_explains_why_not`, `test_cancel_purges_the_attachment`, `test_attachment_shared_by_two_recipients_survives_until_the_last_one`, `test_fresh_attachment_waits_for_the_cleanup_job`, `test_failed_attempt_keeps_the_file_for_the_retry`, `test_missing_file_fails_the_message_without_sending`, `test_duplicate_submit_creates_one_schedule`, `test_detail_modal_shows_the_attachment_to_the_owner`, `test_edit_keeps_or_drops_the_attachment`, `test_cannot_schedule_with_someone_elses_attachment`, `test_downgraded_user_cannot_schedule_an_old_upload`, `test_admin_has_the_feature_regardless_of_plan`, `test_abandoned_upload_and_orphan_files_are_cleaned`, `test_too_many_drafts`, `test_waha_routes_each_kind_to_its_endpoint`, `test_waha_video_falls_back_to_document_without_chrome`, `test_waha_other_video_errors_are_not_masked`, `test_waha_500_keeps_only_the_reason_never_the_echoed_request`, `test_waha_reason_of_a_rejection_is_sanitized`, `test_failed_media_send_records_the_reason`, `test_dashboard_shows_the_attachment_type_of_a_media_only_message`, `test_rotate_keys_reencrypts_attachments_without_overwriting_before_commit`, `test_sniff_signatures`
- [`app/tests/test_multi_whatsapp_dispatch.py`](../../../app/tests/test_multi_whatsapp_dispatch.py) — 2 funções: `test_dispatch_routes_each_schedule_through_its_own_whatsapp_session`, `test_two_automations_on_same_event_send_through_different_whatsapps`
- [`app/tests/test_recurrence.py`](../../../app/tests/test_recurrence.py) — 5 funções (2 parametrizadas): `test_normalize_recurrence`, `test_normalize_recurrence_invalid`, `test_timezone_roundtrip`, `test_next_run_utc_respects_timezone`, `test_next_run_utc_rolls_to_next_day`
- [`app/tests/test_scheduler.py`](../../../app/tests/test_scheduler.py) — 11 funções: `test_due_dispatch_is_sent`, `test_future_dispatch_not_sent`, `test_session_not_working_defers_without_consuming_attempt`, `test_send_error_retries_with_backoff`, `test_send_error_exhausts_to_failed`, `test_overdue_is_skipped`, `test_recurring_materializes_next_after_send`, `test_recover_stuck_processing`, `test_dependency_gate_holds_successor_until_predecessor_sent`, `test_dependency_gate_aborts_successor_when_predecessor_fails_permanently`, `test_dependency_gate_cascade_aborts_two_levels_deep`
- [`app/tests/test_scheduling_service.py`](../../../app/tests/test_scheduling_service.py) — 30 funções: `test_one_recipient_one_message_keeps_18h`, `test_three_messages_are_three_individual_schedules_of_one_group`, `test_sequence_is_chained_so_order_survives_failures`, `test_adding_messages_later_never_changes_the_start`, `test_editing_the_start_moves_every_message`, `test_edit_can_reorder_and_remove_messages`, `test_edit_is_refused_once_sending_started`, `test_recurrence_only_for_a_single_message`, `test_validation`, `test_create_schedule_compat_is_a_group_of_one`, `test_message_goes_out_through_the_selected_whatsapp`, `test_sequence_is_sent_in_order_and_content_is_purged`, `test_later_messages_wait_when_an_earlier_one_fails`, `test_canceled_message_is_never_sent_and_the_others_still_are`, `test_canceling_the_whole_group_sends_nothing`, `test_cancel_during_a_failing_send_does_not_resurrect_the_dispatch`, `test_user_cannot_touch_another_users_schedule`, `test_group_status_derivation`, `test_list_shows_real_local_time_and_sorts_open_first`, `test_times_are_shown_in_the_users_timezone_not_the_schedules`, `test_conversation_scheduled_only_this_chat_and_user`, `test_backfill_groups_legacy_schedules_is_idempotent`, `test_backfill_groups_automation_chain_by_recipient`, `test_reschedule_group_moves_pending_dispatch_and_every_message`, `test_extreme_dates_are_a_validation_error_not_a_crash`, `test_dedupe_collapses_an_identical_double_submit_but_not_a_different_one`, `test_waiting_chain_is_skipped_without_hitting_the_gate`, `test_waiting_chain_still_advances_once_the_first_is_sent`, `test_soft_deleted_whatsapp_cannot_be_used`, `test_run_now_moves_the_whole_sequence_not_just_the_first_message`
- [`app/tests/test_scheduling_ui.py`](../../../app/tests/test_scheduling_ui.py) — 36 funções (1 parametrizadas): `test_agendamentos_form_is_clean_and_uses_shared_components`, `test_create_multi_message_schedule_keeps_the_typed_time`, `test_manual_number_and_contact_are_accepted_and_duplicates_collapse`, `test_error_keeps_everything_the_user_typed`, `test_recurrence_allowed_for_one_message_but_not_for_a_sequence`, `test_schedule_goes_through_the_whatsapp_selected_in_the_form`, `test_picker_lists_only_own_sessions_with_live_status`, `test_disconnected_whatsapp_is_flagged_and_blocks_scheduling`, `test_cannot_schedule_through_another_users_whatsapp`, `test_detail_edit_and_cancel_flow`, `test_edit_error_keeps_the_form_and_does_not_change_anything`, `test_user_a_cannot_open_edit_or_cancel_user_bs_schedule`, `test_contacts_show_photo_when_there_is_one_and_default_avatar_otherwise`, `test_agendamentos_uses_the_same_contact_endpoint_as_the_calendar`, `test_chat_schedule_creates_one_group_with_the_whole_sequence`, `test_chat_schedule_form_never_loses_the_time_after_saving`, `test_scheduled_messages_appear_inside_the_conversation_one_bubble_each`, `test_scheduled_bubbles_do_not_wait_for_the_slow_whatsapp_history`, `test_cancel_one_message_from_the_conversation`, `test_cannot_cancel_another_users_scheduled_message_from_a_chat`, `test_chat_schedule_still_accepts_the_old_single_text_fields`, `test_disconnected_whatsapp_blocks_scheduling_from_a_chat`, `test_end_to_end_conversation_sequence_is_sent_and_shown`, `test_preview_before_and_after_with_custom_interval`, `test_preview_shows_a_clear_validation_error`, `test_create_automation_with_custom_interval_and_edit_keeps_it`, `test_automation_invalid_custom_interval_keeps_the_form_filled`, `test_automation_blocked_when_whatsapp_is_disconnected`, `test_calendar_and_schedule_forms_share_the_same_components`, `test_automation_custom_interval_via_api`, `test_end_to_end_google_event_custom_rule_to_whatsapp`, `test_double_submit_of_the_form_creates_one_schedule`, `test_extreme_date_from_the_form_is_a_message_not_a_500`, `test_recipient_cap_per_submit`, `test_removed_whatsapp_is_rejected_by_the_form`, `test_run_now_from_the_detail_moves_the_whole_group`
- [`app/tests/test_timing.py`](../../../app/tests/test_timing.py) — 20 funções (2 parametrizadas): `test_parse_interval_accepts_hhmm_and_friendly_forms`, `test_parse_interval_rejects_invalid_values`, `test_parse_interval_error_messages_are_clear`, `test_interval_is_normalized_to_one_canonical_form`, `test_custom_interval_before_event_1h45_is_18_15`, `test_custom_interval_after_event_1h45_is_21_45`, `test_custom_interval_is_relative_never_a_wall_clock_time`, `test_at_event_ignores_any_interval`, `test_preset_intervals_still_work`, `test_custom_interval_crossing_midnight_keeps_the_right_date`, `test_build_offset_rule_rejects_bad_input`, `test_fixed_time_of_day_rule_is_still_supported`, `test_rule_descriptions_for_the_summary`, `test_edit_form_keeps_personalizado_value`, `test_sequence_times_never_move_the_start`, `test_local_time_converts_through_zoneinfo_not_manual_offsets`, `test_resolve_local_naive_is_kept_and_aware_is_converted`, `test_parse_local_input_and_errors`, `test_suggested_start_is_in_the_future_rounded_to_5_minutes`, `test_timezone_label_is_friendly`
