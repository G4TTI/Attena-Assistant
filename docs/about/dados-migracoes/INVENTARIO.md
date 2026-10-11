# Dados e Migrações — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/db.py`](../../../app/whatsapp_scheduler/db.py) | 211 |
| [`app/whatsapp_scheduler/migrations.py`](../../../app/whatsapp_scheduler/migrations.py) | 334 |
| [`app/whatsapp_scheduler/models.py`](../../../app/whatsapp_scheduler/models.py) | 818 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_migration_legacy_data.py`](../../../app/tests/test_migration_legacy_data.py), [`app/tests/test_migration_v14.py`](../../../app/tests/test_migration_v14.py).

## Tabelas SQLModel

| Tabela | Modelo | Campos | Fonte |
|---|---|---|---|
| `schedule_groups` | `ScheduleGroup` | 12 | [models.py:51](../../../app/whatsapp_scheduler/models.py#L51) |
| `schedules` | `Schedule` | 19 | [models.py:89](../../../app/whatsapp_scheduler/models.py#L89) |
| `media_attachments` | `MediaAttachment` | 12 | [models.py:140](../../../app/whatsapp_scheduler/models.py#L140) |
| `dispatches` | `Dispatch` | 11 | [models.py:168](../../../app/whatsapp_scheduler/models.py#L168) |
| `calendar_connections` | `CalendarConnection` | 13 | [models.py:248](../../../app/whatsapp_scheduler/models.py#L248) |
| `calendars` | `Calendar` | 10 | [models.py:270](../../../app/whatsapp_scheduler/models.py#L270) |
| `events` | `Event` | 16 | [models.py:290](../../../app/whatsapp_scheduler/models.py#L290) |
| `event_automations` | `EventAutomation` | 8 | [models.py:318](../../../app/whatsapp_scheduler/models.py#L318) |
| `automations` | `Automation` | 10 | [models.py:340](../../../app/whatsapp_scheduler/models.py#L340) |
| `automation_messages` | `AutomationMessage` | 9 | [models.py:370](../../../app/whatsapp_scheduler/models.py#L370) |
| `automation_schedules` | `AutomationSchedule` | 6 | [models.py:389](../../../app/whatsapp_scheduler/models.py#L389) |
| `schedule_dependencies` | `ScheduleDependency` | 3 | [models.py:405](../../../app/whatsapp_scheduler/models.py#L405) |
| `event_sync_status` | `EventSyncStatus` | 4 | [models.py:422](../../../app/whatsapp_scheduler/models.py#L422) |
| `app_settings` | `AppSetting` | 3 | [models.py:437](../../../app/whatsapp_scheduler/models.py#L437) |
| `users` | `User` | 16 | [models.py:474](../../../app/whatsapp_scheduler/models.py#L474) |
| `whatsapp_sessions` | `WhatsAppSession` | 9 | [models.py:511](../../../app/whatsapp_scheduler/models.py#L511) |
| `billing_profiles` | `BillingProfile` | 15 | [models.py:537](../../../app/whatsapp_scheduler/models.py#L537) |
| `user_sessions` | `UserSession` | 9 | [models.py:563](../../../app/whatsapp_scheduler/models.py#L563) |
| `password_reset_tokens` | `PasswordResetToken` | 6 | [models.py:581](../../../app/whatsapp_scheduler/models.py#L581) |
| `email_verification_tokens` | `EmailVerificationToken` | 6 | [models.py:595](../../../app/whatsapp_scheduler/models.py#L595) |
| `login_audit_events` | `LoginAuditEvent` | 7 | [models.py:624](../../../app/whatsapp_scheduler/models.py#L624) |
| `plans` | `Plan` | 16 | [models.py:658](../../../app/whatsapp_scheduler/models.py#L658) |
| `subscriptions` | `Subscription` | 15 | [models.py:701](../../../app/whatsapp_scheduler/models.py#L701) |
| `payments` | `Payment` | 11 | [models.py:733](../../../app/whatsapp_scheduler/models.py#L733) |
| `crm_profiles` | `CrmProfile` | 4 | [models.py:754](../../../app/whatsapp_scheduler/models.py#L754) |
| `crm_tags` | `CrmTag` | 5 | [models.py:763](../../../app/whatsapp_scheduler/models.py#L763) |
| `crm_user_tags` | `CrmUserTag` | 4 | [models.py:774](../../../app/whatsapp_scheduler/models.py#L774) |
| `crm_notes` | `CrmNote` | 7 | [models.py:783](../../../app/whatsapp_scheduler/models.py#L783) |
| `admin_audit_log` | `AdminAuditLog` | 7 | [models.py:797](../../../app/whatsapp_scheduler/models.py#L797) |
| `schema_migrations` | `SchemaMigration` | 2 | [models.py:812](../../../app/whatsapp_scheduler/models.py#L812) |

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `DispatchStatus` | str, enum.Enum | [models.py:19](../../../app/whatsapp_scheduler/models.py#L19) |
| `ScheduleSource` | str, enum.Enum | [models.py:40](../../../app/whatsapp_scheduler/models.py#L40) |
| `ScheduleGroup` | SQLModel | [models.py:51](../../../app/whatsapp_scheduler/models.py#L51) |
| `Schedule` | SQLModel | [models.py:89](../../../app/whatsapp_scheduler/models.py#L89) |
| `MediaKind` | str, enum.Enum | [models.py:128](../../../app/whatsapp_scheduler/models.py#L128) |
| `MediaAttachment` | SQLModel | [models.py:140](../../../app/whatsapp_scheduler/models.py#L140) |
| `Dispatch` | SQLModel | [models.py:168](../../../app/whatsapp_scheduler/models.py#L168) |
| `CalendarConnectionStatus` | str, enum.Enum | [models.py:200](../../../app/whatsapp_scheduler/models.py#L200) |
| `EventSource` | str, enum.Enum | [models.py:209](../../../app/whatsapp_scheduler/models.py#L209) |
| `EventStatus` | str, enum.Enum | [models.py:217](../../../app/whatsapp_scheduler/models.py#L217) |
| `OffsetUnit` | str, enum.Enum | [models.py:225](../../../app/whatsapp_scheduler/models.py#L225) |
| `OffsetDirection` | str, enum.Enum | [models.py:235](../../../app/whatsapp_scheduler/models.py#L235) |
| `CalendarConnection` | SQLModel | [models.py:248](../../../app/whatsapp_scheduler/models.py#L248) |
| `Calendar` | SQLModel | [models.py:270](../../../app/whatsapp_scheduler/models.py#L270) |
| `Event` | SQLModel | [models.py:290](../../../app/whatsapp_scheduler/models.py#L290) |
| `EventAutomation` | SQLModel | [models.py:318](../../../app/whatsapp_scheduler/models.py#L318) |
| `Automation` | SQLModel | [models.py:340](../../../app/whatsapp_scheduler/models.py#L340) |
| `AutomationMessage` | SQLModel | [models.py:370](../../../app/whatsapp_scheduler/models.py#L370) |
| `AutomationSchedule` | SQLModel | [models.py:389](../../../app/whatsapp_scheduler/models.py#L389) |
| `ScheduleDependency` | SQLModel | [models.py:405](../../../app/whatsapp_scheduler/models.py#L405) |
| `EventSyncStatus` | SQLModel | [models.py:422](../../../app/whatsapp_scheduler/models.py#L422) |
| `AppSetting` | SQLModel | [models.py:437](../../../app/whatsapp_scheduler/models.py#L437) |
| `User` | SQLModel | [models.py:474](../../../app/whatsapp_scheduler/models.py#L474) |
| `WhatsAppSession` | SQLModel | [models.py:511](../../../app/whatsapp_scheduler/models.py#L511) |
| `BillingProfile` | SQLModel | [models.py:537](../../../app/whatsapp_scheduler/models.py#L537) |
| `UserSession` | SQLModel | [models.py:563](../../../app/whatsapp_scheduler/models.py#L563) |
| `PasswordResetToken` | SQLModel | [models.py:581](../../../app/whatsapp_scheduler/models.py#L581) |
| `EmailVerificationToken` | SQLModel | [models.py:595](../../../app/whatsapp_scheduler/models.py#L595) |
| `AuditEventType` | str, enum.Enum | [models.py:606](../../../app/whatsapp_scheduler/models.py#L606) |
| `LoginAuditEvent` | SQLModel | [models.py:624](../../../app/whatsapp_scheduler/models.py#L624) |
| `BillingPeriod` | str, enum.Enum | [models.py:650](../../../app/whatsapp_scheduler/models.py#L650) |
| `Plan` | SQLModel | [models.py:658](../../../app/whatsapp_scheduler/models.py#L658) |
| `SubscriptionStatus` | str, enum.Enum | [models.py:685](../../../app/whatsapp_scheduler/models.py#L685) |
| `Subscription` | SQLModel | [models.py:701](../../../app/whatsapp_scheduler/models.py#L701) |
| `PaymentStatus` | str, enum.Enum | [models.py:723](../../../app/whatsapp_scheduler/models.py#L723) |
| `Payment` | SQLModel | [models.py:733](../../../app/whatsapp_scheduler/models.py#L733) |
| `CrmProfile` | SQLModel | [models.py:754](../../../app/whatsapp_scheduler/models.py#L754) |
| `CrmTag` | SQLModel | [models.py:763](../../../app/whatsapp_scheduler/models.py#L763) |
| `CrmUserTag` | SQLModel | [models.py:774](../../../app/whatsapp_scheduler/models.py#L774) |
| `CrmNote` | SQLModel | [models.py:783](../../../app/whatsapp_scheduler/models.py#L783) |
| `AdminAuditLog` | SQLModel | [models.py:797](../../../app/whatsapp_scheduler/models.py#L797) |
| `SchemaMigration` | SQLModel | [models.py:812](../../../app/whatsapp_scheduler/models.py#L812) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `get_engine` |  | [db.py:86](../../../app/whatsapp_scheduler/db.py#L86) |  |
| `get_engine._set_sqlite_pragma` | aninhada | [db.py:98](../../../app/whatsapp_scheduler/db.py#L98) |  |
| `_apply_column_migrations` |  | [db.py:119](../../../app/whatsapp_scheduler/db.py#L119) |  |
| `_apply_index_migrations` |  | [db.py:146](../../../app/whatsapp_scheduler/db.py#L146) |  |
| `init_db` |  | [db.py:152](../../../app/whatsapp_scheduler/db.py#L152) |  |
| `get_session` |  | [db.py:165](../../../app/whatsapp_scheduler/db.py#L165) |  |
| `claim_orphan_data` |  | [db.py:173](../../../app/whatsapp_scheduler/db.py#L173) | Associa ao primeiro usuário cadastrado todo dado criado antes da autenticação existir (`user_id IS NULL`). Não roda no b |
| `_tables` |  | [migrations.py:46](../../../app/whatsapp_scheduler/migrations.py#L46) |  |
| `_columns` |  | [migrations.py:50](../../../app/whatsapp_scheduler/migrations.py#L50) |  |
| `_drop_column` |  | [migrations.py:54](../../../app/whatsapp_scheduler/migrations.py#L54) | DROP COLUMN do SQLite (>= 3.35) recusa coluna indexada: remove antes os índices que a usam. |
| `_failure_code` |  | [migrations.py:68](../../../app/whatsapp_scheduler/migrations.py#L68) | Código + mensagem nova (sem o texto antigo, que podia trazer o corpo da resposta do WAHA). |
| `_ts` |  | [migrations.py:90](../../../app/whatsapp_scheduler/migrations.py#L90) | Mesmo formato que o SQLAlchemy grava num DateTime do SQLite. |
| `_v14_privacy` |  | [migrations.py:95](../../../app/whatsapp_scheduler/migrations.py#L95) |  |
| `_v14_privacy.seal` |  | [migrations.py:247](../../../app/whatsapp_scheduler/migrations.py#L247) |  |
| `_media_messages_capability` |  | [migrations.py:276](../../../app/whatsapp_scheduler/migrations.py#L276) |  |
| `_compact` |  | [migrations.py:309](../../../app/whatsapp_scheduler/migrations.py#L309) | Reescreve o arquivo sem as páginas livres (onde o texto puro antigo ainda estaria). |
| `run_migrations` |  | [migrations.py:317](../../../app/whatsapp_scheduler/migrations.py#L317) | Aplica, em ordem, as migrações ainda não registradas. Retorna as aplicadas. |
| `_uuid` |  | [models.py:15](../../../app/whatsapp_scheduler/models.py#L15) |  |
| `DispatchStatus.__str__` |  | [models.py:27](../../../app/whatsapp_scheduler/models.py#L27) |  |
| `ScheduleSource.__str__` |  | [models.py:47](../../../app/whatsapp_scheduler/models.py#L47) |  |
| `MediaKind.__str__` |  | [models.py:136](../../../app/whatsapp_scheduler/models.py#L136) |  |
| `CalendarConnectionStatus.__str__` |  | [models.py:205](../../../app/whatsapp_scheduler/models.py#L205) |  |
| `EventSource.__str__` |  | [models.py:213](../../../app/whatsapp_scheduler/models.py#L213) |  |
| `EventStatus.__str__` |  | [models.py:221](../../../app/whatsapp_scheduler/models.py#L221) |  |
| `OffsetUnit.__str__` |  | [models.py:231](../../../app/whatsapp_scheduler/models.py#L231) |  |
| `OffsetDirection.__str__` |  | [models.py:244](../../../app/whatsapp_scheduler/models.py#L244) |  |
| `_waha_session_default` |  | [models.py:460](../../../app/whatsapp_scheduler/models.py#L460) |  |
| `AuditEventType.__str__` |  | [models.py:620](../../../app/whatsapp_scheduler/models.py#L620) |  |
| `BillingPeriod.__str__` |  | [models.py:654](../../../app/whatsapp_scheduler/models.py#L654) |  |
| `SubscriptionStatus.__str__` |  | [models.py:693](../../../app/whatsapp_scheduler/models.py#L693) |  |
| `PaymentStatus.__str__` |  | [models.py:729](../../../app/whatsapp_scheduler/models.py#L729) |  |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_migration_legacy_data.py`](../../../app/tests/test_migration_legacy_data.py) — 3 funções: `test_first_user_to_register_inherits_all_orphan_data_and_the_paired_session`, `test_second_user_does_not_steal_the_first_users_orphan_data`, `test_migrate_legacy_sessions_is_idempotent_and_never_duplicates`
- [`app/tests/test_migration_v14.py`](../../../app/tests/test_migration_v14.py) — 7 funções: `test_plaintext_columns_and_conversation_cache_are_gone`, `test_no_plaintext_left_anywhere`, `test_active_data_is_encrypted_and_still_usable`, `test_finished_data_is_purged_but_metrics_survive`, `test_billing_profiles_empty_removed_filled_encrypted`, `test_migration_is_recorded_and_idempotent`, `test_migration_is_atomic_on_failure`
