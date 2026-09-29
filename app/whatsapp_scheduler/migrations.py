"""Migrações de DADOS versionadas (tabela `schema_migrations`).

`db.init_db()` continua cuidando do que é aditivo (tabelas e colunas novas);
aqui ficam as conversões que mexem em dado existente e por isso precisam rodar
UMA vez, numa transação só (SQLite tem DDL transacional: se qualquer passo
falhar, nada é aplicado e o próximo boot tenta de novo do zero).

v1.4 — privacidade (`2026.09.29-v1.4-privacy`):
  1. conteúdo de mensagens programadas/automações ainda ATIVAS -> AES-256-GCM;
     o das já encerradas é expurgado (não há por que cifrar o que não vai
     mais ser enviado);
  2. destinatários -> cifrados (ativos) + HMAC; ids de mensagem do WAHA -> HMAC;
  3. `last_error` reescrito sem corpo de resposta/telefone + `failure_code`;
  4. colunas em texto puro removidas (`ALTER TABLE ... DROP COLUMN`);
  5. tabela `cached_messages` (cópia local do histórico de conversas do
     WhatsApp — mensagens recebidas e enviadas) removida;
  6. `billing_profiles`: dados em texto puro -> cifrados; perfis vazios
     (criados automaticamente no cadastro) apagados;
  7. e-mail digitado em logins que falharam apagado da trilha de auditoria;
  8. fora da transação: VACUUM + checkpoint do WAL, pra o texto puro antigo não
     sobrar nas páginas livres do arquivo.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from . import failures, privacy
from .clock import utcnow

logger = logging.getLogger("whatsapp_scheduler.migrations")


def _tables(conn: Connection) -> set[str]:
    return {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}


def _columns(conn: Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}


def _drop_column(conn: Connection, table: str, column: str) -> None:
    """DROP COLUMN do SQLite (>= 3.35) recusa coluna indexada: remove antes os índices que a usam."""
    if column not in _columns(conn, table):
        return
    for index in conn.execute(text(f"PRAGMA index_list({table})")).mappings().all():
        name = index["name"]
        if name.startswith("sqlite_autoindex"):
            continue
        used = {row[2] for row in conn.execute(text(f"PRAGMA index_info('{name}')"))}
        if column in used:
            conn.execute(text(f'DROP INDEX IF EXISTS "{name}"'))
    conn.execute(text(f'ALTER TABLE {table} DROP COLUMN "{column}"'))


def _failure_code(status: str, error: str | None) -> tuple[str | None, str | None]:
    """Código + mensagem nova (sem o texto antigo, que podia trazer o corpo da resposta do WAHA)."""
    if status == "canceled":
        return failures.CANCELED, "Agendamento cancelado."
    if status == "skipped":
        return failures.OVERDUE, failures.sanitize(error) or "Atrasada além do limite."
    if not error:
        return None, None
    lowered = error.lower()
    if "não está pronta" in lowered or "nao esta pronta" in lowered:
        return failures.SESSION_NOT_READY, "O WhatsApp desta mensagem não estava conectado."
    if "falha de conexão" in lowered:
        return failures.WAHA_UNREACHABLE, "Não foi possível falar com o WAHA (conexão ou tempo esgotado)."
    if "respondeu 5" in lowered:
        return failures.WAHA_SERVER_ERROR, "O WAHA respondeu com erro interno."
    if "respondeu" in lowered:
        return failures.WAHA_REJECTED, "O WAHA recusou o envio."
    if "recuperada" in lowered:
        return failures.STUCK_RECOVERED, "Recuperada depois de um reinício."
    return failures.UNKNOWN, "Erro ao enviar."


def _ts(value) -> str:
    """Mesmo formato que o SQLAlchemy grava num DateTime do SQLite."""
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")


def _v14_privacy(conn: Connection) -> None:
    now = _ts(utcnow())
    tables = _tables(conn)
    counts: dict[str, int] = {}

    open_ids = {
        row[0]
        for row in conn.execute(text("SELECT DISTINCT schedule_id FROM dispatches WHERE status IN ('pending','processing')"))
    }
    schedule_owner: dict[str, str | None] = {}
    active_schedules: set[str] = set()
    for row in conn.execute(text("SELECT id, user_id, enabled FROM schedules")).mappings().all():
        schedule_owner[row["id"]] = row["user_id"]
        if row["enabled"] or row["id"] in open_ids:
            active_schedules.add(row["id"])

    # 1+2. Mensagens programadas -------------------------------------------- #
    if "text" in _columns(conn, "schedules"):
        rows = conn.execute(text("SELECT id, user_id, text, chat_id FROM schedules")).mappings().all()
        for row in rows:
            ns = SimpleNamespace(id=row["id"], user_id=row["user_id"])
            values = {"id": row["id"], "hash": privacy.recipient_hash(row["user_id"], row["chat_id"])}
            if row["id"] in active_schedules:
                privacy.seal_schedule_message(ns, row["text"] or "")
                privacy.seal_schedule_recipient(ns, row["chat_id"])
                values.update(
                    ct=ns.message_ciphertext, nonce=ns.encryption_nonce, ver=ns.encryption_key_version,
                    rcpt=ns.recipient_phone_encrypted, purged=None,
                )
                counts["schedules_encrypted"] = counts.get("schedules_encrypted", 0) + 1
            else:
                values.update(ct=None, nonce=None, ver=None, rcpt=None, purged=now)
                counts["schedules_purged"] = counts.get("schedules_purged", 0) + 1
            conn.execute(
                text(
                    "UPDATE schedules SET message_ciphertext=:ct, encryption_nonce=:nonce, encryption_key_version=:ver, "
                    "recipient_phone_encrypted=:rcpt, recipient_phone_hash=:hash, content_purged_at=:purged WHERE id=:id"
                ),
                values,
            )

    # Destinatário de cada agendamento (grupo) ------------------------------ #
    if "chat_id" in _columns(conn, "schedule_groups"):
        group_of = {row[0]: row[1] for row in conn.execute(text("SELECT id, group_id FROM schedules")).all()}
        active_groups = {group_of[sid] for sid in active_schedules if group_of.get(sid)}
        rows = conn.execute(
            text("SELECT id, user_id, recipient_input, recipient_name, chat_id FROM schedule_groups")
        ).mappings().all()
        for row in rows:
            ns = SimpleNamespace(id=row["id"], user_id=row["user_id"])
            values = {"id": row["id"], "hash": privacy.recipient_hash(row["user_id"], row["chat_id"])}
            if row["id"] in active_groups:
                privacy.seal_group_recipient(
                    ns, chat_id=row["chat_id"], recipient_input=row["recipient_input"] or row["chat_id"],
                    recipient_name=row["recipient_name"],
                )
                values.update(enc=ns.recipient_encrypted, purged=None)
            else:
                values.update(enc=None, purged=now)
            conn.execute(
                text(
                    "UPDATE schedule_groups SET recipient_encrypted=:enc, recipient_phone_hash=:hash, "
                    "content_purged_at=:purged WHERE id=:id"
                ),
                values,
            )
        counts["groups"] = len(rows)

    # Mensagens de automações ------------------------------------------------ #
    if "text" in _columns(conn, "automation_messages"):
        active_messages = {
            row[0]
            for row in conn.execute(text("SELECT message_id, schedule_id FROM automation_schedules")).all()
            if row[1] in active_schedules
        }
        rows = conn.execute(text("SELECT id, text FROM automation_messages")).mappings().all()
        for row in rows:
            ns = SimpleNamespace(id=row["id"])
            if row["id"] in active_messages:
                privacy.seal_automation_message(ns, row["text"] or "")
                values = dict(ct=ns.message_ciphertext, nonce=ns.encryption_nonce, ver=ns.encryption_key_version, purged=None)
            else:
                values = dict(ct=None, nonce=None, ver=None, purged=now)
            conn.execute(
                text(
                    "UPDATE automation_messages SET message_ciphertext=:ct, encryption_nonce=:nonce, "
                    "encryption_key_version=:ver, content_purged_at=:purged WHERE id=:id"
                ),
                {"id": row["id"], **values},
            )
        counts["automation_messages"] = len(rows)

    if "recipient_chat_id" in _columns(conn, "automation_schedules"):
        rows = conn.execute(text("SELECT id, schedule_id, recipient_chat_id FROM automation_schedules")).mappings().all()
        for row in rows:
            conn.execute(
                text("UPDATE automation_schedules SET recipient_phone_hash=:hash WHERE id=:id"),
                {"id": row["id"], "hash": privacy.recipient_hash(schedule_owner.get(row["schedule_id"]), row["recipient_chat_id"])},
            )

    # 3. Dispatches: id do WAHA -> HMAC; erro sanitizado --------------------- #
    dispatch_columns = _columns(conn, "dispatches")
    select_waha = ", waha_message_id" if "waha_message_id" in dispatch_columns else ""
    rows = conn.execute(text(f"SELECT id, schedule_id, status, last_error{select_waha} FROM dispatches")).mappings().all()
    for row in rows:
        code, message = _failure_code(row["status"], row["last_error"])
        waha_id = row.get("waha_message_id") if select_waha else None
        conn.execute(
            text(
                "UPDATE dispatches SET failure_code=:code, last_error=:msg, "
                "waha_message_hash=COALESCE(:hash, waha_message_hash) WHERE id=:id"
            ),
            {
                "id": row["id"], "code": code, "msg": message,
                "hash": privacy.waha_message_hash(schedule_owner.get(row["schedule_id"]), waha_id) if waha_id else None,
            },
        )

    # 4. Colunas em texto puro ----------------------------------------------- #
    for table, column in (
        ("schedules", "text"), ("schedules", "recipient_input"), ("schedules", "chat_id"),
        ("schedule_groups", "recipient_input"), ("schedule_groups", "recipient_name"), ("schedule_groups", "chat_id"),
        ("automation_messages", "text"), ("automation_schedules", "recipient_chat_id"),
        ("dispatches", "waha_message_id"),
    ):
        _drop_column(conn, table, column)

    # 5. Cópia local do histórico de conversas ------------------------------- #
    if "cached_messages" in tables:
        counts["cached_messages_removed"] = conn.execute(text("SELECT COUNT(*) FROM cached_messages")).scalar() or 0
        conn.execute(text("DROP TABLE cached_messages"))

    # 6. Dados de faturamento ------------------------------------------------ #
    billing_columns = _columns(conn, "billing_profiles")
    if "legal_name" in billing_columns:
        rows = conn.execute(
            text(
                "SELECT id, legal_name, postal_code, address, number, complement, neighborhood, city, state "
                "FROM billing_profiles"
            )
        ).mappings().all()
        for row in rows:
            fields = {k: (row[k] or "").strip() for k in ("legal_name", "postal_code", "address", "number", "complement", "neighborhood", "city")}
            if not any(fields.values()) and not (row["state"] or "").strip():
                conn.execute(text("DELETE FROM billing_profiles WHERE id=:id"), {"id": row["id"]})
                continue
            address = fields["address"] + (f" — {fields['neighborhood']}" if fields["neighborhood"] else "")

            def seal(column: str, value: str) -> str | None:
                return privacy.seal_field("billing_profiles", column, row["id"], value or None)

            conn.execute(
                text(
                    "UPDATE billing_profiles SET full_name_encrypted=:name, postal_code_encrypted=:cep, "
                    "address_encrypted=:addr, address_number_encrypted=:num, address_complement_encrypted=:comp, "
                    "city_encrypted=:city WHERE id=:id"
                ),
                {
                    "id": row["id"],
                    "name": seal("full_name", fields["legal_name"]),
                    "cep": seal("postal_code", fields["postal_code"]),
                    "addr": seal("address", address),
                    "num": seal("address_number", fields["number"]),
                    "comp": seal("address_complement", fields["complement"]),
                    "city": seal("city", fields["city"]),
                },
            )
        for column in ("legal_name", "postal_code", "address", "number", "complement", "neighborhood", "city"):
            _drop_column(conn, "billing_profiles", column)

    # 7. E-mail digitado em login que falhou --------------------------------- #
    if "login_audit_events" in tables:
        conn.execute(text("UPDATE login_audit_events SET detail=NULL WHERE event_type='login_failed'"))

    logger.info("migração v1.4 (privacidade) aplicada: %s", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "nada a converter")


MIGRATIONS: list[tuple[str, Callable[[Connection], None]]] = [
    ("2026.09.29-v1.4-privacy", _v14_privacy),
]


def _compact(engine: Engine) -> None:
    """Reescreve o arquivo sem as páginas livres (onde o texto puro antigo ainda estaria)."""
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.exec_driver_sql("VACUUM")
        conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")


def run_migrations(engine: Engine) -> list[str]:
    """Aplica, em ordem, as migrações ainda não registradas. Retorna as aplicadas."""
    applied: list[str] = []
    with engine.begin() as conn:
        done = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}
    for version, migrate in MIGRATIONS:
        if version in done:
            continue
        with engine.begin() as conn:
            migrate(conn)
            conn.execute(
                text("INSERT INTO schema_migrations (version, applied_at) VALUES (:v, :at)"),
                {"v": version, "at": _ts(utcnow())},
            )
        applied.append(version)
    if applied:
        _compact(engine)
    return applied
