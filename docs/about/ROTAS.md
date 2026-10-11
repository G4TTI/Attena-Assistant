# Rotas HTTP declaradas no código

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`.

Extração estática dos decoradores e prefixos APIRouter. Inclui páginas, parciais HTMX, REST e webhook; exclui rotas automáticas do FastAPI (listadas ao final). Não representa chamadas executadas nem validação funcional.

Gerado por `build_inventory.py`; não edite à mão. O contrato de cada rota está no about.md do domínio.

| Método | Caminho | Handler | Domínio | Fonte |
|---|---|---|---|---|
| GET | `/api/calendar/connections` | `list_connections` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/calendar.py#L18) |
| DELETE | `/api/calendar/connections/{connection_id}` | `disconnect` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/calendar.py#L25) |
| POST | `/api/calendar/connections/{connection_id}/sync` | `sync_now` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/calendar.py#L34) |
| GET | `/api/calendar/connections/{connection_id}/calendars` | `list_calendars` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/calendar.py#L44) |
| POST | `/api/calendar/calendars/{calendar_id}/toggle` | `toggle_calendar` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/calendar.py#L51) |
| GET | `/api/calendar/events` | `list_events` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/calendar.py#L64) |
| POST | `/api/calendar/events/{event_id}/automations` | `create_automation` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/calendar.py#L77) |
| DELETE | `/api/calendar/automations/{automation_id}` | `delete_automation` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/calendar.py#L123) |
| GET | `/api/whatsapp-sessions/{session_id}/chats` | `chats` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/chats.py#L30) |
| GET | `/api/whatsapp-sessions/{session_id}/chats/messages` | `messages` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/chats.py#L47) |
| POST | `/api/whatsapp-sessions/{session_id}/chats/send` | `send` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/chats.py#L70) |
| POST | `/api/schedules` | `create` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/schedules.py#L34) |
| GET | `/api/schedules` | `list_schedules` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/schedules.py#L69) |
| GET | `/api/schedules/{schedule_id}` | `get_schedule` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/schedules.py#L82) |
| DELETE | `/api/schedules/{schedule_id}` | `delete_schedule` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/schedules.py#L90) |
| POST | `/api/schedules/{schedule_id}/run-now` | `trigger_now` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/schedules.py#L99) |
| GET | `/api/whatsapp-sessions` | `list_sessions` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/session.py#L39) |
| POST | `/api/whatsapp-sessions` | `create_session` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/session.py#L49) |
| GET | `/api/whatsapp-sessions/{session_id}` | `session_status` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/session.py#L63) |
| GET | `/api/whatsapp-sessions/{session_id}/qr` | `session_qr` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/session.py#L85) |
| POST | `/api/whatsapp-sessions/{session_id}/start` | `session_start` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/session.py#L100) |
| POST | `/api/whatsapp-sessions/{session_id}/rename` | `rename_session` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/session.py#L117) |
| DELETE | `/api/whatsapp-sessions/{session_id}` | `disconnect_session` | [api](api/about.md) | [código](../../app/whatsapp_scheduler/api/session.py#L130) |
| GET | `/healthz` | `healthz` | [arquitetura](arquitetura/about.md) | [código](../../app/whatsapp_scheduler/main.py#L203) |
| GET | `/admin` | `admin_dashboard` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L71) |
| GET | `/admin/usuarios` | `admin_users` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L85) |
| GET | `/admin/usuarios/{user_id}` | `admin_user_detail` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L117) |
| POST | `/admin/usuarios/{user_id}/crm/status` | `admin_set_crm_status` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L159) |
| POST | `/admin/usuarios/{user_id}/crm/tags` | `admin_add_tag` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L175) |
| POST | `/admin/usuarios/{user_id}/crm/tags/{tag_id}/remover` | `admin_remove_tag` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L201) |
| POST | `/admin/usuarios/{user_id}/crm/notas` | `admin_add_note` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L212) |
| POST | `/admin/usuarios/{user_id}/crm/notas/{note_id}` | `admin_update_note` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L229) |
| POST | `/admin/usuarios/{user_id}/crm/notas/{note_id}/excluir` | `admin_delete_note` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L246) |
| POST | `/admin/usuarios/{user_id}/suspender` | `admin_suspend` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L256) |
| POST | `/admin/usuarios/{user_id}/reativar` | `admin_reactivate` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L277) |
| POST | `/admin/usuarios/{user_id}/plano` | `admin_change_plan` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L294) |
| GET | `/admin/crm` | `admin_crm` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L324) |
| POST | `/admin/crm/tags` | `admin_create_tag` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L349) |
| POST | `/admin/crm/tags/{tag_id}/excluir` | `admin_delete_tag` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L361) |
| GET | `/admin/planos` | `admin_plans` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L375) |
| POST | `/admin/planos/{plan_id}` | `admin_update_plan` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L398) |
| GET | `/admin/faturamento` | `admin_finance` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L464) |
| GET | `/admin/agendamentos` | `admin_schedules` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L483) |
| GET | `/admin/logins` | `admin_logins` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L508) |
| GET | `/admin/auditoria` | `admin_audit` | [administracao](administracao/about.md) | [código](../../app/whatsapp_scheduler/web/admin_routes.py#L525) |
| GET | `/login` | `page_login` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L35) |
| POST | `/login` | `do_login` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L51) |
| POST | `/logout` | `do_logout` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L91) |
| GET | `/cadastro` | `page_cadastro` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L105) |
| POST | `/cadastro` | `do_cadastro` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L112) |
| GET | `/esqueci-senha` | `page_esqueci_senha` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L159) |
| POST | `/esqueci-senha` | `do_esqueci_senha` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L164) |
| GET | `/redefinir-senha/{token}` | `page_redefinir_senha` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L183) |
| POST | `/redefinir-senha/{token}` | `do_redefinir_senha` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L188) |
| GET | `/verificar-email/{token}` | `verificar_email` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L210) |
| POST | `/verificar-email/reenviar` | `reenviar_verificacao` | [autenticacao](autenticacao/about.md) | [código](../../app/whatsapp_scheduler/web/auth_routes.py#L219) |
| GET | `/planos` | `page_planos` | [planos-faturamento](planos-faturamento/about.md) | [código](../../app/whatsapp_scheduler/web/billing_routes.py#L68) |
| GET | `/planos/{code}/upgrade` | `page_upgrade` | [planos-faturamento](planos-faturamento/about.md) | [código](../../app/whatsapp_scheduler/web/billing_routes.py#L95) |
| POST | `/planos/{code}/upgrade` | `do_upgrade` | [planos-faturamento](planos-faturamento/about.md) | [código](../../app/whatsapp_scheduler/web/billing_routes.py#L112) |
| GET | `/planos/{code}/pagamento` | `page_payment` | [planos-faturamento](planos-faturamento/about.md) | [código](../../app/whatsapp_scheduler/web/billing_routes.py#L137) |
| POST | `/planos/solicitacao/cancelar` | `cancel_request` | [planos-faturamento](planos-faturamento/about.md) | [código](../../app/whatsapp_scheduler/web/billing_routes.py#L169) |
| POST | `/planos/faturamento/remover` | `remove_billing` | [planos-faturamento](planos-faturamento/about.md) | [código](../../app/whatsapp_scheduler/web/billing_routes.py#L175) |
| POST | `/billing/webhook/{provider}` | `billing_webhook` | [planos-faturamento](planos-faturamento/about.md) | [código](../../app/whatsapp_scheduler/web/billing_routes.py#L187) |
| GET | `/calendario` | `page_calendario` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L356) |
| GET | `/ui/calendario/grid` | `ui_grid` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L371) |
| GET | `/calendario/dia` | `page_calendario_dia` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L388) |
| GET | `/ui/calendario/dia` | `ui_calendario_dia` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L403) |
| GET | `/ui/calendario/events/new` | `ui_event_new` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L421) |
| GET | `/ui/calendario/events/{event_id}` | `ui_event_detail` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L451) |
| GET | `/ui/calendario/events/{event_id}/edit` | `ui_event_edit` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L467) |
| GET | `/ui/calendario/events/{event_id}/delete-confirm` | `ui_event_delete_confirm` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L503) |
| POST | `/ui/calendario/events` | `ui_event_create` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L529) |
| POST | `/ui/calendario/events/{event_id}` | `ui_event_update` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L568) |
| POST | `/ui/calendario/events/{event_id}/delete` | `ui_event_delete` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L607) |
| GET | `/ui/calendario/contacts` | `ui_calendario_contacts` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L646) |
| GET | `/ui/calendario/events/{event_id}/similar-events` | `ui_calendario_similar_events` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L670) |
| GET | `/ui/calendario/events/{event_id}/automation/new` | `ui_automation_new` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L711) |
| GET | `/ui/calendario/automations/{automation_id}/edit` | `ui_automation_edit` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L727) |
| GET | `/ui/calendario/events/{event_id}/automation-preview` | `ui_automation_preview` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L746) |
| POST | `/ui/calendario/events/{event_id}/automation` | `ui_automation_create` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L796) |
| POST | `/ui/calendario/automations/{automation_id}` | `ui_automation_update` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L878) |
| POST | `/ui/calendario/automations/{automation_id}/remove` | `ui_automation_remove` | [calendario](calendario/about.md) | [código](../../app/whatsapp_scheduler/web/calendar_routes.py#L933) |
| GET | `/` | `page_dashboard` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/dashboard_routes.py#L102) |
| GET | `/ui/dashboard/summary` | `ui_dashboard_summary` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/dashboard_routes.py#L119) |
| POST | `/ui/dashboard/calendar-card/sync` | `ui_dashboard_calendar_sync` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/dashboard_routes.py#L128) |
| GET | `/onboarding` | `page_onboarding` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/onboarding_routes.py#L41) |
| GET | `/ui/onboarding/whatsapp` | `ui_onboarding_whatsapp` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/onboarding_routes.py#L53) |
| POST | `/onboarding/whatsapp/start` | `ui_onboarding_whatsapp_start` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/onboarding_routes.py#L69) |
| POST | `/onboarding/timezone` | `ui_onboarding_timezone` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/onboarding_routes.py#L97) |
| GET | `/onboarding/pular` | `ui_onboarding_skip` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/onboarding_routes.py#L122) |
| POST | `/onboarding/finish` | `ui_onboarding_finish` | [onboarding-dashboard](onboarding-dashboard/about.md) | [código](../../app/whatsapp_scheduler/web/onboarding_routes.py#L132) |
| GET | `/agendamentos` | `page_schedules` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L209) |
| GET | `/conversas` | `page_chats` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L222) |
| GET | `/conversas/{session_id}` | `page_chats_session` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L234) |
| GET | `/ui/sidebar-status` | `ui_sidebar_status` | [interface](interface/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L261) |
| GET | `/ui/schedules` | `ui_schedules` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L280) |
| POST | `/ui/schedules` | `ui_create` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L303) |
| GET | `/ui/schedules/{group_id}` | `ui_schedule_detail` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L383) |
| GET | `/ui/schedules/{group_id}/edit` | `ui_schedule_edit` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L418) |
| POST | `/ui/schedules/{group_id}/edit` | `ui_schedule_update` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L439) |
| POST | `/ui/schedules/{group_id}/cancel` | `ui_cancel` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L476) |
| POST | `/ui/schedules/cancel-selected` | `ui_cancel_selected` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L487) |
| POST | `/ui/schedules/{group_id}/run-now` | `ui_run_now` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L507) |
| POST | `/ui/media` | `ui_media_upload` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L525) |
| GET | `/ui/media/{media_id}` | `ui_media_file` | [agendamentos](agendamentos/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L568) |
| GET | `/ui/chats/{session_id}` | `ui_chats` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L622) |
| GET | `/ui/chats/{session_id}/view` | `ui_chat_view` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L675) |
| GET | `/ui/chats/{session_id}/messages` | `ui_chat_messages` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L687) |
| GET | `/ui/chats/{session_id}/scheduled` | `ui_chat_scheduled` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L716) |
| POST | `/ui/chats/{session_id}/scheduled/{schedule_id}/cancel` | `ui_chat_scheduled_cancel` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L733) |
| GET | `/ui/chats/{session_id}/scheduled/panel` | `ui_chat_scheduled_panel` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L787) |
| GET | `/ui/chats/{session_id}/scheduled/panel/list` | `ui_chat_scheduled_panel_list` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L809) |
| POST | `/ui/chats/{session_id}/scheduled/panel/messages/{schedule_id}/cancel` | `ui_chat_panel_cancel_message` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L829) |
| POST | `/ui/chats/{session_id}/scheduled/panel/cancel-selected` | `ui_chat_panel_cancel_selected` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L852) |
| POST | `/ui/chats/{session_id}/scheduled/panel/groups/{group_id}/cancel` | `ui_chat_panel_cancel_group` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L888) |
| POST | `/ui/chats/{session_id}/send` | `ui_chat_send` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L915) |
| POST | `/ui/chats/{session_id}/schedule` | `ui_chat_schedule` | [whatsapp-conversas](whatsapp-conversas/about.md) | [código](../../app/whatsapp_scheduler/web/routes.py#L938) |
| GET | `/configuracoes` | `page_configuracoes` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L91) |
| GET | `/ui/configuracoes/connections` | `ui_connections` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L109) |
| POST | `/configuracoes/preferencias/timezone` | `ui_set_timezone` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L119) |
| GET | `/ui/configuracoes/relogio` | `ui_clock` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L145) |
| POST | `/configuracoes/google/connect` | `connect_google` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L150) |
| GET | `/calendario/oauth/callback` | `google_oauth_callback` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L164) |
| POST | `/ui/configuracoes/calendars/{calendar_id}/toggle` | `ui_toggle_calendar` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L204) |
| POST | `/ui/configuracoes/connections/{connection_id}/sync` | `ui_sync_now` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L219) |
| POST | `/ui/configuracoes/connections/{connection_id}/disconnect` | `ui_disconnect` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L233) |
| POST | `/configuracoes/conta/perfil` | `ui_update_profile` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L253) |
| POST | `/configuracoes/conta/senha` | `ui_change_password` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L272) |
| POST | `/configuracoes/conta/sair-outros-dispositivos` | `ui_logout_other_sessions` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/settings_routes.py#L297) |
| GET | `/whatsapps` | `page_whatsapps` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/whatsapp_routes.py#L30) |
| GET | `/ui/whatsapps` | `ui_whatsapps` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/whatsapp_routes.py#L38) |
| GET | `/ui/whatsapp-picker-options` | `ui_whatsapp_picker_options` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/whatsapp_routes.py#L53) |
| POST | `/whatsapps` | `ui_whatsapp_create` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/whatsapp_routes.py#L76) |
| POST | `/whatsapps/{session_id}/start` | `ui_whatsapp_start` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/whatsapp_routes.py#L96) |
| POST | `/whatsapps/{session_id}/rename` | `ui_whatsapp_rename` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/whatsapp_routes.py#L118) |
| POST | `/whatsapps/{session_id}/disconnect` | `ui_whatsapp_disconnect` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/whatsapp_routes.py#L130) |
| GET | `/ui/whatsapps/{session_id}/qr` | `ui_whatsapp_qr` | [configuracoes-conexoes](configuracoes-conexoes/about.md) | [código](../../app/whatsapp_scheduler/web/whatsapp_routes.py#L141) |

## Rotas automáticas do FastAPI

Derivadas dos argumentos de `FastAPI(...)`: argumento ausente = padrão do FastAPI. Não verificado em execução; middlewares podem alterar o acesso.

| Argumento | Valor efetivo | Explícito | Fonte |
|---|---|---|---|
| `openapi_url` | `'/openapi.json'` | não (padrão) | [código](../../app/whatsapp_scheduler/main.py#L100) |
| `docs_url` | `'/docs'` | não (padrão) | [código](../../app/whatsapp_scheduler/main.py#L100) |
| `redoc_url` | `'/redoc'` | não (padrão) | [código](../../app/whatsapp_scheduler/main.py#L100) |
| `swagger_ui_oauth2_redirect_url` | `'/docs/oauth2-redirect'` | não (padrão) | [código](../../app/whatsapp_scheduler/main.py#L100) |
