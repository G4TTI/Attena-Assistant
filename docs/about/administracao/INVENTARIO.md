# Administração — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/admin/__init__.py`](../../../app/whatsapp_scheduler/admin/__init__.py) | 7 |
| [`app/whatsapp_scheduler/admin/access.py`](../../../app/whatsapp_scheduler/admin/access.py) | 82 |
| [`app/whatsapp_scheduler/admin/crm.py`](../../../app/whatsapp_scheduler/admin/crm.py) | 194 |
| [`app/whatsapp_scheduler/admin/security.py`](../../../app/whatsapp_scheduler/admin/security.py) | 110 |
| [`app/whatsapp_scheduler/admin/service.py`](../../../app/whatsapp_scheduler/admin/service.py) | 699 |
| [`app/whatsapp_scheduler/web/admin_routes.py`](../../../app/whatsapp_scheduler/web/admin_routes.py) | 549 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_admin.py`](../../../app/tests/test_admin.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/admin` | `admin_dashboard` | [admin_routes.py:71](../../../app/whatsapp_scheduler/web/admin_routes.py#L71) |
| GET | `/admin/usuarios` | `admin_users` | [admin_routes.py:85](../../../app/whatsapp_scheduler/web/admin_routes.py#L85) |
| GET | `/admin/usuarios/{user_id}` | `admin_user_detail` | [admin_routes.py:117](../../../app/whatsapp_scheduler/web/admin_routes.py#L117) |
| POST | `/admin/usuarios/{user_id}/crm/status` | `admin_set_crm_status` | [admin_routes.py:159](../../../app/whatsapp_scheduler/web/admin_routes.py#L159) |
| POST | `/admin/usuarios/{user_id}/crm/tags` | `admin_add_tag` | [admin_routes.py:175](../../../app/whatsapp_scheduler/web/admin_routes.py#L175) |
| POST | `/admin/usuarios/{user_id}/crm/tags/{tag_id}/remover` | `admin_remove_tag` | [admin_routes.py:201](../../../app/whatsapp_scheduler/web/admin_routes.py#L201) |
| POST | `/admin/usuarios/{user_id}/crm/notas` | `admin_add_note` | [admin_routes.py:212](../../../app/whatsapp_scheduler/web/admin_routes.py#L212) |
| POST | `/admin/usuarios/{user_id}/crm/notas/{note_id}` | `admin_update_note` | [admin_routes.py:229](../../../app/whatsapp_scheduler/web/admin_routes.py#L229) |
| POST | `/admin/usuarios/{user_id}/crm/notas/{note_id}/excluir` | `admin_delete_note` | [admin_routes.py:246](../../../app/whatsapp_scheduler/web/admin_routes.py#L246) |
| POST | `/admin/usuarios/{user_id}/suspender` | `admin_suspend` | [admin_routes.py:256](../../../app/whatsapp_scheduler/web/admin_routes.py#L256) |
| POST | `/admin/usuarios/{user_id}/reativar` | `admin_reactivate` | [admin_routes.py:277](../../../app/whatsapp_scheduler/web/admin_routes.py#L277) |
| POST | `/admin/usuarios/{user_id}/plano` | `admin_change_plan` | [admin_routes.py:294](../../../app/whatsapp_scheduler/web/admin_routes.py#L294) |
| GET | `/admin/crm` | `admin_crm` | [admin_routes.py:324](../../../app/whatsapp_scheduler/web/admin_routes.py#L324) |
| POST | `/admin/crm/tags` | `admin_create_tag` | [admin_routes.py:349](../../../app/whatsapp_scheduler/web/admin_routes.py#L349) |
| POST | `/admin/crm/tags/{tag_id}/excluir` | `admin_delete_tag` | [admin_routes.py:361](../../../app/whatsapp_scheduler/web/admin_routes.py#L361) |
| GET | `/admin/planos` | `admin_plans` | [admin_routes.py:375](../../../app/whatsapp_scheduler/web/admin_routes.py#L375) |
| POST | `/admin/planos/{plan_id}` | `admin_update_plan` | [admin_routes.py:398](../../../app/whatsapp_scheduler/web/admin_routes.py#L398) |
| GET | `/admin/faturamento` | `admin_finance` | [admin_routes.py:464](../../../app/whatsapp_scheduler/web/admin_routes.py#L464) |
| GET | `/admin/agendamentos` | `admin_schedules` | [admin_routes.py:483](../../../app/whatsapp_scheduler/web/admin_routes.py#L483) |
| GET | `/admin/logins` | `admin_logins` | [admin_routes.py:508](../../../app/whatsapp_scheduler/web/admin_routes.py#L508) |
| GET | `/admin/auditoria` | `admin_audit` | [admin_routes.py:525](../../../app/whatsapp_scheduler/web/admin_routes.py#L525) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `NoteView` |  | [crm.py:141](../../../app/whatsapp_scheduler/admin/crm.py#L141) |
| `AdminReauthRequired` | Exception | [security.py:32](../../../app/whatsapp_scheduler/admin/security.py#L32) |
| `DashboardMetrics` |  | [service.py:79](../../../app/whatsapp_scheduler/admin/service.py#L79) |
| `UserRow` |  | [service.py:181](../../../app/whatsapp_scheduler/admin/service.py#L181) |
| `UserFilters` |  | [service.py:203](../../../app/whatsapp_scheduler/admin/service.py#L203) |
| `UserDetail` |  | [service.py:342](../../../app/whatsapp_scheduler/admin/service.py#L342) |
| `DispatchRow` |  | [service.py:448](../../../app/whatsapp_scheduler/admin/service.py#L448) |
| `DispatchFilters` |  | [service.py:465](../../../app/whatsapp_scheduler/admin/service.py#L465) |
| `LoginRow` |  | [service.py:547](../../../app/whatsapp_scheduler/admin/service.py#L547) |
| `LoginFilters` |  | [service.py:556](../../../app/whatsapp_scheduler/admin/service.py#L556) |
| `AuditRow` |  | [service.py:596](../../../app/whatsapp_scheduler/admin/service.py#L596) |
| `AuditFilters` |  | [service.py:608](../../../app/whatsapp_scheduler/admin/service.py#L608) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `is_owner` |  | [access.py:22](../../../app/whatsapp_scheduler/admin/access.py#L22) |  |
| `is_admin` |  | [access.py:26](../../../app/whatsapp_scheduler/admin/access.py#L26) |  |
| `assignable_plans` |  | [access.py:30](../../../app/whatsapp_scheduler/admin/access.py#L30) | Planos que `actor` pode escolher no painel: a conta principal vê todos (inclusive "Administrador" e os ocultos/inativos) |
| `can_manage` |  | [access.py:38](../../../app/whatsapp_scheduler/admin/access.py#L38) | `actor` pode mudar plano/suspender `target`? A conta principal nunca é alvo; outros admins só são alvo da conta principa |
| `set_plan` |  | [access.py:48](../../../app/whatsapp_scheduler/admin/access.py#L48) | Atribui `plan` a `target` (cortesia, nunca receita). Devolve (código do plano anterior, "granted" \| "revoked" \| None par |
| `revoke_admin` |  | [access.py:69](../../../app/whatsapp_scheduler/admin/access.py#L69) | Tira o acesso de admin (volta ao plano padrão). Usado pelo CLI de emergência e ao (re)definir a conta principal. Nunca r |
| `seed_default_tags` |  | [crm.py:40](../../../app/whatsapp_scheduler/admin/crm.py#L40) |  |
| `status_of` |  | [crm.py:48](../../../app/whatsapp_scheduler/admin/crm.py#L48) |  |
| `set_status` |  | [crm.py:53](../../../app/whatsapp_scheduler/admin/crm.py#L53) |  |
| `list_tags` |  | [crm.py:66](../../../app/whatsapp_scheduler/admin/crm.py#L66) |  |
| `user_tags` |  | [crm.py:70](../../../app/whatsapp_scheduler/admin/crm.py#L70) |  |
| `get_or_create_tag` |  | [crm.py:81](../../../app/whatsapp_scheduler/admin/crm.py#L81) |  |
| `add_tag` |  | [crm.py:97](../../../app/whatsapp_scheduler/admin/crm.py#L97) |  |
| `remove_tag` |  | [crm.py:105](../../../app/whatsapp_scheduler/admin/crm.py#L105) |  |
| `delete_tag` |  | [crm.py:115](../../../app/whatsapp_scheduler/admin/crm.py#L115) |  |
| `_clean_note` |  | [crm.py:126](../../../app/whatsapp_scheduler/admin/crm.py#L126) |  |
| `list_notes` |  | [crm.py:150](../../../app/whatsapp_scheduler/admin/crm.py#L150) |  |
| `add_note` |  | [crm.py:167](../../../app/whatsapp_scheduler/admin/crm.py#L167) |  |
| `update_note` |  | [crm.py:176](../../../app/whatsapp_scheduler/admin/crm.py#L176) |  |
| `delete_note` |  | [crm.py:188](../../../app/whatsapp_scheduler/admin/crm.py#L188) |  |
| `AdminReauthRequired.__init__` |  | [security.py:35](../../../app/whatsapp_scheduler/admin/security.py#L35) |  |
| `_next_path` |  | [security.py:39](../../../app/whatsapp_scheduler/admin/security.py#L39) |  |
| `_check` |  | [security.py:43](../../../app/whatsapp_scheduler/admin/security.py#L43) |  |
| `require_admin` |  | [security.py:66](../../../app/whatsapp_scheduler/admin/security.py#L66) |  |
| `csrf_token` |  | [security.py:75](../../../app/whatsapp_scheduler/admin/security.py#L75) |  |
| `verify_csrf` | async | [security.py:80](../../../app/whatsapp_scheduler/admin/security.py#L80) |  |
| `audit` |  | [security.py:90](../../../app/whatsapp_scheduler/admin/security.py#L90) | Registra uma ação administrativa. `detail` deve ser curto e NÃO sensível (nunca texto de nota, CPF, conteúdo...). Faz co |
| `_like` |  | [service.py:62](../../../app/whatsapp_scheduler/admin/service.py#L62) |  |
| `_count` |  | [service.py:67](../../../app/whatsapp_scheduler/admin/service.py#L67) |  |
| `_scalar` |  | [service.py:71](../../../app/whatsapp_scheduler/admin/service.py#L71) |  |
| `dashboard` |  | [service.py:100](../../../app/whatsapp_scheduler/admin/service.py#L100) |  |
| `dashboard.users_where` | aninhada | [service.py:103](../../../app/whatsapp_scheduler/admin/service.py#L103) |  |
| `dashboard.activity_since` | aninhada | [service.py:106](../../../app/whatsapp_scheduler/admin/service.py#L106) |  |
| `dashboard.logins` | aninhada | [service.py:109](../../../app/whatsapp_scheduler/admin/service.py#L109) |  |
| `dashboard.dispatches` | aninhada | [service.py:117](../../../app/whatsapp_scheduler/admin/service.py#L117) |  |
| `active_session_names` |  | [service.py:148](../../../app/whatsapp_scheduler/admin/service.py#L148) | session_name -> user_id das conexões WhatsApp não desconectadas. |
| `live_whatsapp_status` | async | [service.py:158](../../../app/whatsapp_scheduler/admin/service.py#L158) | Quantas conexões estão WORKING agora. Usa só `name` e `status` da lista do WAHA — o campo `me` (número/nome do perfil) é |
| `UserRow.online` |  | [service.py:198](../../../app/whatsapp_scheduler/admin/service.py#L198) |  |
| `UserFilters.as_params` |  | [service.py:216](../../../app/whatsapp_scheduler/admin/service.py#L216) | Parâmetros de URL (com os nomes da query string: `dir`, não `direction`). |
| `_entitled_subquery` |  | [service.py:233](../../../app/whatsapp_scheduler/admin/service.py#L233) |  |
| `list_users` |  | [service.py:245](../../../app/whatsapp_scheduler/admin/service.py#L245) |  |
| `_subscription_dict` |  | [service.py:372](../../../app/whatsapp_scheduler/admin/service.py#L372) |  |
| `user_detail` |  | [service.py:383](../../../app/whatsapp_scheduler/admin/service.py#L383) |  |
| `user_detail.dispatch_count` | aninhada | [service.py:405](../../../app/whatsapp_scheduler/admin/service.py#L405) |  |
| `DispatchFilters.as_params` |  | [service.py:472](../../../app/whatsapp_scheduler/admin/service.py#L472) |  |
| `_parse_day` |  | [service.py:480](../../../app/whatsapp_scheduler/admin/service.py#L480) |  |
| `dispatch_summary` |  | [service.py:487](../../../app/whatsapp_scheduler/admin/service.py#L487) |  |
| `list_dispatches` |  | [service.py:497](../../../app/whatsapp_scheduler/admin/service.py#L497) |  |
| `LoginFilters.as_params` |  | [service.py:562](../../../app/whatsapp_scheduler/admin/service.py#L562) |  |
| `login_events` |  | [service.py:568](../../../app/whatsapp_scheduler/admin/service.py#L568) |  |
| `AuditFilters.as_params` |  | [service.py:613](../../../app/whatsapp_scheduler/admin/service.py#L613) |  |
| `audit_entries` |  | [service.py:619](../../../app/whatsapp_scheduler/admin/service.py#L619) |  |
| `plan_rows` |  | [service.py:655](../../../app/whatsapp_scheduler/admin/service.py#L655) |  |
| `recent_payments` |  | [service.py:671](../../../app/whatsapp_scheduler/admin/service.py#L671) |  |
| `recent_subscriptions` |  | [service.py:687](../../../app/whatsapp_scheduler/admin/service.py#L687) |  |
| `_ctx` |  | [admin_routes.py:38](../../../app/whatsapp_scheduler/web/admin_routes.py#L38) |  |
| `_pages` |  | [admin_routes.py:51](../../../app/whatsapp_scheduler/web/admin_routes.py#L51) |  |
| `_back` |  | [admin_routes.py:55](../../../app/whatsapp_scheduler/web/admin_routes.py#L55) |  |
| `_target_user` |  | [admin_routes.py:61](../../../app/whatsapp_scheduler/web/admin_routes.py#L61) |  |
| `admin_dashboard` | rota, async | [admin_routes.py:72](../../../app/whatsapp_scheduler/web/admin_routes.py#L72) |  |
| `admin_users` | rota | [admin_routes.py:86](../../../app/whatsapp_scheduler/web/admin_routes.py#L86) |  |
| `admin_user_detail` | rota, async | [admin_routes.py:118](../../../app/whatsapp_scheduler/web/admin_routes.py#L118) |  |
| `admin_user_detail._status` | async, aninhada | [admin_routes.py:138](../../../app/whatsapp_scheduler/web/admin_routes.py#L138) |  |
| `admin_set_crm_status` | rota, async | [admin_routes.py:160](../../../app/whatsapp_scheduler/web/admin_routes.py#L160) |  |
| `admin_add_tag` | rota, async | [admin_routes.py:176](../../../app/whatsapp_scheduler/web/admin_routes.py#L176) |  |
| `admin_remove_tag` | rota, async | [admin_routes.py:202](../../../app/whatsapp_scheduler/web/admin_routes.py#L202) |  |
| `admin_add_note` | rota, async | [admin_routes.py:213](../../../app/whatsapp_scheduler/web/admin_routes.py#L213) |  |
| `admin_update_note` | rota, async | [admin_routes.py:230](../../../app/whatsapp_scheduler/web/admin_routes.py#L230) |  |
| `admin_delete_note` | rota, async | [admin_routes.py:247](../../../app/whatsapp_scheduler/web/admin_routes.py#L247) |  |
| `admin_suspend` | rota, async | [admin_routes.py:257](../../../app/whatsapp_scheduler/web/admin_routes.py#L257) |  |
| `admin_reactivate` | rota, async | [admin_routes.py:278](../../../app/whatsapp_scheduler/web/admin_routes.py#L278) |  |
| `admin_change_plan` | rota, async | [admin_routes.py:295](../../../app/whatsapp_scheduler/web/admin_routes.py#L295) |  |
| `admin_crm` | rota | [admin_routes.py:325](../../../app/whatsapp_scheduler/web/admin_routes.py#L325) |  |
| `admin_create_tag` | rota, async | [admin_routes.py:350](../../../app/whatsapp_scheduler/web/admin_routes.py#L350) |  |
| `admin_delete_tag` | rota, async | [admin_routes.py:362](../../../app/whatsapp_scheduler/web/admin_routes.py#L362) |  |
| `admin_plans` | rota | [admin_routes.py:376](../../../app/whatsapp_scheduler/web/admin_routes.py#L376) |  |
| `admin_update_plan` | rota, async | [admin_routes.py:399](../../../app/whatsapp_scheduler/web/admin_routes.py#L399) |  |
| `admin_finance` | rota | [admin_routes.py:465](../../../app/whatsapp_scheduler/web/admin_routes.py#L465) |  |
| `admin_schedules` | rota | [admin_routes.py:484](../../../app/whatsapp_scheduler/web/admin_routes.py#L484) |  |
| `admin_logins` | rota | [admin_routes.py:509](../../../app/whatsapp_scheduler/web/admin_routes.py#L509) |  |
| `admin_audit` | rota | [admin_routes.py:526](../../../app/whatsapp_scheduler/web/admin_routes.py#L526) |  |
| `_qs` |  | [admin_routes.py:544](../../../app/whatsapp_scheduler/web/admin_routes.py#L544) |  |

## Templates desta funcionalidade

Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).

| Template | hx-* | Listeners JS | Handlers inline | Polling |
|---|---|---|---|---|
| [`admin/_base.html`](../../../app/whatsapp_scheduler/web/templates/admin/_base.html) | 0 | 0 | 0 | 0 |
| [`admin/_macros.html`](../../../app/whatsapp_scheduler/web/templates/admin/_macros.html) | 0 | 0 | 0 | 0 |
| [`admin/agendamentos.html`](../../../app/whatsapp_scheduler/web/templates/admin/agendamentos.html) | 0 | 0 | 0 | 0 |
| [`admin/auditoria.html`](../../../app/whatsapp_scheduler/web/templates/admin/auditoria.html) | 0 | 0 | 0 | 0 |
| [`admin/crm.html`](../../../app/whatsapp_scheduler/web/templates/admin/crm.html) | 0 | 0 | 1 | 0 |
| [`admin/dashboard.html`](../../../app/whatsapp_scheduler/web/templates/admin/dashboard.html) | 0 | 0 | 0 | 0 |
| [`admin/faturamento.html`](../../../app/whatsapp_scheduler/web/templates/admin/faturamento.html) | 0 | 0 | 0 | 0 |
| [`admin/logins.html`](../../../app/whatsapp_scheduler/web/templates/admin/logins.html) | 0 | 0 | 0 | 0 |
| [`admin/planos.html`](../../../app/whatsapp_scheduler/web/templates/admin/planos.html) | 0 | 0 | 0 | 0 |
| [`admin/usuario.html`](../../../app/whatsapp_scheduler/web/templates/admin/usuario.html) | 0 | 0 | 2 | 0 |
| [`admin/usuarios.html`](../../../app/whatsapp_scheduler/web/templates/admin/usuarios.html) | 0 | 0 | 0 | 0 |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_admin.py`](../../../app/tests/test_admin.py) — 27 funções: `test_anonymous_is_sent_to_login`, `test_regular_user_gets_404_everywhere_even_forging_role`, `test_admin_role_is_read_from_the_database_every_request`, `test_every_admin_page_renders_for_admin`, `test_old_admin_session_must_log_in_again`, `test_admin_posts_require_csrf_token`, `test_cross_site_post_is_rejected_by_origin_check`, `test_admin_rate_limit`, `test_no_admin_route_exposes_messages_conversations_or_media`, `test_admin_code_never_touches_decryption_of_user_content`, `test_admin_pages_never_show_content_phone_or_full_cpf`, `test_schedule_health_shows_only_metadata`, `test_users_list_search_filter_sort_and_counts`, `test_crm_status_tags_notes_are_audited`, `test_crm_note_refuses_pasted_whatsapp_conversation`, `test_suspend_and_reactivate`, `test_admin_cannot_suspend_self`, `test_manual_plan_change_is_not_revenue`, `test_edit_plan_catalog_is_audited`, `test_logins_page_lists_success_and_failure_without_ip`, `test_dashboard_counts_do_not_need_content`, `test_owner_email_is_reserved_on_public_signup`, `test_setup_owner_resets_password_kills_sessions_and_demotes_other_admins`, `test_only_the_owner_grants_admin_through_the_admin_plan`, `test_granted_admin_cannot_grant_admin_or_touch_other_admins`, `test_owner_plan_cannot_be_changed`, `test_admin_plan_is_internal_and_not_sellable`
