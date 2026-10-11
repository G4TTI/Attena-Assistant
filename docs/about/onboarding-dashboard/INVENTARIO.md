# Onboarding e Dashboard — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/dashboard_service.py`](../../../app/whatsapp_scheduler/dashboard_service.py) | 275 |
| [`app/whatsapp_scheduler/onboarding_service.py`](../../../app/whatsapp_scheduler/onboarding_service.py) | 76 |
| [`app/whatsapp_scheduler/web/dashboard_routes.py`](../../../app/whatsapp_scheduler/web/dashboard_routes.py) | 138 |
| [`app/whatsapp_scheduler/web/onboarding_routes.py`](../../../app/whatsapp_scheduler/web/onboarding_routes.py) | 137 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_onboarding.py`](../../../app/tests/test_onboarding.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/` | `page_dashboard` | [dashboard_routes.py:102](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L102) |
| GET | `/ui/dashboard/summary` | `ui_dashboard_summary` | [dashboard_routes.py:119](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L119) |
| POST | `/ui/dashboard/calendar-card/sync` | `ui_dashboard_calendar_sync` | [dashboard_routes.py:128](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L128) |
| GET | `/onboarding` | `page_onboarding` | [onboarding_routes.py:41](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L41) |
| GET | `/ui/onboarding/whatsapp` | `ui_onboarding_whatsapp` | [onboarding_routes.py:53](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L53) |
| POST | `/onboarding/whatsapp/start` | `ui_onboarding_whatsapp_start` | [onboarding_routes.py:69](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L69) |
| POST | `/onboarding/timezone` | `ui_onboarding_timezone` | [onboarding_routes.py:97](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L97) |
| GET | `/onboarding/pular` | `ui_onboarding_skip` | [onboarding_routes.py:122](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L122) |
| POST | `/onboarding/finish` | `ui_onboarding_finish` | [onboarding_routes.py:132](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L132) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `today_local_date` |  | [dashboard_service.py:40](../../../app/whatsapp_scheduler/dashboard_service.py#L40) |  |
| `_local_day_bounds_utc` |  | [dashboard_service.py:44](../../../app/whatsapp_scheduler/dashboard_service.py#L44) |  |
| `today_events` |  | [dashboard_service.py:53](../../../app/whatsapp_scheduler/dashboard_service.py#L53) | Eventos de hoje, em qualquer calendário — reaproveita o mesmo bucketing por dia/timezone que a grade do Calendário já us |
| `upcoming_today_count` |  | [dashboard_service.py:66](../../../app/whatsapp_scheduler/dashboard_service.py#L66) |  |
| `upcoming_events` |  | [dashboard_service.py:71](../../../app/whatsapp_scheduler/dashboard_service.py#L71) | Próximos eventos (qualquer dia), em ordem cronológica. |
| `scheduled_dispatches` |  | [dashboard_service.py:90](../../../app/whatsapp_scheduler/dashboard_service.py#L90) |  |
| `sent_count_on` |  | [dashboard_service.py:102](../../../app/whatsapp_scheduler/dashboard_service.py#L102) |  |
| `failed_count_on` |  | [dashboard_service.py:116](../../../app/whatsapp_scheduler/dashboard_service.py#L116) |  |
| `_group_info` |  | [dashboard_service.py:130](../../../app/whatsapp_scheduler/dashboard_service.py#L130) | (quantas mensagens tem o agendamento a que este `Schedule` pertence, nome do destinatário — decifrado em memória, só par |
| `_media_label` |  | [dashboard_service.py:141](../../../app/whatsapp_scheduler/dashboard_service.py#L141) |  |
| `upcoming_dispatch_rows` |  | [dashboard_service.py:146](../../../app/whatsapp_scheduler/dashboard_service.py#L146) | `tz_name`: fuso do USUÁRIO — o horário mostrado é sempre nele (o mesmo das outras telas), não no fuso guardado em cada s |
| `recent_activity` |  | [dashboard_service.py:175](../../../app/whatsapp_scheduler/dashboard_service.py#L175) |  |
| `has_any_activity` |  | [dashboard_service.py:236](../../../app/whatsapp_scheduler/dashboard_service.py#L236) | Já existe QUALQUER schedule, evento ou automação deste usuário, alguma vez (não só hoje/futuro)? Usado só pra decidir se |
| `relative_label` |  | [dashboard_service.py:256](../../../app/whatsapp_scheduler/dashboard_service.py#L256) |  |
| `primary_calendar_connection` |  | [dashboard_service.py:273](../../../app/whatsapp_scheduler/dashboard_service.py#L273) |  |
| `migrate_legacy_users` |  | [onboarding_service.py:23](../../../app/whatsapp_scheduler/onboarding_service.py#L23) | Idempotente, roda uma única vez no boot desta versão (mesmo padrão de `db.claim_orphan_data`, com uma flag em `AppSettin |
| `progress` | async | [onboarding_service.py:44](../../../app/whatsapp_scheduler/onboarding_service.py#L44) | Estado ao vivo das 3 etapas — sempre recalculado, nunca cacheado (mesma escolha de `whatsapp_service.status_rows`). |
| `first_incomplete_step` |  | [onboarding_service.py:61](../../../app/whatsapp_scheduler/onboarding_service.py#L61) | 1=WhatsApp, 2=Google Agenda, 3=Fuso horário, 4=Concluído. |
| `finish` |  | [onboarding_service.py:72](../../../app/whatsapp_scheduler/onboarding_service.py#L72) |  |
| `_format_date_long_pt` |  | [dashboard_routes.py:34](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L34) |  |
| `_greeting_name` |  | [dashboard_routes.py:38](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L38) | Primeiro nome do perfil da primeira conexão WhatsApp conectada (session.me.pushName) — dado real da sessão WAHA, não um  |
| `_event_row` |  | [dashboard_routes.py:52](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L52) |  |
| `_summary_ctx` | async | [dashboard_routes.py:57](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L57) | Tudo que é dinâmico no Dashboard — cards, listas e os cards de status (WhatsApp/Google Agenda). Usado tanto no primeiro  |
| `page_dashboard` | rota, async | [dashboard_routes.py:103](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L103) |  |
| `ui_dashboard_summary` | rota, async | [dashboard_routes.py:120](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L120) |  |
| `ui_dashboard_calendar_sync` | rota, async | [dashboard_routes.py:129](../../../app/whatsapp_scheduler/web/dashboard_routes.py#L129) |  |
| `_waha` |  | [onboarding_routes.py:25](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L25) |  |
| `_ctx` | async | [onboarding_routes.py:29](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L29) |  |
| `page_onboarding` | rota, async | [onboarding_routes.py:42](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L42) |  |
| `ui_onboarding_whatsapp` | rota, async | [onboarding_routes.py:54](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L54) | Atualização periódica do passo. `sig` é a assinatura do que a tela já mostra: se nada mudou, 204 (o htmx não troca nada) |
| `ui_onboarding_whatsapp_start` | rota, async | [onboarding_routes.py:70](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L70) |  |
| `ui_onboarding_timezone` | rota, async | [onboarding_routes.py:98](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L98) |  |
| `ui_onboarding_skip` | rota, async | [onboarding_routes.py:123](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L123) |  |
| `ui_onboarding_finish` | rota | [onboarding_routes.py:133](../../../app/whatsapp_scheduler/web/onboarding_routes.py#L133) |  |

## Templates desta funcionalidade

Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).

| Template | hx-* | Listeners JS | Handlers inline | Polling |
|---|---|---|---|---|
| [`_dashboard_calendar_card.html`](../../../app/whatsapp_scheduler/web/templates/_dashboard_calendar_card.html) | 3 | 0 | 0 | 0 |
| [`_dashboard_summary.html`](../../../app/whatsapp_scheduler/web/templates/_dashboard_summary.html) | 8 | 0 | 0 | 0 |
| [`_dashboard_whatsapp_card.html`](../../../app/whatsapp_scheduler/web/templates/_dashboard_whatsapp_card.html) | 0 | 0 | 0 | 0 |
| [`_onboarding_whatsapp_step.html`](../../../app/whatsapp_scheduler/web/templates/_onboarding_whatsapp_step.html) | 7 | 0 | 0 | 1 |
| [`dashboard.html`](../../../app/whatsapp_scheduler/web/templates/dashboard.html) | 3 | 0 | 0 | 0 |
| [`onboarding.html`](../../../app/whatsapp_scheduler/web/templates/onboarding.html) | 0 | 0 | 0 | 0 |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_onboarding.py`](../../../app/tests/test_onboarding.py) — 24 funções: `test_migrate_legacy_users_marks_existing_accounts_as_done_and_is_idempotent`, `test_first_incomplete_step_progression`, `test_fresh_user_is_redirected_to_onboarding`, `test_onboarding_page_defaults_to_first_step`, `test_skip_whatsapp_step_advances_to_google`, `test_whatsapp_step_form_has_phone_field`, `test_starting_pairing_saves_the_phone_number`, `test_set_timezone_persists_and_advances_to_done`, `test_invalid_timezone_shows_error_and_stays_on_step_3`, `test_finish_marks_completed_and_unblocks_the_rest_of_the_app`, `test_api_and_htmx_partials_are_never_redirected_while_onboarding_pending`, `test_opening_onboarding_creates_the_missing_waha_session`, `test_polling_the_whatsapp_step_does_not_create_the_session_twice`, `test_qr_image_only_appears_once_waha_has_a_qr`, `test_start_pairing_works_without_a_phone_number`, `test_start_pairing_shows_the_waha_error_instead_of_swallowing_it`, `test_passive_status_polling_never_creates_sessions`, `test_failed_session_offers_a_way_to_generate_a_new_qr`, `test_qr_image_is_preserved_across_the_periodic_refresh`, `test_qr_image_has_no_src_in_the_html_so_polls_do_not_redownload_it`, `test_periodic_poll_returns_204_when_nothing_changed`, `test_poll_renders_again_as_soon_as_the_state_changes`, `test_polling_container_is_marked_so_it_does_not_flip_the_buttons_label`, `test_new_qr_is_decoded_before_it_replaces_the_old_one_and_identical_qr_is_skipped`
