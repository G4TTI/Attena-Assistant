# Autenticação — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/auth.py`](../../../app/whatsapp_scheduler/auth.py) | 224 |
| [`app/whatsapp_scheduler/auth_service.py`](../../../app/whatsapp_scheduler/auth_service.py) | 301 |
| [`app/whatsapp_scheduler/ratelimit.py`](../../../app/whatsapp_scheduler/ratelimit.py) | 57 |
| [`app/whatsapp_scheduler/web/auth_routes.py`](../../../app/whatsapp_scheduler/web/auth_routes.py) | 227 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_multi_tenant_isolation.py`](../../../app/tests/test_multi_tenant_isolation.py), [`app/tests/test_security_hardening.py`](../../../app/tests/test_security_hardening.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/login` | `page_login` | [auth_routes.py:35](../../../app/whatsapp_scheduler/web/auth_routes.py#L35) |
| POST | `/login` | `do_login` | [auth_routes.py:51](../../../app/whatsapp_scheduler/web/auth_routes.py#L51) |
| POST | `/logout` | `do_logout` | [auth_routes.py:91](../../../app/whatsapp_scheduler/web/auth_routes.py#L91) |
| GET | `/cadastro` | `page_cadastro` | [auth_routes.py:105](../../../app/whatsapp_scheduler/web/auth_routes.py#L105) |
| POST | `/cadastro` | `do_cadastro` | [auth_routes.py:112](../../../app/whatsapp_scheduler/web/auth_routes.py#L112) |
| GET | `/esqueci-senha` | `page_esqueci_senha` | [auth_routes.py:159](../../../app/whatsapp_scheduler/web/auth_routes.py#L159) |
| POST | `/esqueci-senha` | `do_esqueci_senha` | [auth_routes.py:164](../../../app/whatsapp_scheduler/web/auth_routes.py#L164) |
| GET | `/redefinir-senha/{token}` | `page_redefinir_senha` | [auth_routes.py:183](../../../app/whatsapp_scheduler/web/auth_routes.py#L183) |
| POST | `/redefinir-senha/{token}` | `do_redefinir_senha` | [auth_routes.py:188](../../../app/whatsapp_scheduler/web/auth_routes.py#L188) |
| GET | `/verificar-email/{token}` | `verificar_email` | [auth_routes.py:210](../../../app/whatsapp_scheduler/web/auth_routes.py#L210) |
| POST | `/verificar-email/reenviar` | `reenviar_verificacao` | [auth_routes.py:219](../../../app/whatsapp_scheduler/web/auth_routes.py#L219) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `NotAuthenticated` | Exception | [auth.py:32](../../../app/whatsapp_scheduler/auth.py#L32) |
| `AuthenticationError` | ValueError | [auth_service.py:35](../../../app/whatsapp_scheduler/auth_service.py#L35) |
| `RateLimitExceeded` | Exception | [ratelimit.py:20](../../../app/whatsapp_scheduler/ratelimit.py#L20) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `NotAuthenticated.__init__` |  | [auth.py:35](../../../app/whatsapp_scheduler/auth.py#L35) |  |
| `normalize_email` |  | [auth.py:39](../../../app/whatsapp_scheduler/auth.py#L39) |  |
| `hash_password` |  | [auth.py:43](../../../app/whatsapp_scheduler/auth.py#L43) |  |
| `verify_password` |  | [auth.py:47](../../../app/whatsapp_scheduler/auth.py#L47) |  |
| `generate_token` |  | [auth.py:54](../../../app/whatsapp_scheduler/auth.py#L54) | Token opaco de alta entropia — usado tanto pro cookie de sessão quanto pelos links de reset/verificação. Nunca persistid |
| `hash_token` |  | [auth.py:61](../../../app/whatsapp_scheduler/auth.py#L61) | SHA-256 é suficiente aqui (não Argon2id): o "segredo" já é um token aleatório de 256 bits, não uma senha de usuário suje |
| `client_ip` |  | [auth.py:69](../../../app/whatsapp_scheduler/auth.py#L69) |  |
| `client_user_agent` |  | [auth.py:79](../../../app/whatsapp_scheduler/auth.py#L79) |  |
| `create_user_session` |  | [auth.py:87](../../../app/whatsapp_scheduler/auth.py#L87) | Abre uma sessão (login ou cadastro) e registra o login no usuário — base de "último login"/"usuários ativos" no admin. |
| `cookie_secure` |  | [auth.py:109](../../../app/whatsapp_scheduler/auth.py#L109) | Secure por padrão em produção; `SESSION_COOKIE_SECURE` força (ex.: teste servido por HTTPS). |
| `set_session_cookie` |  | [auth.py:116](../../../app/whatsapp_scheduler/auth.py#L116) |  |
| `clear_session_cookie` |  | [auth.py:130](../../../app/whatsapp_scheduler/auth.py#L130) |  |
| `_touch_session` |  | [auth.py:134](../../../app/whatsapp_scheduler/auth.py#L134) | Atualiza "visto por último" da sessão e a última atividade do usuário (base de "usuários ativos" no admin) — no máximo 1 |
| `get_current_session` |  | [auth.py:148](../../../app/whatsapp_scheduler/auth.py#L148) |  |
| `revoke_session` |  | [auth.py:158](../../../app/whatsapp_scheduler/auth.py#L158) |  |
| `revoke_other_sessions` |  | [auth.py:164](../../../app/whatsapp_scheduler/auth.py#L164) |  |
| `revoke_all_sessions` |  | [auth.py:179](../../../app/whatsapp_scheduler/auth.py#L179) | Usado após redefinição de senha — nenhuma sessão antiga sobrevive a uma senha comprometida (mesmo que o próprio dono nun |
| `get_current_user_optional` |  | [auth.py:198](../../../app/whatsapp_scheduler/auth.py#L198) |  |
| `require_user_web` |  | [auth.py:209](../../../app/whatsapp_scheduler/auth.py#L209) |  |
| `require_user_api` |  | [auth.py:218](../../../app/whatsapp_scheduler/auth.py#L218) |  |
| `log_event` |  | [auth_service.py:40](../../../app/whatsapp_scheduler/auth_service.py#L40) |  |
| `_validate_password` |  | [auth_service.py:60](../../../app/whatsapp_scheduler/auth_service.py#L60) |  |
| `_find_by_email` |  | [auth_service.py:65](../../../app/whatsapp_scheduler/auth_service.py#L65) |  |
| `register_user` |  | [auth_service.py:69](../../../app/whatsapp_scheduler/auth_service.py#L69) |  |
| `authenticate_user` |  | [auth_service.py:112](../../../app/whatsapp_scheduler/auth_service.py#L112) |  |
| `change_password` |  | [auth_service.py:124](../../../app/whatsapp_scheduler/auth_service.py#L124) |  |
| `create_password_reset_link` |  | [auth_service.py:141](../../../app/whatsapp_scheduler/auth_service.py#L141) | Gera um token de redefinição e devolve o CAMINHO do link. Quem chama decide como entregar — nunca por log (o token dá ac |
| `request_password_reset` |  | [auth_service.py:156](../../../app/whatsapp_scheduler/auth_service.py#L156) | Sempre "silencioso" pro chamador: nunca revela se o e-mail existe. |
| `reset_password` |  | [auth_service.py:175](../../../app/whatsapp_scheduler/auth_service.py#L175) |  |
| `create_email_verification_link` |  | [auth_service.py:208](../../../app/whatsapp_scheduler/auth_service.py#L208) |  |
| `request_email_verification` |  | [auth_service.py:221](../../../app/whatsapp_scheduler/auth_service.py#L221) | Sem provedor de e-mail ainda: nada a enviar (e o link NUNCA vai para o log). O operador gera um com `python -m whatsapp_ |
| `resend_email_verification` |  | [auth_service.py:227](../../../app/whatsapp_scheduler/auth_service.py#L227) |  |
| `verify_email` |  | [auth_service.py:233](../../../app/whatsapp_scheduler/auth_service.py#L233) |  |
| `setup_owner` |  | [auth_service.py:254](../../../app/whatsapp_scheduler/auth_service.py#L254) | Cria ou redefine a CONTA PRINCIPAL. Idempotente e seguro de repetir: |
| `RateLimitExceeded.__init__` |  | [ratelimit.py:21](../../../app/whatsapp_scheduler/ratelimit.py#L21) |  |
| `check_rate_limit` |  | [ratelimit.py:25](../../../app/whatsapp_scheduler/ratelimit.py#L25) | Levanta `RateLimitExceeded` se `key` já bateu o limite na janela atual. Não conta a chamada em si como tentativa — quem  |
| `record_attempt` |  | [ratelimit.py:46](../../../app/whatsapp_scheduler/ratelimit.py#L46) |  |
| `prune` |  | [ratelimit.py:50](../../../app/whatsapp_scheduler/ratelimit.py#L50) | Esquece chaves sem tentativa recente (a chave de login tem IP + e-mail — não fica na memória além da janela). Retorna qu |
| `_safe_next` |  | [auth_routes.py:25](../../../app/whatsapp_scheduler/web/auth_routes.py#L25) | Só aceita caminho relativo interno — nunca um redirect pra fora do app. |
| `page_login` | rota | [auth_routes.py:36](../../../app/whatsapp_scheduler/web/auth_routes.py#L36) |  |
| `do_login` | rota | [auth_routes.py:52](../../../app/whatsapp_scheduler/web/auth_routes.py#L52) |  |
| `do_logout` | rota | [auth_routes.py:92](../../../app/whatsapp_scheduler/web/auth_routes.py#L92) |  |
| `page_cadastro` | rota | [auth_routes.py:106](../../../app/whatsapp_scheduler/web/auth_routes.py#L106) |  |
| `do_cadastro` | rota | [auth_routes.py:113](../../../app/whatsapp_scheduler/web/auth_routes.py#L113) |  |
| `page_esqueci_senha` | rota | [auth_routes.py:160](../../../app/whatsapp_scheduler/web/auth_routes.py#L160) |  |
| `do_esqueci_senha` | rota | [auth_routes.py:165](../../../app/whatsapp_scheduler/web/auth_routes.py#L165) |  |
| `page_redefinir_senha` | rota | [auth_routes.py:184](../../../app/whatsapp_scheduler/web/auth_routes.py#L184) |  |
| `do_redefinir_senha` | rota | [auth_routes.py:189](../../../app/whatsapp_scheduler/web/auth_routes.py#L189) |  |
| `verificar_email` | rota | [auth_routes.py:211](../../../app/whatsapp_scheduler/web/auth_routes.py#L211) |  |
| `reenviar_verificacao` | rota | [auth_routes.py:220](../../../app/whatsapp_scheduler/web/auth_routes.py#L220) |  |

## Templates desta funcionalidade

Mecânica HTMX/JS detalhada no anexo de [Interface](../interface/INVENTARIO.md).

| Template | hx-* | Listeners JS | Handlers inline | Polling |
|---|---|---|---|---|
| [`auth_base.html`](../../../app/whatsapp_scheduler/web/templates/auth_base.html) | 0 | 0 | 0 | 0 |
| [`cadastro.html`](../../../app/whatsapp_scheduler/web/templates/cadastro.html) | 0 | 0 | 0 | 0 |
| [`esqueci_senha.html`](../../../app/whatsapp_scheduler/web/templates/esqueci_senha.html) | 0 | 0 | 0 | 0 |
| [`login.html`](../../../app/whatsapp_scheduler/web/templates/login.html) | 0 | 0 | 0 | 0 |
| [`redefinir_senha.html`](../../../app/whatsapp_scheduler/web/templates/redefinir_senha.html) | 0 | 0 | 0 | 0 |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_multi_tenant_isolation.py`](../../../app/tests/test_multi_tenant_isolation.py) — 3 funções: `test_two_users_never_see_each_others_data`, `test_timezone_preference_never_leaks_between_users`, `test_qr_code_is_only_served_to_the_owner_of_the_whatsapp_session`
- [`app/tests/test_security_hardening.py`](../../../app/tests/test_security_hardening.py) — 8 funções: `test_cross_site_form_post_is_blocked_but_same_origin_passes`, `test_session_cookie_flags`, `test_login_records_activity_and_failed_login_does_not_store_typed_email`, `test_password_change_revokes_other_sessions`, `test_private_pages_are_not_cached`, `test_user_b_cannot_touch_user_a_schedules_or_session_data`, `test_session_status_api_does_not_leak_waha_config`, `test_app_refuses_to_start_without_data_keys`
