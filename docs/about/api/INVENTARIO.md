# API REST — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/api/__init__.py`](../../../app/whatsapp_scheduler/api/__init__.py) | 0 |
| [`app/whatsapp_scheduler/api/calendar.py`](../../../app/whatsapp_scheduler/api/calendar.py) | 129 |
| [`app/whatsapp_scheduler/api/chats.py`](../../../app/whatsapp_scheduler/api/chats.py) | 87 |
| [`app/whatsapp_scheduler/api/schedules.py`](../../../app/whatsapp_scheduler/api/schedules.py) | 106 |
| [`app/whatsapp_scheduler/api/session.py`](../../../app/whatsapp_scheduler/api/session.py) | 139 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_api.py`](../../../app/tests/test_api.py), [`app/tests/test_calendar_api.py`](../../../app/tests/test_calendar_api.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/api/calendar/connections` | `list_connections` | [calendar.py:18](../../../app/whatsapp_scheduler/api/calendar.py#L18) |
| DELETE | `/api/calendar/connections/{connection_id}` | `disconnect` | [calendar.py:25](../../../app/whatsapp_scheduler/api/calendar.py#L25) |
| POST | `/api/calendar/connections/{connection_id}/sync` | `sync_now` | [calendar.py:34](../../../app/whatsapp_scheduler/api/calendar.py#L34) |
| GET | `/api/calendar/connections/{connection_id}/calendars` | `list_calendars` | [calendar.py:44](../../../app/whatsapp_scheduler/api/calendar.py#L44) |
| POST | `/api/calendar/calendars/{calendar_id}/toggle` | `toggle_calendar` | [calendar.py:51](../../../app/whatsapp_scheduler/api/calendar.py#L51) |
| GET | `/api/calendar/events` | `list_events` | [calendar.py:64](../../../app/whatsapp_scheduler/api/calendar.py#L64) |
| POST | `/api/calendar/events/{event_id}/automations` | `create_automation` | [calendar.py:77](../../../app/whatsapp_scheduler/api/calendar.py#L77) |
| DELETE | `/api/calendar/automations/{automation_id}` | `delete_automation` | [calendar.py:123](../../../app/whatsapp_scheduler/api/calendar.py#L123) |
| GET | `/api/whatsapp-sessions/{session_id}/chats` | `chats` | [chats.py:30](../../../app/whatsapp_scheduler/api/chats.py#L30) |
| GET | `/api/whatsapp-sessions/{session_id}/chats/messages` | `messages` | [chats.py:47](../../../app/whatsapp_scheduler/api/chats.py#L47) |
| POST | `/api/whatsapp-sessions/{session_id}/chats/send` | `send` | [chats.py:70](../../../app/whatsapp_scheduler/api/chats.py#L70) |
| POST | `/api/schedules` | `create` | [schedules.py:34](../../../app/whatsapp_scheduler/api/schedules.py#L34) |
| GET | `/api/schedules` | `list_schedules` | [schedules.py:69](../../../app/whatsapp_scheduler/api/schedules.py#L69) |
| GET | `/api/schedules/{schedule_id}` | `get_schedule` | [schedules.py:82](../../../app/whatsapp_scheduler/api/schedules.py#L82) |
| DELETE | `/api/schedules/{schedule_id}` | `delete_schedule` | [schedules.py:90](../../../app/whatsapp_scheduler/api/schedules.py#L90) |
| POST | `/api/schedules/{schedule_id}/run-now` | `trigger_now` | [schedules.py:99](../../../app/whatsapp_scheduler/api/schedules.py#L99) |
| GET | `/api/whatsapp-sessions` | `list_sessions` | [session.py:39](../../../app/whatsapp_scheduler/api/session.py#L39) |
| POST | `/api/whatsapp-sessions` | `create_session` | [session.py:49](../../../app/whatsapp_scheduler/api/session.py#L49) |
| GET | `/api/whatsapp-sessions/{session_id}` | `session_status` | [session.py:63](../../../app/whatsapp_scheduler/api/session.py#L63) |
| GET | `/api/whatsapp-sessions/{session_id}/qr` | `session_qr` | [session.py:85](../../../app/whatsapp_scheduler/api/session.py#L85) |
| POST | `/api/whatsapp-sessions/{session_id}/start` | `session_start` | [session.py:100](../../../app/whatsapp_scheduler/api/session.py#L100) |
| POST | `/api/whatsapp-sessions/{session_id}/rename` | `rename_session` | [session.py:117](../../../app/whatsapp_scheduler/api/session.py#L117) |
| DELETE | `/api/whatsapp-sessions/{session_id}` | `disconnect_session` | [session.py:130](../../../app/whatsapp_scheduler/api/session.py#L130) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `WhatsAppSessionCreate` | BaseModel | [session.py:20](../../../app/whatsapp_scheduler/api/session.py#L20) |
| `WhatsAppSessionRename` | BaseModel | [session.py:24](../../../app/whatsapp_scheduler/api/session.py#L24) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `list_connections` | rota | [calendar.py:19](../../../app/whatsapp_scheduler/api/calendar.py#L19) |  |
| `disconnect` | rota, async | [calendar.py:26](../../../app/whatsapp_scheduler/api/calendar.py#L26) |  |
| `sync_now` | rota, async | [calendar.py:35](../../../app/whatsapp_scheduler/api/calendar.py#L35) |  |
| `list_calendars` | rota | [calendar.py:45](../../../app/whatsapp_scheduler/api/calendar.py#L45) |  |
| `toggle_calendar` | rota | [calendar.py:52](../../../app/whatsapp_scheduler/api/calendar.py#L52) |  |
| `list_events` | rota | [calendar.py:65](../../../app/whatsapp_scheduler/api/calendar.py#L65) |  |
| `create_automation` | rota | [calendar.py:78](../../../app/whatsapp_scheduler/api/calendar.py#L78) |  |
| `delete_automation` | rota | [calendar.py:124](../../../app/whatsapp_scheduler/api/calendar.py#L124) |  |
| `_waha` |  | [chats.py:19](../../../app/whatsapp_scheduler/api/chats.py#L19) |  |
| `_owned` |  | [chats.py:23](../../../app/whatsapp_scheduler/api/chats.py#L23) |  |
| `chats` | rota, async | [chats.py:31](../../../app/whatsapp_scheduler/api/chats.py#L31) |  |
| `messages` | rota, async | [chats.py:48](../../../app/whatsapp_scheduler/api/chats.py#L48) |  |
| `send` | rota, async | [chats.py:71](../../../app/whatsapp_scheduler/api/chats.py#L71) |  |
| `_load` |  | [schedules.py:17](../../../app/whatsapp_scheduler/api/schedules.py#L17) |  |
| `_dispatches` |  | [schedules.py:24](../../../app/whatsapp_scheduler/api/schedules.py#L24) |  |
| `create` | rota | [schedules.py:35](../../../app/whatsapp_scheduler/api/schedules.py#L35) |  |
| `list_schedules` | rota | [schedules.py:70](../../../app/whatsapp_scheduler/api/schedules.py#L70) |  |
| `get_schedule` | rota | [schedules.py:83](../../../app/whatsapp_scheduler/api/schedules.py#L83) |  |
| `delete_schedule` | rota | [schedules.py:91](../../../app/whatsapp_scheduler/api/schedules.py#L91) |  |
| `trigger_now` | rota | [schedules.py:100](../../../app/whatsapp_scheduler/api/schedules.py#L100) |  |
| `_waha` |  | [session.py:28](../../../app/whatsapp_scheduler/api/session.py#L28) |  |
| `_owned` |  | [session.py:32](../../../app/whatsapp_scheduler/api/session.py#L32) |  |
| `list_sessions` | rota | [session.py:40](../../../app/whatsapp_scheduler/api/session.py#L40) |  |
| `create_session` | rota | [session.py:50](../../../app/whatsapp_scheduler/api/session.py#L50) |  |
| `session_status` | rota, async | [session.py:64](../../../app/whatsapp_scheduler/api/session.py#L64) |  |
| `session_qr` | rota, async | [session.py:86](../../../app/whatsapp_scheduler/api/session.py#L86) |  |
| `session_start` | rota, async | [session.py:101](../../../app/whatsapp_scheduler/api/session.py#L101) |  |
| `rename_session` | rota | [session.py:118](../../../app/whatsapp_scheduler/api/session.py#L118) |  |
| `disconnect_session` | rota, async | [session.py:131](../../../app/whatsapp_scheduler/api/session.py#L131) |  |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_api.py`](../../../app/tests/test_api.py) — 18 funções: `test_healthz`, `test_create_and_list`, `test_create_rejects_bad_recipient`, `test_create_rejects_bad_recurrence`, `test_get_missing_is_404`, `test_delete_cancels`, `test_run_now_creates_immediate_dispatch`, `test_session_status_and_qr`, `test_session_start_restarts_a_failed_session`, `test_session_status_and_start_404_for_unowned_session`, `test_ui_whatsapp_start_renders_updated_list_with_feedback`, `test_ui_whatsapp_start_shows_error_when_waha_unreachable`, `test_agendamentos_page_renders`, `test_dashboard_is_now_the_index_page`, `test_dashboard_shows_welcome_block_for_brand_new_user_with_no_activity`, `test_dashboard_shows_stat_cards_once_user_has_activity`, `test_dashboard_summary_partial_renders_standalone`, `test_dashboard_does_not_auto_poll_inside_modal_trigger_scope`
- [`app/tests/test_calendar_api.py`](../../../app/tests/test_calendar_api.py) — 7 funções: `test_list_connections_never_exposes_tokens`, `test_toggle_calendar`, `test_create_automation_produces_one_of_each`, `test_delete_automation_cancels_without_deleting_event`, `test_create_automation_with_multiple_messages_and_recipients`, `test_create_automation_rejects_empty_recipients`, `test_disconnect_connection`
