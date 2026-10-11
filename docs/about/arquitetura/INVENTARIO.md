# Arquitetura — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/__init__.py`](../../../app/whatsapp_scheduler/__init__.py) | 3 |
| [`app/whatsapp_scheduler/app_settings.py`](../../../app/whatsapp_scheduler/app_settings.py) | 58 |
| [`app/whatsapp_scheduler/clock.py`](../../../app/whatsapp_scheduler/clock.py) | 32 |
| [`app/whatsapp_scheduler/config.py`](../../../app/whatsapp_scheduler/config.py) | 158 |
| [`app/whatsapp_scheduler/errors.py`](../../../app/whatsapp_scheduler/errors.py) | 8 |
| [`app/whatsapp_scheduler/main.py`](../../../app/whatsapp_scheduler/main.py) | 233 |
| [`app/whatsapp_scheduler/time_sync.py`](../../../app/whatsapp_scheduler/time_sync.py) | 98 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_app_settings.py`](../../../app/tests/test_app_settings.py), [`app/tests/test_time_sync.py`](../../../app/tests/test_time_sync.py).

## Rotas

| Método | Caminho | Handler | Fonte |
|---|---|---|---|
| GET | `/healthz` | `healthz` | [main.py:203](../../../app/whatsapp_scheduler/main.py#L203) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `Settings` | BaseSettings | [config.py:10](../../../app/whatsapp_scheduler/config.py#L10) |
| `ValidationError` | ValueError | [errors.py:7](../../../app/whatsapp_scheduler/errors.py#L7) |
| `ClockSyncService` |  | [time_sync.py:65](../../../app/whatsapp_scheduler/time_sync.py#L65) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `user_timezone` |  | [app_settings.py:25](../../../app/whatsapp_scheduler/app_settings.py#L25) | Fuso horário efetivo de UM usuário (v1.3 — Parte 35): `User.timezone` quando o usuário já escolheu o seu (cadastro/onboa |
| `load_from_db` |  | [app_settings.py:36](../../../app/whatsapp_scheduler/app_settings.py#L36) |  |
| `set_timezone` |  | [app_settings.py:42](../../../app/whatsapp_scheduler/app_settings.py#L42) |  |
| `utcnow` |  | [clock.py:20](../../../app/whatsapp_scheduler/clock.py#L20) | Agora, em UTC, sem tzinfo (naive) — já corrigido pelo offset de sincronização com a internet, se houver (ver `time_sync. |
| `set_offset` |  | [clock.py:26](../../../app/whatsapp_scheduler/clock.py#L26) |  |
| `get_offset` |  | [clock.py:31](../../../app/whatsapp_scheduler/clock.py#L31) |  |
| `get_settings` |  | [config.py:154](../../../app/whatsapp_scheduler/config.py#L154) |  |
| `lifespan` | async | [main.py:53](../../../app/whatsapp_scheduler/main.py#L53) |  |
| `_not_authenticated_handler` | async | [main.py:117](../../../app/whatsapp_scheduler/main.py#L117) |  |
| `_admin_reauth_handler` | async | [main.py:124](../../../app/whatsapp_scheduler/main.py#L124) |  |
| `_allowed_hosts` |  | [main.py:161](../../../app/whatsapp_scheduler/main.py#L161) |  |
| `_origin_check` | async | [main.py:171](../../../app/whatsapp_scheduler/main.py#L171) | CSRF (defesa em profundidade, além do cookie SameSite=Lax e do token do /admin): um POST vindo de OUTRO site traz `Origi |
| `_security_headers` | async | [main.py:188](../../../app/whatsapp_scheduler/main.py#L188) |  |
| `healthz` | rota | [main.py:204](../../../app/whatsapp_scheduler/main.py#L204) |  |
| `_needs_onboarding` |  | [main.py:219](../../../app/whatsapp_scheduler/main.py#L219) |  |
| `_onboarding_gate` | async | [main.py:226](../../../app/whatsapp_scheduler/main.py#L226) |  |
| `sync_once` | async | [time_sync.py:31](../../../app/whatsapp_scheduler/time_sync.py#L31) | Consulta o cabeçalho `Date` de um servidor HTTPS confiável, calcula o desvio em relação ao relógio do sistema (descontan |
| `ClockSyncService.__init__` |  | [time_sync.py:68](../../../app/whatsapp_scheduler/time_sync.py#L68) |  |
| `ClockSyncService.start` | async | [time_sync.py:72](../../../app/whatsapp_scheduler/time_sync.py#L72) |  |
| `ClockSyncService.stop` | async | [time_sync.py:82](../../../app/whatsapp_scheduler/time_sync.py#L82) |  |
| `ClockSyncService._run` | async | [time_sync.py:91](../../../app/whatsapp_scheduler/time_sync.py#L91) |  |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_app_settings.py`](../../../app/tests/test_app_settings.py) — 6 funções: `test_user_timezone_uses_users_own_value_when_set`, `test_user_timezone_falls_back_to_global_default_when_unset`, `test_user_timezone_never_leaks_between_users`, `test_client_ip_ignores_forwarded_headers_by_default`, `test_client_ip_uses_configured_proxy_header`, `test_client_ip_takes_first_hop_of_x_forwarded_for`
- [`app/tests/test_time_sync.py`](../../../app/tests/test_time_sync.py) — 6 funções: `test_clock_utcnow_applies_offset`, `test_clock_utcnow_defaults_to_no_offset`, `test_sync_once_computes_and_applies_offset`, `test_sync_once_returns_none_and_keeps_old_offset_on_network_failure`, `test_sync_once_returns_none_when_response_has_no_date_header`, `test_clock_sync_service_syncs_immediately_on_start_and_stops_cleanly`
