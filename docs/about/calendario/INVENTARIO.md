# Calendário — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/calendar_providers/__init__.py`](../../../app/whatsapp_scheduler/calendar_providers/__init__.py) | 30 |
| [`app/whatsapp_scheduler/calendar_providers/base.py`](../../../app/whatsapp_scheduler/calendar_providers/base.py) | 145 |
| [`app/whatsapp_scheduler/calendar_providers/google.py`](../../../app/whatsapp_scheduler/calendar_providers/google.py) | 426 |
| [`app/whatsapp_scheduler/calendar_schemas.py`](../../../app/whatsapp_scheduler/calendar_schemas.py) | 114 |
| [`app/whatsapp_scheduler/calendar_service.py`](../../../app/whatsapp_scheduler/calendar_service.py) | 1108 |
| [`app/whatsapp_scheduler/calendar_sync.py`](../../../app/whatsapp_scheduler/calendar_sync.py) | 345 |
| [`app/whatsapp_scheduler/web/calendar_routes.py`](../../../app/whatsapp_scheduler/web/calendar_routes.py) | 950 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_calendar_providers.py`](../../../app/tests/test_calendar_providers.py), [`app/tests/test_calendar_service.py`](../../../app/tests/test_calendar_service.py), [`app/tests/test_calendar_sync.py`](../../../app/tests/test_calendar_sync.py), [`app/tests/test_calendar_web.py`](../../../app/tests/test_calendar_web.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/calendario` | `page_calendario` | [calendar_routes.py:356](../../../app/whatsapp_scheduler/web/calendar_routes.py#L356) |
| GET | `/ui/calendario/grid` | `ui_grid` | [calendar_routes.py:371](../../../app/whatsapp_scheduler/web/calendar_routes.py#L371) |
| GET | `/calendario/dia` | `page_calendario_dia` | [calendar_routes.py:388](../../../app/whatsapp_scheduler/web/calendar_routes.py#L388) |
| GET | `/ui/calendario/dia` | `ui_calendario_dia` | [calendar_routes.py:403](../../../app/whatsapp_scheduler/web/calendar_routes.py#L403) |
| GET | `/ui/calendario/events/new` | `ui_event_new` | [calendar_routes.py:421](../../../app/whatsapp_scheduler/web/calendar_routes.py#L421) |
| GET | `/ui/calendario/events/{event_id}` | `ui_event_detail` | [calendar_routes.py:451](../../../app/whatsapp_scheduler/web/calendar_routes.py#L451) |
| GET | `/ui/calendario/events/{event_id}/edit` | `ui_event_edit` | [calendar_routes.py:467](../../../app/whatsapp_scheduler/web/calendar_routes.py#L467) |
| GET | `/ui/calendario/events/{event_id}/delete-confirm` | `ui_event_delete_confirm` | [calendar_routes.py:503](../../../app/whatsapp_scheduler/web/calendar_routes.py#L503) |
| POST | `/ui/calendario/events` | `ui_event_create` | [calendar_routes.py:529](../../../app/whatsapp_scheduler/web/calendar_routes.py#L529) |
| POST | `/ui/calendario/events/{event_id}` | `ui_event_update` | [calendar_routes.py:568](../../../app/whatsapp_scheduler/web/calendar_routes.py#L568) |
| POST | `/ui/calendario/events/{event_id}/delete` | `ui_event_delete` | [calendar_routes.py:607](../../../app/whatsapp_scheduler/web/calendar_routes.py#L607) |
| GET | `/ui/calendario/contacts` | `ui_calendario_contacts` | [calendar_routes.py:646](../../../app/whatsapp_scheduler/web/calendar_routes.py#L646) |
| GET | `/ui/calendario/events/{event_id}/similar-events` | `ui_calendario_similar_events` | [calendar_routes.py:670](../../../app/whatsapp_scheduler/web/calendar_routes.py#L670) |
| GET | `/ui/calendario/events/{event_id}/automation/new` | `ui_automation_new` | [calendar_routes.py:711](../../../app/whatsapp_scheduler/web/calendar_routes.py#L711) |
| GET | `/ui/calendario/automations/{automation_id}/edit` | `ui_automation_edit` | [calendar_routes.py:727](../../../app/whatsapp_scheduler/web/calendar_routes.py#L727) |
| GET | `/ui/calendario/events/{event_id}/automation-preview` | `ui_automation_preview` | [calendar_routes.py:746](../../../app/whatsapp_scheduler/web/calendar_routes.py#L746) |
| POST | `/ui/calendario/events/{event_id}/automation` | `ui_automation_create` | [calendar_routes.py:796](../../../app/whatsapp_scheduler/web/calendar_routes.py#L796) |
| POST | `/ui/calendario/automations/{automation_id}` | `ui_automation_update` | [calendar_routes.py:878](../../../app/whatsapp_scheduler/web/calendar_routes.py#L878) |
| POST | `/ui/calendario/automations/{automation_id}/remove` | `ui_automation_remove` | [calendar_routes.py:933](../../../app/whatsapp_scheduler/web/calendar_routes.py#L933) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `OAuthTokens` |  | [base.py:17](../../../app/whatsapp_scheduler/calendar_providers/base.py#L17) |
| `RemoteCalendar` |  | [base.py:25](../../../app/whatsapp_scheduler/calendar_providers/base.py#L25) |
| `RemoteEvent` |  | [base.py:34](../../../app/whatsapp_scheduler/calendar_providers/base.py#L34) |
| `RemoteEventPage` |  | [base.py:50](../../../app/whatsapp_scheduler/calendar_providers/base.py#L50) |
| `CalendarProviderError` | RuntimeError | [base.py:56](../../../app/whatsapp_scheduler/calendar_providers/base.py#L56) |
| `SyncTokenExpired` | CalendarProviderError | [base.py:60](../../../app/whatsapp_scheduler/calendar_providers/base.py#L60) |
| `CalendarProvider` | ABC | [base.py:64](../../../app/whatsapp_scheduler/calendar_providers/base.py#L64) |
| `GoogleCalendarError` | CalendarProviderError | [google.py:40](../../../app/whatsapp_scheduler/calendar_providers/google.py#L40) |
| `GoogleSyncTokenExpired` | SyncTokenExpired | [google.py:44](../../../app/whatsapp_scheduler/calendar_providers/google.py#L44) |
| `GoogleCalendarClient` |  | [google.py:113](../../../app/whatsapp_scheduler/calendar_providers/google.py#L113) |
| `GoogleCalendarProvider` | CalendarProvider | [google.py:252](../../../app/whatsapp_scheduler/calendar_providers/google.py#L252) |
| `ConnectionRead` | BaseModel | [calendar_schemas.py:13](../../../app/whatsapp_scheduler/calendar_schemas.py#L13) |
| `CalendarRead` | BaseModel | [calendar_schemas.py:35](../../../app/whatsapp_scheduler/calendar_schemas.py#L35) |
| `AutomationRead` | BaseModel | [calendar_schemas.py:55](../../../app/whatsapp_scheduler/calendar_schemas.py#L55) |
| `EventRead` | BaseModel | [calendar_schemas.py:85](../../../app/whatsapp_scheduler/calendar_schemas.py#L85) |
| `NotConfiguredError` | RuntimeError | [calendar_service.py:56](../../../app/whatsapp_scheduler/calendar_service.py#L56) |
| `CalendarSyncService` |  | [calendar_sync.py:301](../../../app/whatsapp_scheduler/calendar_sync.py#L301) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `_registry` |  | [__init__.py:18](../../../app/whatsapp_scheduler/calendar_providers/__init__.py#L18) |  |
| `get_provider` |  | [__init__.py:22](../../../app/whatsapp_scheduler/calendar_providers/__init__.py#L22) |  |
| `available_providers` |  | [__init__.py:29](../../../app/whatsapp_scheduler/calendar_providers/__init__.py#L29) |  |
| `CalendarProvider.is_configured` |  | [base.py:70](../../../app/whatsapp_scheduler/calendar_providers/base.py#L70) | Client id/secret (e o que mais for preciso) estão configurados? |
| `CalendarProvider.get_authorize_url` |  | [base.py:74](../../../app/whatsapp_scheduler/calendar_providers/base.py#L74) | URL para redirecionar o usuário iniciar o consentimento OAuth. |
| `CalendarProvider.exchange_code` | async | [base.py:78](../../../app/whatsapp_scheduler/calendar_providers/base.py#L78) | Troca o `code` do callback OAuth pelos tokens de acesso. |
| `CalendarProvider.refresh` | async | [base.py:82](../../../app/whatsapp_scheduler/calendar_providers/base.py#L82) | Renova o access token usando o refresh token salvo. |
| `CalendarProvider.revoke` | async | [base.py:85](../../../app/whatsapp_scheduler/calendar_providers/base.py#L85) | Revoga o acesso no provedor quando o usuário desconecta a conta. Opcional (padrão: nada) — os tokens locais já são apaga |
| `CalendarProvider.get_account_identifier` | async | [base.py:90](../../../app/whatsapp_scheduler/calendar_providers/base.py#L90) | E-mail/identificador da conta conectada, só para exibição na UI. |
| `CalendarProvider.list_calendars` | async | [base.py:99](../../../app/whatsapp_scheduler/calendar_providers/base.py#L99) | Lista os calendários disponíveis na conta conectada. |
| `CalendarProvider.list_events` | async | [base.py:103](../../../app/whatsapp_scheduler/calendar_providers/base.py#L103) | Lista eventos de um calendário — sync completo (time_min/time_max) ou incremental (sync_token). |
| `CalendarProvider.create_event` | async | [base.py:115](../../../app/whatsapp_scheduler/calendar_providers/base.py#L115) | Cria um evento no provedor. Retorna o `external_id` do evento criado. |
| `CalendarProvider.update_event` | async | [base.py:129](../../../app/whatsapp_scheduler/calendar_providers/base.py#L129) | Atualiza (PATCH) um evento já existente no provedor pelo `external_id` — nunca cria um novo. |
| `CalendarProvider.delete_event` | async | [base.py:144](../../../app/whatsapp_scheduler/calendar_providers/base.py#L144) | Exclui um evento no provedor pelo `external_id`. |
| `_rfc3339` |  | [google.py:48](../../../app/whatsapp_scheduler/calendar_providers/google.py#L48) |  |
| `_parse_iso` |  | [google.py:54](../../../app/whatsapp_scheduler/calendar_providers/google.py#L54) |  |
| `_parse_start_end` |  | [google.py:58](../../../app/whatsapp_scheduler/calendar_providers/google.py#L58) | Retorna (utc_naive, timezone_efetiva, all_day). |
| `_to_remote_event` |  | [google.py:71](../../../app/whatsapp_scheduler/calendar_providers/google.py#L71) |  |
| `_error_summary` |  | [google.py:99](../../../app/whatsapp_scheduler/calendar_providers/google.py#L99) | Só o código/mensagem de erro do Google (nunca tokens do corpo). |
| `GoogleCalendarClient.__init__` |  | [google.py:116](../../../app/whatsapp_scheduler/calendar_providers/google.py#L116) |  |
| `GoogleCalendarClient.aclose` | async | [google.py:119](../../../app/whatsapp_scheduler/calendar_providers/google.py#L119) |  |
| `GoogleCalendarClient._request` | async | [google.py:122](../../../app/whatsapp_scheduler/calendar_providers/google.py#L122) |  |
| `GoogleCalendarClient.exchange_code` | async | [google.py:137](../../../app/whatsapp_scheduler/calendar_providers/google.py#L137) |  |
| `GoogleCalendarClient.refresh_token` | async | [google.py:151](../../../app/whatsapp_scheduler/calendar_providers/google.py#L151) |  |
| `GoogleCalendarClient.revoke` | async | [google.py:164](../../../app/whatsapp_scheduler/calendar_providers/google.py#L164) |  |
| `GoogleCalendarClient.get_userinfo` | async | [google.py:167](../../../app/whatsapp_scheduler/calendar_providers/google.py#L167) |  |
| `GoogleCalendarClient.list_calendars` | async | [google.py:175](../../../app/whatsapp_scheduler/calendar_providers/google.py#L175) |  |
| `GoogleCalendarClient.list_events_page` | async | [google.py:183](../../../app/whatsapp_scheduler/calendar_providers/google.py#L183) |  |
| `GoogleCalendarClient.insert_event` | async | [google.py:214](../../../app/whatsapp_scheduler/calendar_providers/google.py#L214) |  |
| `GoogleCalendarClient.patch_event` | async | [google.py:224](../../../app/whatsapp_scheduler/calendar_providers/google.py#L224) |  |
| `GoogleCalendarClient.delete_event` | async | [google.py:235](../../../app/whatsapp_scheduler/calendar_providers/google.py#L235) |  |
| `GoogleCalendarProvider.__init__` |  | [google.py:255](../../../app/whatsapp_scheduler/calendar_providers/google.py#L255) |  |
| `GoogleCalendarProvider.is_configured` |  | [google.py:258](../../../app/whatsapp_scheduler/calendar_providers/google.py#L258) |  |
| `GoogleCalendarProvider._require_configured` |  | [google.py:261](../../../app/whatsapp_scheduler/calendar_providers/google.py#L261) |  |
| `GoogleCalendarProvider.get_authorize_url` |  | [google.py:267](../../../app/whatsapp_scheduler/calendar_providers/google.py#L267) |  |
| `GoogleCalendarProvider._tokens_from_response` |  | [google.py:280](../../../app/whatsapp_scheduler/calendar_providers/google.py#L280) |  |
| `GoogleCalendarProvider.exchange_code` | async | [google.py:301](../../../app/whatsapp_scheduler/calendar_providers/google.py#L301) |  |
| `GoogleCalendarProvider.refresh` | async | [google.py:311](../../../app/whatsapp_scheduler/calendar_providers/google.py#L311) |  |
| `GoogleCalendarProvider.revoke` | async | [google.py:320](../../../app/whatsapp_scheduler/calendar_providers/google.py#L320) | Revoga o acesso no Google (o usuário desconectou a conta no Attena). |
| `GoogleCalendarProvider.get_account_identifier` | async | [google.py:324](../../../app/whatsapp_scheduler/calendar_providers/google.py#L324) |  |
| `GoogleCalendarProvider.list_calendars` | async | [google.py:332](../../../app/whatsapp_scheduler/calendar_providers/google.py#L332) |  |
| `GoogleCalendarProvider.list_events` | async | [google.py:345](../../../app/whatsapp_scheduler/calendar_providers/google.py#L345) |  |
| `GoogleCalendarProvider._event_body` |  | [google.py:380](../../../app/whatsapp_scheduler/calendar_providers/google.py#L380) |  |
| `GoogleCalendarProvider.create_event` | async | [google.py:388](../../../app/whatsapp_scheduler/calendar_providers/google.py#L388) |  |
| `GoogleCalendarProvider.update_event` | async | [google.py:408](../../../app/whatsapp_scheduler/calendar_providers/google.py#L408) |  |
| `GoogleCalendarProvider.delete_event` | async | [google.py:425](../../../app/whatsapp_scheduler/calendar_providers/google.py#L425) |  |
| `ConnectionRead.of` |  | [calendar_schemas.py:23](../../../app/whatsapp_scheduler/calendar_schemas.py#L23) |  |
| `CalendarRead.of` |  | [calendar_schemas.py:44](../../../app/whatsapp_scheduler/calendar_schemas.py#L44) |  |
| `AutomationRead.of` |  | [calendar_schemas.py:68](../../../app/whatsapp_scheduler/calendar_schemas.py#L68) | `item` é uma entrada de `calendar_service.event_automations()` — `{"automation", "recipients", "messages", "enabled"}`. |
| `EventRead.of` |  | [calendar_schemas.py:100](../../../app/whatsapp_scheduler/calendar_schemas.py#L100) |  |
| `missing_config` |  | [calendar_service.py:60](../../../app/whatsapp_scheduler/calendar_service.py#L60) | Nomes exatos das variáveis de ambiente que faltam configurar. |
| `start_connect` |  | [calendar_service.py:71](../../../app/whatsapp_scheduler/calendar_service.py#L71) | Retorna (authorize_url, state); o state deve ir num cookie httponly p/ validar no callback. |
| `finish_connect` | async | [calendar_service.py:83](../../../app/whatsapp_scheduler/calendar_service.py#L83) |  |
| `refresh_remote_calendars` | async | [calendar_service.py:120](../../../app/whatsapp_scheduler/calendar_service.py#L120) |  |
| `list_connections` |  | [calendar_service.py:154](../../../app/whatsapp_scheduler/calendar_service.py#L154) | Só conexões que ainda "existem" pro usuário — `disconnected` é um soft-delete (a linha continua no banco só pra manter o |
| `_owned_connection` |  | [calendar_service.py:172](../../../app/whatsapp_scheduler/calendar_service.py#L172) |  |
| `connection_has_write_scope` |  | [calendar_service.py:182](../../../app/whatsapp_scheduler/calendar_service.py#L182) | Compara por token exato (não substring) — `"...calendar.readonly"` contém a palavra "calendar" mas NÃO é o escopo de esc |
| `list_calendars` |  | [calendar_service.py:188](../../../app/whatsapp_scheduler/calendar_service.py#L188) |  |
| `_owned_calendar` |  | [calendar_service.py:198](../../../app/whatsapp_scheduler/calendar_service.py#L198) |  |
| `set_calendar_enabled` |  | [calendar_service.py:208](../../../app/whatsapp_scheduler/calendar_service.py#L208) |  |
| `sync_now` | async | [calendar_service.py:224](../../../app/whatsapp_scheduler/calendar_service.py#L224) |  |
| `disconnect` |  | [calendar_service.py:233](../../../app/whatsapp_scheduler/calendar_service.py#L233) | Para novas sincronizações e cancela mensagens futuras ainda pendentes ligadas a esta conta — preserva histórico e mensag |
| `disconnect_and_revoke` | async | [calendar_service.py:268](../../../app/whatsapp_scheduler/calendar_service.py#L268) | Desconecta (apaga os tokens locais) e pede ao Google para revogar o acesso — best-effort: se o Google não responder, os  |
| `_parse_offset` |  | [calendar_service.py:292](../../../app/whatsapp_scheduler/calendar_service.py#L292) |  |
| `_resolve_custom_time` |  | [calendar_service.py:304](../../../app/whatsapp_scheduler/calendar_service.py#L304) | direction != custom: ignora qualquer valor recebido (nunca persiste lixo). direction == custom: exige um "HH:MM" válido. |
| `_find_duplicate_automation` |  | [calendar_service.py:321](../../../app/whatsapp_scheduler/calendar_service.py#L321) | Evita duplicar: duplo clique, duplo submit, ou salvar a mesma automação duas vezes. A trava é no nível da `Automation` i |
| `_resolve_custom_interval` |  | [calendar_service.py:375](../../../app/whatsapp_scheduler/calendar_service.py#L375) | "Personalizado · 1:45" só existe em antes/depois; o texto guardado é a forma canônica e tem que bater com `amount`/`unit |
| `create_event_automation` |  | [calendar_service.py:389](../../../app/whatsapp_scheduler/calendar_service.py#L389) | Cria a automação e, pra CADA destinatário, um agendamento (`ScheduleGroup`, origem `calendar`) com a sequência inteira d |
| `similar_events` |  | [calendar_service.py:514](../../../app/whatsapp_scheduler/calendar_service.py#L514) | Outros eventos FUTUROS "iguais" a este (v1.3) — usado pra oferecer "repetir esta automação" sem precisar recriá-la manua |
| `_owned_automation` |  | [calendar_service.py:545](../../../app/whatsapp_scheduler/calendar_service.py#L545) |  |
| `remove_event_automation` |  | [calendar_service.py:555](../../../app/whatsapp_scheduler/calendar_service.py#L555) |  |
| `update_event_automation` |  | [calendar_service.py:564](../../../app/whatsapp_scheduler/calendar_service.py#L564) | "Editar" = cancelar todos os schedules da automação antiga + apagar as linhas de ligação + criar uma nova do zero. Não m |
| `event_automations` |  | [calendar_service.py:619](../../../app/whatsapp_scheduler/calendar_service.py#L619) | Uma entrada por `Automation`, com suas mensagens em ordem e, para cada uma, o `Schedule` de cada destinatário (pra mostr |
| `migrate_legacy_automations` |  | [calendar_service.py:709](../../../app/whatsapp_scheduler/calendar_service.py#L709) | Converte, uma única vez, as automações do modelo antigo (incremento 2 — `EventAutomation`, 1 `Schedule` por linha, 1 men |
| `agenda` |  | [calendar_service.py:765](../../../app/whatsapp_scheduler/calendar_service.py#L765) | Eventos a partir de agora até `days` dias à frente (default: settings). Usado pela API REST (`/api/calendar/events`) — a |
| `day_events` |  | [calendar_service.py:783](../../../app/whatsapp_scheduler/calendar_service.py#L783) | Eventos de UM dia local específico (v1.3, visão diária — item 29), mesma lógica de bucketing por timezone PRÓPRIA do eve |
| `month_grid` |  | [calendar_service.py:812](../../../app/whatsapp_scheduler/calendar_service.py#L812) | Grade de 6 semanas (42 dias, domingo a sábado) pro mês pedido. |
| `_validate_event_fields` |  | [calendar_service.py:877](../../../app/whatsapp_scheduler/calendar_service.py#L877) |  |
| `_google_provider_and_tokens` | async | [calendar_service.py:890](../../../app/whatsapp_scheduler/calendar_service.py#L890) |  |
| `_remote_calendar` |  | [calendar_service.py:899](../../../app/whatsapp_scheduler/calendar_service.py#L899) |  |
| `_set_sync_status` |  | [calendar_service.py:903](../../../app/whatsapp_scheduler/calendar_service.py#L903) |  |
| `_delete_automations_for_event` |  | [calendar_service.py:914](../../../app/whatsapp_scheduler/calendar_service.py#L914) |  |
| `create_internal_event` | async | [calendar_service.py:924](../../../app/whatsapp_scheduler/calendar_service.py#L924) | `target_calendar_id` (opcional) é o id (interno, de `Calendar`) de um calendário Google habilitado — cria o evento local |
| `update_internal_event` | async | [calendar_service.py:989](../../../app/whatsapp_scheduler/calendar_service.py#L989) | Se o evento estiver vinculado a um calendário Google, o PATCH é tentado ANTES de qualquer alteração local ser commitada  |
| `delete_internal_event` | async | [calendar_service.py:1056](../../../app/whatsapp_scheduler/calendar_service.py#L1056) | `also_delete_google` só importa se o evento estiver vinculado — se o DELETE no Google falhar, o evento local NÃO é exclu |
| `list_contacts` | async | [calendar_service.py:1100](../../../app/whatsapp_scheduler/calendar_service.py#L1100) | Contatos pra automação — reaproveita a lista de conversas do WhatsApp já existente (`chatsvc.list_chats`); não cria uma  |
| `ensure_fresh_tokens` | async | [calendar_sync.py:59](../../../app/whatsapp_scheduler/calendar_sync.py#L59) | Decifra os tokens salvos; renova (e persiste) se estiverem perto de expirar. |
| `_automation_target_utc` |  | [calendar_sync.py:89](../../../app/whatsapp_scheduler/calendar_sync.py#L89) | Novo horário de INÍCIO de uma automação para o horário atual do evento — o cálculo é o de `timing` (o mesmo da criação e |
| `_reschedule_automations` |  | [calendar_sync.py:102](../../../app/whatsapp_scheduler/calendar_sync.py#L102) | Evento com novo horário: remarca cada agendamento (grupo) das automações ligadas, no lugar (sem duplicar) — `service.res |
| `_cancel_automations` |  | [calendar_sync.py:130](../../../app/whatsapp_scheduler/calendar_sync.py#L130) |  |
| `reschedule_event_automations` |  | [calendar_sync.py:139](../../../app/whatsapp_scheduler/calendar_sync.py#L139) | Wrapper público de `_reschedule_automations` — usado também pela edição de eventos internos (`calendar_service.update_in |
| `cancel_event_automations` |  | [calendar_sync.py:146](../../../app/whatsapp_scheduler/calendar_sync.py#L146) | Wrapper público de `_cancel_automations` — usado também pela exclusão de eventos internos (`calendar_service.delete_inte |
| `_reconcile_event` |  | [calendar_sync.py:152](../../../app/whatsapp_scheduler/calendar_sync.py#L152) |  |
| `sync_calendar` | async | [calendar_sync.py:213](../../../app/whatsapp_scheduler/calendar_sync.py#L213) |  |
| `sync_calendar._bounds` | aninhada | [calendar_sync.py:219](../../../app/whatsapp_scheduler/calendar_sync.py#L219) |  |
| `sync_calendar._reconcile_page` | aninhada | [calendar_sync.py:239](../../../app/whatsapp_scheduler/calendar_sync.py#L239) |  |
| `sync_connection` | async | [calendar_sync.py:257](../../../app/whatsapp_scheduler/calendar_sync.py#L257) |  |
| `sync_all` | async | [calendar_sync.py:289](../../../app/whatsapp_scheduler/calendar_sync.py#L289) |  |
| `CalendarSyncService.__init__` |  | [calendar_sync.py:308](../../../app/whatsapp_scheduler/calendar_sync.py#L308) |  |
| `CalendarSyncService.start` | async | [calendar_sync.py:313](../../../app/whatsapp_scheduler/calendar_sync.py#L313) |  |
| `CalendarSyncService.stop` | async | [calendar_sync.py:319](../../../app/whatsapp_scheduler/calendar_sync.py#L319) |  |
| `CalendarSyncService.run_once` | async | [calendar_sync.py:328](../../../app/whatsapp_scheduler/calendar_sync.py#L328) |  |
| `CalendarSyncService._run` | async | [calendar_sync.py:331](../../../app/whatsapp_scheduler/calendar_sync.py#L331) |  |
| `_waha` |  | [calendar_routes.py:54](../../../app/whatsapp_scheduler/web/calendar_routes.py#L54) |  |
| `_day_label` |  | [calendar_routes.py:58](../../../app/whatsapp_scheduler/web/calendar_routes.py#L58) |  |
| `_month_label` |  | [calendar_routes.py:62](../../../app/whatsapp_scheduler/web/calendar_routes.py#L62) |  |
| `_shift_month` |  | [calendar_routes.py:66](../../../app/whatsapp_scheduler/web/calendar_routes.py#L66) |  |
| `_ctx` |  | [calendar_routes.py:71](../../../app/whatsapp_scheduler/web/calendar_routes.py#L71) |  |
| `_current_year_month` |  | [calendar_routes.py:75](../../../app/whatsapp_scheduler/web/calendar_routes.py#L75) |  |
| `_filterable_calendars` |  | [calendar_routes.py:80](../../../app/whatsapp_scheduler/web/calendar_routes.py#L80) |  |
| `_google_target_calendars` |  | [calendar_routes.py:89](../../../app/whatsapp_scheduler/web/calendar_routes.py#L89) | Calendários Google habilitados — opções do seletor "Calendário" ao criar um evento (além de "Calendário interno", sempre |
| `_automation_summary_map` |  | [calendar_routes.py:98](../../../app/whatsapp_scheduler/web/calendar_routes.py#L98) | Uma consulta só pra saber quantas automações ATIVAS cada evento tem — evita N+1 na grade mensal (pode ter dezenas de eve |
| `_event_chip` |  | [calendar_routes.py:120](../../../app/whatsapp_scheduler/web/calendar_routes.py#L120) |  |
| `_grid_ctx` |  | [calendar_routes.py:131](../../../app/whatsapp_scheduler/web/calendar_routes.py#L131) |  |
| `_day_event_row` |  | [calendar_routes.py:160](../../../app/whatsapp_scheduler/web/calendar_routes.py#L160) |  |
| `_day_ctx` |  | [calendar_routes.py:172](../../../app/whatsapp_scheduler/web/calendar_routes.py#L172) |  |
| `_parse_date_str` |  | [calendar_routes.py:192](../../../app/whatsapp_scheduler/web/calendar_routes.py#L192) |  |
| `_load_event` |  | [calendar_routes.py:201](../../../app/whatsapp_scheduler/web/calendar_routes.py#L201) |  |
| `_event_detail_ctx` |  | [calendar_routes.py:208](../../../app/whatsapp_scheduler/web/calendar_routes.py#L208) |  |
| `_parse_local_dt` |  | [calendar_routes.py:228](../../../app/whatsapp_scheduler/web/calendar_routes.py#L228) |  |
| `_contacts_ctx` | async | [calendar_routes.py:235](../../../app/whatsapp_scheduler/web/calendar_routes.py#L235) |  |
| `_prefill_from_automation` |  | [calendar_routes.py:243](../../../app/whatsapp_scheduler/web/calendar_routes.py#L243) | Valores do formulário de EDIÇÃO a partir do que está gravado (+ o id do WhatsApp usado, pra pré-selecionar). Nada é rein |
| `_automation_modal_ctx` |  | [calendar_routes.py:294](../../../app/whatsapp_scheduler/web/calendar_routes.py#L294) | `form_values`: o que o usuário tinha digitado quando a validação falhou — o modal volta com tudo preenchido em vez de ze |
| `_submitted_form_values` |  | [calendar_routes.py:334](../../../app/whatsapp_scheduler/web/calendar_routes.py#L334) |  |
| `page_calendario` | rota | [calendar_routes.py:357](../../../app/whatsapp_scheduler/web/calendar_routes.py#L357) |  |
| `ui_grid` | rota | [calendar_routes.py:372](../../../app/whatsapp_scheduler/web/calendar_routes.py#L372) |  |
| `page_calendario_dia` | rota | [calendar_routes.py:389](../../../app/whatsapp_scheduler/web/calendar_routes.py#L389) |  |
| `ui_calendario_dia` | rota | [calendar_routes.py:404](../../../app/whatsapp_scheduler/web/calendar_routes.py#L404) |  |
| `ui_event_new` | rota | [calendar_routes.py:422](../../../app/whatsapp_scheduler/web/calendar_routes.py#L422) |  |
| `ui_event_detail` | rota | [calendar_routes.py:452](../../../app/whatsapp_scheduler/web/calendar_routes.py#L452) |  |
| `ui_event_edit` | rota | [calendar_routes.py:468](../../../app/whatsapp_scheduler/web/calendar_routes.py#L468) |  |
| `ui_event_delete_confirm` | rota | [calendar_routes.py:504](../../../app/whatsapp_scheduler/web/calendar_routes.py#L504) |  |
| `ui_event_create` | rota, async | [calendar_routes.py:530](../../../app/whatsapp_scheduler/web/calendar_routes.py#L530) |  |
| `ui_event_update` | rota, async | [calendar_routes.py:569](../../../app/whatsapp_scheduler/web/calendar_routes.py#L569) |  |
| `ui_event_delete` | rota, async | [calendar_routes.py:608](../../../app/whatsapp_scheduler/web/calendar_routes.py#L608) |  |
| `_resolve_waha_session` |  | [calendar_routes.py:634](../../../app/whatsapp_scheduler/web/calendar_routes.py#L634) | Sessão explicitamente escolhida no seletor "Enviar através de"; sem escolha (GET inicial do modal), cai pra conexão mais |
| `ui_calendario_contacts` | rota, async | [calendar_routes.py:647](../../../app/whatsapp_scheduler/web/calendar_routes.py#L647) | Lista de contatos do popover de destinatário — carregada à parte do resto do modal (v1.3): é a única coisa no modal de a |
| `ui_calendario_similar_events` | rota | [calendar_routes.py:671](../../../app/whatsapp_scheduler/web/calendar_routes.py#L671) | "Repetir esta automação em eventos iguais?" do modal de automação, em dois passos — a varredura de `similar_events` (tod |
| `ui_automation_new` | rota | [calendar_routes.py:712](../../../app/whatsapp_scheduler/web/calendar_routes.py#L712) |  |
| `ui_automation_edit` | rota | [calendar_routes.py:728](../../../app/whatsapp_scheduler/web/calendar_routes.py#L728) |  |
| `ui_automation_preview` | rota | [calendar_routes.py:747](../../../app/whatsapp_scheduler/web/calendar_routes.py#L747) | Horário calculado do disparo — pelo MESMO cálculo (`timing.py`) que grava o agendamento, então o que aparece aqui é exat |
| `ui_automation_create` | rota, async | [calendar_routes.py:797](../../../app/whatsapp_scheduler/web/calendar_routes.py#L797) |  |
| `ui_automation_create._create_for_all_targets` | aninhada | [calendar_routes.py:832](../../../app/whatsapp_scheduler/web/calendar_routes.py#L832) |  |
| `ui_automation_update` | rota, async | [calendar_routes.py:879](../../../app/whatsapp_scheduler/web/calendar_routes.py#L879) |  |
| `ui_automation_remove` | rota | [calendar_routes.py:934](../../../app/whatsapp_scheduler/web/calendar_routes.py#L934) |  |

## Templates desta funcionalidade

Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).

| Template | hx-* | Listeners JS | Handlers inline | Polling |
|---|---|---|---|---|
| [`_calendar_automation_modal.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_automation_modal.html) | 13 | 0 | 4 | 0 |
| [`_calendar_automation_preview.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_automation_preview.html) | 1 | 0 | 0 | 0 |
| [`_calendar_confirm_delete.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_confirm_delete.html) | 6 | 0 | 2 | 0 |
| [`_calendar_day_view.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_day_view.html) | 17 | 0 | 0 | 0 |
| [`_calendar_event_detail_modal.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_event_detail_modal.html) | 13 | 0 | 1 | 0 |
| [`_calendar_event_modal.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_event_modal.html) | 4 | 0 | 2 | 0 |
| [`_calendar_month_grid.html`](../../../app/whatsapp_scheduler/web/templates/_calendar_month_grid.html) | 13 | 0 | 2 | 0 |
| [`_contact_options.html`](../../../app/whatsapp_scheduler/web/templates/_contact_options.html) | 0 | 0 | 2 | 0 |
| [`_similar_events_box.html`](../../../app/whatsapp_scheduler/web/templates/_similar_events_box.html) | 4 | 0 | 0 | 0 |
| [`_similar_events_checklist.html`](../../../app/whatsapp_scheduler/web/templates/_similar_events_checklist.html) | 0 | 0 | 2 | 0 |
| [`calendario.html`](../../../app/whatsapp_scheduler/web/templates/calendario.html) | 2 | 0 | 2 | 0 |
| [`calendario_dia.html`](../../../app/whatsapp_scheduler/web/templates/calendario_dia.html) | 2 | 0 | 0 | 0 |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_calendar_providers.py`](../../../app/tests/test_calendar_providers.py) — 13 funções: `test_authorize_url_has_expected_params`, `test_exchange_code_returns_tokens`, `test_refresh_preserves_refresh_token_when_response_omits_it`, `test_refresh_raises_if_no_refresh_token_anywhere`, `test_list_calendars_maps_fields`, `test_bootstrap_sync_uses_time_bounds_no_sync_token`, `test_incremental_sync_uses_only_sync_token`, `test_expired_sync_token_returns_invalid_flag`, `test_pagination_follows_next_page_token`, `test_event_mapping_all_day_and_cancelled`, `test_create_event_posts_body_and_returns_external_id`, `test_update_event_patches_existing_id_never_creates`, `test_delete_event_treats_404_as_already_gone`
- [`app/tests/test_calendar_service.py`](../../../app/tests/test_calendar_service.py) — 45 funções: `test_missing_config_lists_exact_env_vars_when_unconfigured`, `test_start_connect_works_when_configured`, `test_create_event_automation_creates_one_message_one_schedule_and_link`, `test_create_event_automation_multiple_recipients_creates_one_schedule_each`, `test_create_event_automation_rejects_unknown_event`, `test_create_event_automation_rejects_empty_messages`, `test_create_event_automation_custom_persists_time_and_computes_dispatch`, `test_create_event_automation_custom_requires_time`, `test_create_event_automation_custom_rejects_malformed_time`, `test_create_event_automation_non_custom_ignores_stray_custom_time`, `test_multi_message_automation_chains_schedules_by_recipient_with_dependency`, `test_reschedule_preserves_per_message_gap`, `test_remove_event_automation_cancels_schedules_but_keeps_event`, `test_disconnect_cancels_pending_but_preserves_sent_history`, `test_month_grid_always_has_42_cells`, `test_month_grid_places_event_on_correct_local_day`, `test_month_grid_buckets_by_event_own_timezone_not_default`, `test_day_events_returns_only_events_of_that_local_day`, `test_day_events_buckets_by_event_own_timezone_not_the_requested_one`, `test_day_events_ordered_chronologically`, `test_similar_events_matches_by_recurring_event_id_when_present`, `test_similar_events_falls_back_to_title_match_for_internal_events`, `test_similar_events_excludes_past_and_cancelled`, `test_similar_events_never_crosses_users`, `test_create_internal_event_validates_fields`, `test_update_internal_event_reschedules_pending_dispatch_in_place`, `test_update_internal_event_does_not_touch_already_sent_dispatch`, `test_update_internal_event_rejects_google_sourced_event`, `test_delete_internal_event_cancels_automations_and_preserves_schedule_history`, `test_delete_internal_event_rejects_google_sourced_event`, `test_update_event_automation_does_not_leave_ghost_row_and_keeps_old_schedule_untouched`, `test_create_event_automation_is_idempotent_for_identical_immediate_resubmit`, `test_duplicate_guard_multi_message_resubmit_does_not_violate_unique_constraint`, `test_edit_flow_not_blocked_by_duplicate_guard_even_with_near_identical_values`, `test_migrate_legacy_automations_is_idempotent_and_preserves_schedule`, `test_create_internal_event_pushes_to_google_and_links`, `test_create_internal_event_survives_google_push_failure`, `test_update_internal_event_rejects_local_change_when_google_push_fails`, `test_delete_internal_event_keeps_local_row_when_google_delete_fails`, `test_delete_internal_event_google_failure_leaves_automations_intact`, `test_create_internal_event_with_unavailable_target_calendar_creates_nothing`, `test_delete_internal_event_app_only_leaves_google_event_alone`, `test_set_timezone_updates_settings_and_persists_across_reload`, `test_set_timezone_rejects_invalid_and_leaves_setting_untouched`, `test_set_timezone_does_not_touch_already_created_schedule_timezone`
- [`app/tests/test_calendar_sync.py`](../../../app/tests/test_calendar_sync.py) — 15 funções: `test_first_sync_imports_events_using_time_bounds`, `test_incremental_sync_uses_stored_sync_token`, `test_event_time_change_reschedules_same_dispatch_without_duplicating`, `test_time_change_with_no_pending_dispatch_is_noop`, `test_dispatch_already_processing_is_not_overwritten_by_reschedule`, `test_cancelled_event_cancels_open_dispatch_and_keeps_event_row`, `test_sent_dispatch_untouched_after_event_cancelled`, `test_expired_sync_token_triggers_full_resync`, `test_disabled_calendar_is_skipped_by_sync_connection`, `test_sync_connection_syncs_enabled_calendars_only`, `test_target_utc_for_offset_custom_uses_event_local_date_and_chosen_time`, `test_target_utc_for_offset_custom_tracks_event_date_when_event_moves_day`, `test_target_utc_for_offset_custom_requires_custom_time_local`, `test_target_utc_for_message_custom_still_applies_position_gap`, `test_custom_automation_recomputed_when_event_date_changes`
- [`app/tests/test_calendar_web.py`](../../../app/tests/test_calendar_web.py) — 19 funções: `test_month_grid_hoje_button_links_to_day_view`, `test_day_view_page_shows_todays_event`, `test_day_view_partial_navigates_between_days`, `test_day_view_does_not_leak_other_days_events`, `test_automation_modal_shows_repeat_toggle_defaulting_to_no_without_querying_similar_events`, `test_choosing_sim_opens_the_box_first_without_running_the_search`, `test_similar_events_search_step_lists_future_matches`, `test_similar_events_search_step_empty_state_when_no_matches`, `test_lazy_similar_events_endpoint_returns_nothing_and_skips_the_query_when_repeat_choice_is_not_sim`, `test_lazy_similar_events_endpoint_ignored_for_another_users_event`, `test_create_automation_applies_to_selected_similar_events`, `test_create_automation_ignores_unrelated_event_id_even_if_submitted`, `test_create_automation_ignores_another_users_event_id_even_if_submitted`, `test_bulk_automation_creation_is_offloaded_to_a_worker_thread`, `test_opening_automation_modal_never_calls_waha_for_contacts`, `test_automation_modal_popover_points_to_the_lazy_contacts_endpoint`, `test_lazy_contacts_endpoint_returns_contacts_for_the_given_whatsapp`, `test_lazy_contacts_endpoint_ignored_for_unowned_whatsapp_session`, `test_edit_automation_modal_pins_down_whatsapp_and_prefill_ids_for_the_lazy_fetch`
