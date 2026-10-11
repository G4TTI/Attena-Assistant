# Privacidade — inventário (anexo gerado)

Base: `9ea5dceb89d019755becd82c411013f9636bceb8`. Gerado por [`build_inventory.py`](../build_inventory.py); não edite à mão. Lista estática do que o inventário associa a este domínio; a descrição e a evidência ficam no [about.md](about.md).

## Arquivos

| Arquivo | Linhas |
|---|---|
| [`app/whatsapp_scheduler/crypto.py`](../../../app/whatsapp_scheduler/crypto.py) | 52 |
| [`app/whatsapp_scheduler/log_sanitizer.py`](../../../app/whatsapp_scheduler/log_sanitizer.py) | 126 |
| [`app/whatsapp_scheduler/privacy.py`](../../../app/whatsapp_scheduler/privacy.py) | 416 |
| [`app/whatsapp_scheduler/retention.py`](../../../app/whatsapp_scheduler/retention.py) | 531 |
| [`docs/SECURITY_AND_PRIVACY.md`](../../../docs/SECURITY_AND_PRIVACY.md) | 335 |

Símbolos deste domínio em arquivos de outro domínio: [`app/tests/test_logs_privacy.py`](../../../app/tests/test_logs_privacy.py), [`app/tests/test_privacy_crypto.py`](../../../app/tests/test_privacy_crypto.py), [`app/tests/test_privacy_lifecycle.py`](../../../app/tests/test_privacy_lifecycle.py).

## Classes

| Classe | Bases | Fonte |
|---|---|---|
| `CryptoNotConfigured` | RuntimeError | [crypto.py:18](../../../app/whatsapp_scheduler/crypto.py#L18) |
| `DecryptionFailed` | RuntimeError | [crypto.py:22](../../../app/whatsapp_scheduler/crypto.py#L22) |
| `SanitizingFilter` | logging.Filter | [log_sanitizer.py:83](../../../app/whatsapp_scheduler/log_sanitizer.py#L83) |
| `KeyConfigurationError` | RuntimeError | [privacy.py:60](../../../app/whatsapp_scheduler/privacy.py#L60) |
| `DecryptionError` | RuntimeError | [privacy.py:64](../../../app/whatsapp_scheduler/privacy.py#L64) |
| `_Keyring` |  | [privacy.py:101](../../../app/whatsapp_scheduler/privacy.py#L101) |
| `Sealed` |  | [privacy.py:162](../../../app/whatsapp_scheduler/privacy.py#L162) |
| `Recipient` |  | [privacy.py:306](../../../app/whatsapp_scheduler/privacy.py#L306) |
| `PrivacyCleanupService` |  | [retention.py:494](../../../app/whatsapp_scheduler/retention.py#L494) |

## Funções e métodos

Docstring = primeira frase do código (não verificada).

| Símbolo | Tipo | Fonte | Docstring |
|---|---|---|---|
| `is_configured` |  | [crypto.py:26](../../../app/whatsapp_scheduler/crypto.py#L26) |  |
| `_fernet` |  | [crypto.py:31](../../../app/whatsapp_scheduler/crypto.py#L31) |  |
| `encrypt` |  | [crypto.py:44](../../../app/whatsapp_scheduler/crypto.py#L44) |  |
| `decrypt` |  | [crypto.py:48](../../../app/whatsapp_scheduler/crypto.py#L48) |  |
| `_phone` |  | [log_sanitizer.py:49](../../../app/whatsapp_scheduler/log_sanitizer.py#L49) |  |
| `redact` |  | [log_sanitizer.py:57](../../../app/whatsapp_scheduler/log_sanitizer.py#L57) | Versão de `text` segura para log. |
| `redact_path` |  | [log_sanitizer.py:75](../../../app/whatsapp_scheduler/log_sanitizer.py#L75) | Caminho de uma requisição para o access log: sem query string e sem tokens no path. |
| `SanitizingFilter.filter` |  | [log_sanitizer.py:84](../../../app/whatsapp_scheduler/log_sanitizer.py#L84) |  |
| `_attach` |  | [log_sanitizer.py:112](../../../app/whatsapp_scheduler/log_sanitizer.py#L112) |  |
| `install` |  | [log_sanitizer.py:117](../../../app/whatsapp_scheduler/log_sanitizer.py#L117) | Idempotente: coloca o filtro em todo handler existente (raiz, uvicorn…). |
| `generate_key` |  | [privacy.py:68](../../../app/whatsapp_scheduler/privacy.py#L68) | Uma chave nova de 256 bits em base64 (serve para cifra e para HMAC). |
| `_b64` |  | [privacy.py:73](../../../app/whatsapp_scheduler/privacy.py#L73) |  |
| `_unb64` |  | [privacy.py:77](../../../app/whatsapp_scheduler/privacy.py#L77) |  |
| `_read_secret` |  | [privacy.py:81](../../../app/whatsapp_scheduler/privacy.py#L81) |  |
| `_decode_key` |  | [privacy.py:90](../../../app/whatsapp_scheduler/privacy.py#L90) |  |
| `_keyring` |  | [privacy.py:107](../../../app/whatsapp_scheduler/privacy.py#L107) |  |
| `_hash_key` |  | [privacy.py:135](../../../app/whatsapp_scheduler/privacy.py#L135) |  |
| `check_configuration` |  | [privacy.py:142](../../../app/whatsapp_scheduler/privacy.py#L142) | Valida as duas chaves (levanta `KeyConfigurationError`). Chamada no boot. |
| `reset_key_cache` |  | [privacy.py:148](../../../app/whatsapp_scheduler/privacy.py#L148) | Relê as chaves na próxima operação (testes e rotação). |
| `active_key_version` |  | [privacy.py:154](../../../app/whatsapp_scheduler/privacy.py#L154) |  |
| `seal` |  | [privacy.py:168](../../../app/whatsapp_scheduler/privacy.py#L168) |  |
| `unseal` |  | [privacy.py:175](../../../app/whatsapp_scheduler/privacy.py#L175) |  |
| `seal_bytes` |  | [privacy.py:185](../../../app/whatsapp_scheduler/privacy.py#L185) | Como `seal`, para conteúdo binário (arquivos). Devolve o ciphertext cru (que vai para o disco) e o nonce/versão (que vão |
| `unseal_bytes` |  | [privacy.py:194](../../../app/whatsapp_scheduler/privacy.py#L194) |  |
| `encrypt_field` |  | [privacy.py:204](../../../app/whatsapp_scheduler/privacy.py#L204) | Envelope de uma coluna só: "v<versão>:<nonce b64>:<ciphertext b64>". |
| `_parse_envelope` |  | [privacy.py:212](../../../app/whatsapp_scheduler/privacy.py#L212) |  |
| `decrypt_field` |  | [privacy.py:222](../../../app/whatsapp_scheduler/privacy.py#L222) |  |
| `envelope_version` |  | [privacy.py:229](../../../app/whatsapp_scheduler/privacy.py#L229) |  |
| `blind_index` |  | [privacy.py:238](../../../app/whatsapp_scheduler/privacy.py#L238) |  |
| `recipient_hash` |  | [privacy.py:243](../../../app/whatsapp_scheduler/privacy.py#L243) | Hash do destinatário no escopo de UM usuário (nunca o número em si). |
| `waha_message_hash` |  | [privacy.py:248](../../../app/whatsapp_scheduler/privacy.py#L248) | O id de mensagem do WAHA embute o telefone ("true_5511...@c.us_ABC") — guardamos só o hash. |
| `_aad` |  | [privacy.py:257](../../../app/whatsapp_scheduler/privacy.py#L257) |  |
| `_safe` |  | [privacy.py:261](../../../app/whatsapp_scheduler/privacy.py#L261) |  |
| `seal_schedule_message` |  | [privacy.py:272](../../../app/whatsapp_scheduler/privacy.py#L272) |  |
| `schedule_message` |  | [privacy.py:280](../../../app/whatsapp_scheduler/privacy.py#L280) |  |
| `seal_schedule_recipient` |  | [privacy.py:292](../../../app/whatsapp_scheduler/privacy.py#L292) |  |
| `schedule_recipient` |  | [privacy.py:297](../../../app/whatsapp_scheduler/privacy.py#L297) |  |
| `Recipient.is_group` |  | [privacy.py:312](../../../app/whatsapp_scheduler/privacy.py#L312) |  |
| `Recipient.phone` |  | [privacy.py:316](../../../app/whatsapp_scheduler/privacy.py#L316) | "+5511999998888" para contato individual; None para grupo/outros ids. |
| `Recipient.display` |  | [privacy.py:322](../../../app/whatsapp_scheduler/privacy.py#L322) |  |
| `seal_group_recipient` |  | [privacy.py:326](../../../app/whatsapp_scheduler/privacy.py#L326) |  |
| `group_recipient` |  | [privacy.py:333](../../../app/whatsapp_scheduler/privacy.py#L333) |  |
| `seal_automation_message` |  | [privacy.py:345](../../../app/whatsapp_scheduler/privacy.py#L345) |  |
| `automation_message` |  | [privacy.py:353](../../../app/whatsapp_scheduler/privacy.py#L353) |  |
| `seal_media_file` |  | [privacy.py:368](../../../app/whatsapp_scheduler/privacy.py#L368) | Cifra o arquivo e grava nonce/versão na linha. Devolve o que vai pro disco. |
| `open_media_file` |  | [privacy.py:377](../../../app/whatsapp_scheduler/privacy.py#L377) |  |
| `seal_media_filename` |  | [privacy.py:386](../../../app/whatsapp_scheduler/privacy.py#L386) |  |
| `media_filename` |  | [privacy.py:390](../../../app/whatsapp_scheduler/privacy.py#L390) |  |
| `seal_field` |  | [privacy.py:398](../../../app/whatsapp_scheduler/privacy.py#L398) |  |
| `open_field` |  | [privacy.py:402](../../../app/whatsapp_scheduler/privacy.py#L402) |  |
| `seal_crm_note` |  | [privacy.py:409](../../../app/whatsapp_scheduler/privacy.py#L409) |  |
| `crm_note_body` |  | [privacy.py:413](../../../app/whatsapp_scheduler/privacy.py#L413) |  |
| `purge_schedule` |  | [retention.py:74](../../../app/whatsapp_scheduler/retention.py#L74) |  |
| `purge_group` |  | [retention.py:85](../../../app/whatsapp_scheduler/retention.py#L85) |  |
| `purge_automation_message` |  | [retention.py:93](../../../app/whatsapp_scheduler/retention.py#L93) |  |
| `purge_media` |  | [retention.py:103](../../../app/whatsapp_scheduler/retention.py#L103) | Apaga o arquivo do disco e o que dá pra ler dele no banco (nome, nonce). O arquivo some ANTES do commit de quem chamou:  |
| `_has_open_dispatch` |  | [retention.py:124](../../../app/whatsapp_scheduler/retention.py#L124) |  |
| `schedule_active_clause` |  | [retention.py:128](../../../app/whatsapp_scheduler/retention.py#L128) | A mensagem ainda pode sair: regra ativa ou alguma dispatch aberta. |
| `is_finished` |  | [retention.py:133](../../../app/whatsapp_scheduler/retention.py#L133) |  |
| `_group_finished` |  | [retention.py:144](../../../app/whatsapp_scheduler/retention.py#L144) |  |
| `_automation_message_finished` |  | [retention.py:151](../../../app/whatsapp_scheduler/retention.py#L151) |  |
| `media_in_use` |  | [retention.py:162](../../../app/whatsapp_scheduler/retention.py#L162) |  |
| `finalize_schedules` |  | [retention.py:170](../../../app/whatsapp_scheduler/retention.py#L170) | Chamada no MESMO ponto (e antes do mesmo commit) em que mensagens chegam a um estado final: expurga o conteúdo das que t |
| `_count` |  | [retention.py:214](../../../app/whatsapp_scheduler/retention.py#L214) |  |
| `run_cleanup` |  | [retention.py:218](../../../app/whatsapp_scheduler/retention.py#L218) | Uma passada completa (síncrona). Devolve contagens por categoria. |
| `_sweep_orphan_media_files` |  | [retention.py:416](../../../app/whatsapp_scheduler/retention.py#L416) | Arquivos na pasta de anexos que nenhuma linha viva aponta (ex.: o processo caiu entre gravar o arquivo e commitar, ou o  |
| `pending_waha_purges` |  | [retention.py:439](../../../app/whatsapp_scheduler/retention.py#L439) |  |
| `purge_waha_session` | async | [retention.py:449](../../../app/whatsapp_scheduler/retention.py#L449) | Desloga e apaga a sessão no WAHA (credenciais + dados locais do WhatsApp Web). Idempotente: sessão já inexistente (404)  |
| `run_cleanup_async` | async | [retention.py:467](../../../app/whatsapp_scheduler/retention.py#L467) |  |
| `run_cleanup_async._sync` | aninhada | [retention.py:468](../../../app/whatsapp_scheduler/retention.py#L468) |  |
| `PrivacyCleanupService.__init__` |  | [retention.py:497](../../../app/whatsapp_scheduler/retention.py#L497) |  |
| `PrivacyCleanupService.start` | async | [retention.py:502](../../../app/whatsapp_scheduler/retention.py#L502) |  |
| `PrivacyCleanupService.stop` | async | [retention.py:508](../../../app/whatsapp_scheduler/retention.py#L508) |  |
| `PrivacyCleanupService.run_once` | async | [retention.py:517](../../../app/whatsapp_scheduler/retention.py#L517) |  |
| `PrivacyCleanupService._run` | async | [retention.py:520](../../../app/whatsapp_scheduler/retention.py#L520) |  |

## Testes (definições, não execuções)

Uma definição parametrizada gera vários casos na execução; a contagem abaixo é de funções.

- [`app/tests/test_logs_privacy.py`](../../../app/tests/test_logs_privacy.py) — 8 funções (1 parametrizadas): `test_redact_removes_sensitive_data`, `test_redact_keeps_operational_metadata`, `test_access_log_path_loses_query_and_tokens`, `test_filter_sanitizes_messages_args_and_tracebacks`, `test_uvicorn_access_record_keeps_format_but_redacts_path`, `test_handlers_have_the_filter_and_httpx_is_quiet`, `test_sending_a_scheduled_message_logs_no_content_or_phone`, `test_password_reset_and_login_never_log_tokens_or_passwords`
- [`app/tests/test_privacy_crypto.py`](../../../app/tests/test_privacy_crypto.py) — 11 funções (1 parametrizadas): `test_seal_roundtrip_and_ciphertext_is_not_plaintext`, `test_every_seal_uses_a_fresh_nonce`, `test_ciphertext_copied_to_another_row_does_not_decrypt`, `test_tampered_ciphertext_is_rejected`, `test_key_rotation_old_versions_still_decrypt`, `test_wrong_key_cannot_decrypt`, `test_invalid_or_missing_keys_refuse_to_start`, `test_missing_hash_key_refuses_to_start`, `test_keys_can_come_from_a_secret_file`, `test_recipient_hash_is_hmac_scoped_per_user_and_never_the_number`, `test_group_recipient_roundtrip`
- [`app/tests/test_privacy_lifecycle.py`](../../../app/tests/test_privacy_lifecycle.py) — 16 funções: `test_scheduled_message_is_encrypted_in_the_database`, `test_other_user_cannot_see_the_message`, `test_content_and_recipient_are_removed_after_sending`, `test_content_is_removed_after_cancel`, `test_single_message_cancel_from_the_chat_purges_only_that_message`, `test_failed_final_removes_content_but_retry_keeps_it`, `test_recurring_message_keeps_content_until_the_recurrence_ends`, `test_removing_an_automation_purges_its_messages`, `test_api_never_returns_purged_or_foreign_content`, `test_suspended_account_messages_are_not_sent`, `test_received_messages_history_and_contacts_are_never_persisted`, `test_sending_now_from_a_conversation_is_not_stored`, `test_privacy_cleanup_finds_leftovers_and_applies_retention`, `test_privacy_cleanup_log_contains_only_counts`, `test_disconnecting_a_whatsapp_logs_out_and_deletes_the_waha_session`, `test_disconnecting_google_wipes_the_tokens`
