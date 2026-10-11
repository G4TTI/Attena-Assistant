# Configurações e Conexões — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/web/settings_routes.py`](../../../app/whatsapp_scheduler/web/settings_routes.py) | 306 |
| [`app/whatsapp_scheduler/web/whatsapp_routes.py`](../../../app/whatsapp_scheduler/web/whatsapp_routes.py) | 155 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_configuracoes.py`](../../../app/tests/test_configuracoes.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/configuracoes` | `page_configuracoes` | [settings_routes.py:91](../../../app/whatsapp_scheduler/web/settings_routes.py#L91) |
| GET | `/ui/configuracoes/connections` | `ui_connections` | [settings_routes.py:109](../../../app/whatsapp_scheduler/web/settings_routes.py#L109) |
| POST | `/configuracoes/preferencias/timezone` | `ui_set_timezone` | [settings_routes.py:119](../../../app/whatsapp_scheduler/web/settings_routes.py#L119) |
| GET | `/ui/configuracoes/relogio` | `ui_clock` | [settings_routes.py:145](../../../app/whatsapp_scheduler/web/settings_routes.py#L145) |
| POST | `/configuracoes/google/connect` | `connect_google` | [settings_routes.py:150](../../../app/whatsapp_scheduler/web/settings_routes.py#L150) |
| GET | `/calendario/oauth/callback` | `google_oauth_callback` | [settings_routes.py:164](../../../app/whatsapp_scheduler/web/settings_routes.py#L164) |
| POST | `/ui/configuracoes/calendars/{calendar_id}/toggle` | `ui_toggle_calendar` | [settings_routes.py:204](../../../app/whatsapp_scheduler/web/settings_routes.py#L204) |
| POST | `/ui/configuracoes/connections/{connection_id}/sync` | `ui_sync_now` | [settings_routes.py:219](../../../app/whatsapp_scheduler/web/settings_routes.py#L219) |
| POST | `/ui/configuracoes/connections/{connection_id}/disconnect` | `ui_disconnect` | [settings_routes.py:233](../../../app/whatsapp_scheduler/web/settings_routes.py#L233) |
| POST | `/configuracoes/conta/perfil` | `ui_update_profile` | [settings_routes.py:253](../../../app/whatsapp_scheduler/web/settings_routes.py#L253) |
| POST | `/configuracoes/conta/senha` | `ui_change_password` | [settings_routes.py:272](../../../app/whatsapp_scheduler/web/settings_routes.py#L272) |
| POST | `/configuracoes/conta/sair-outros-dispositivos` | `ui_logout_other_sessions` | [settings_routes.py:297](../../../app/whatsapp_scheduler/web/settings_routes.py#L297) |
| GET | `/whatsapps` | `page_whatsapps` | [whatsapp_routes.py:30](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L30) |
| GET | `/ui/whatsapps` | `ui_whatsapps` | [whatsapp_routes.py:38](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L38) |
| GET | `/ui/whatsapp-picker-options` | `ui_whatsapp_picker_options` | [whatsapp_routes.py:53](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L53) |
| POST | `/whatsapps` | `ui_whatsapp_create` | [whatsapp_routes.py:76](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L76) |
| POST | `/whatsapps/{session_id}/start` | `ui_whatsapp_start` | [whatsapp_routes.py:96](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L96) |
| POST | `/whatsapps/{session_id}/rename` | `ui_whatsapp_rename` | [whatsapp_routes.py:118](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L118) |
| POST | `/whatsapps/{session_id}/disconnect` | `ui_whatsapp_disconnect` | [whatsapp_routes.py:130](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L130) |
| GET | `/ui/whatsapps/{session_id}/qr` | `ui_whatsapp_qr` | [whatsapp_routes.py:141](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L141) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `_ctx` |  | [settings_routes.py:45](../../../app/whatsapp_scheduler/web/settings_routes.py#L45) |  |
| `_whatsapp_ctx` | async | [settings_routes.py:54](../../../app/whatsapp_scheduler/web/settings_routes.py#L54) |  |
| `_connections_ctx` |  | [settings_routes.py:59](../../../app/whatsapp_scheduler/web/settings_routes.py#L59) |  |
| `_preferences_ctx` |  | [settings_routes.py:76](../../../app/whatsapp_scheduler/web/settings_routes.py#L76) |  |
| `page_configuracoes` | rota, async | [settings_routes.py:92](../../../app/whatsapp_scheduler/web/settings_routes.py#L92) |  |
| `ui_connections` | rota | [settings_routes.py:110](../../../app/whatsapp_scheduler/web/settings_routes.py#L110) |  |
| `ui_set_timezone` | rota | [settings_routes.py:120](../../../app/whatsapp_scheduler/web/settings_routes.py#L120) |  |
| `ui_clock` | rota | [settings_routes.py:146](../../../app/whatsapp_scheduler/web/settings_routes.py#L146) |  |
| `connect_google` | rota | [settings_routes.py:151](../../../app/whatsapp_scheduler/web/settings_routes.py#L151) |  |
| `google_oauth_callback` | rota, async | [settings_routes.py:165](../../../app/whatsapp_scheduler/web/settings_routes.py#L165) |  |
| `ui_toggle_calendar` | rota | [settings_routes.py:205](../../../app/whatsapp_scheduler/web/settings_routes.py#L205) |  |
| `ui_sync_now` | rota, async | [settings_routes.py:220](../../../app/whatsapp_scheduler/web/settings_routes.py#L220) |  |
| `ui_disconnect` | rota, async | [settings_routes.py:234](../../../app/whatsapp_scheduler/web/settings_routes.py#L234) |  |
| `ui_update_profile` | rota | [settings_routes.py:254](../../../app/whatsapp_scheduler/web/settings_routes.py#L254) |  |
| `ui_change_password` | rota | [settings_routes.py:273](../../../app/whatsapp_scheduler/web/settings_routes.py#L273) |  |
| `ui_logout_other_sessions` | rota | [settings_routes.py:298](../../../app/whatsapp_scheduler/web/settings_routes.py#L298) |  |
| `_waha` |  | [whatsapp_routes.py:21](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L21) |  |
| `_list_ctx` | async | [whatsapp_routes.py:25](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L25) |  |
| `page_whatsapps` | rota | [whatsapp_routes.py:31](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L31) | WhatsApps deixou de ser um destino próprio na sidebar — vira a aba "Conexões" de Configurações (junto com Calendários).  |
| `ui_whatsapps` | rota, async | [whatsapp_routes.py:39](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L39) | Atualização periódica da lista de conexões: 204 quando nada mudou desde a última renderização (`sig`), pra a lista, os b |
| `ui_whatsapp_picker_options` | rota, async | [whatsapp_routes.py:54](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L54) | `<option>`s do seletor "Enviar através de" com o status ao vivo — só os WhatsApps do usuário autenticado. Carregado à pa |
| `ui_whatsapp_create` | rota, async | [whatsapp_routes.py:77](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L77) |  |
| `ui_whatsapp_start` | rota, async | [whatsapp_routes.py:97](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L97) |  |
| `ui_whatsapp_rename` | rota, async | [whatsapp_routes.py:119](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L119) |  |
| `ui_whatsapp_disconnect` | rota, async | [whatsapp_routes.py:131](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L131) |  |
| `ui_whatsapp_qr` | rota, async | [whatsapp_routes.py:142](../../../app/whatsapp_scheduler/web/whatsapp_routes.py#L142) |  |

## Templates desta funcionalidade

Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).

| Template | hx-* | Listeners JS | Handlers inline | Polling |
|---|---|---|---|---|
| [`_connections.html`](../../../app/whatsapp_scheduler/web/templates/_connections.html) | 10 | 0 | 0 | 0 |
| [`_preferences.html`](../../../app/whatsapp_scheduler/web/templates/_preferences.html) | 8 | 0 | 0 | 1 |
| [`_whatsapp_list.html`](../../../app/whatsapp_scheduler/web/templates/_whatsapp_list.html) | 18 | 0 | 0 | 0 |
| [`_whatsapp_picker_options.html`](../../../app/whatsapp_scheduler/web/templates/_whatsapp_picker_options.html) | 1 | 0 | 0 | 0 |
| [`configuracoes.html`](../../../app/whatsapp_scheduler/web/templates/configuracoes.html) | 0 | 0 | 2 | 0 |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_configuracoes.py`](../../../app/tests/test_configuracoes.py) — 9 funções: `test_configuracoes_page_has_both_tabs_in_one_response`, `test_whatsapps_route_redirects_to_configuracoes_conexoes_tab`, `test_dashboard_no_longer_links_the_old_whatsapps_page`, `test_connections_list_polls_fast_until_the_whatsapp_is_connected`, `test_connections_list_only_shows_the_qr_when_waha_has_one`, `test_connections_list_keeps_polling_after_a_waha_error`, `test_connections_list_preserves_the_qr_image_across_polls`, `test_connections_list_qr_image_has_no_src_in_the_html`, `test_connections_list_poll_returns_204_when_nothing_changed`
