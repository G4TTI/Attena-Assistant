"""Migração v1.4 (privacidade) sobre um banco com o schema REAL da v1.3.4
(tests/fixtures/schema_v1_3_4.sql — só estrutura, sem dados)."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, select

from tests.conftest import db_locations_containing
from whatsapp_scheduler import migrations, privacy
from whatsapp_scheduler.db import get_engine, init_db
from whatsapp_scheduler.models import AutomationMessage, BillingProfile, Dispatch, Schedule, ScheduleGroup

SCHEMA = (Path(__file__).parent / "fixtures" / "schema_v1_3_4.sql").read_text(encoding="utf-8")
T = "2026-09-01 12:00:00.000000"
FUTURE = "2999-01-01 09:00:00.000000"


def _drop_everything() -> None:
    """Apaga TODAS as tabelas (inclusive as que não estão nos modelos, como a
    antiga cached_messages). Descarta o pool antes/depois: uma conexão antiga
    com leitura em aberto enxergaria o schema anterior (snapshot do WAL)."""
    engine = get_engine()
    engine.dispose()
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for (name,) in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")).all():
            conn.execute(text(f'DROP TABLE IF EXISTS "{name}"'))
    engine.dispose()


def _reset_to_v13() -> None:
    _drop_everything()
    with get_engine().begin() as conn:
        for statement in SCHEMA.split(";\n"):
            if statement.strip():
                conn.exec_driver_sql(statement)
    get_engine().dispose()


def _seed(conn) -> None:
    q = conn.exec_driver_sql
    q(f"INSERT INTO users VALUES ('u1','Dona','dona@example.com','hash','+5511999990000','s1',NULL,1,1,'{T}','{T}','{T}')")
    q(f"INSERT INTO users VALUES ('u2','Outra','outra@example.com','hash',NULL,'s2',NULL,0,1,'{T}','{T}','{T}')")
    q(f"INSERT INTO whatsapp_sessions VALUES ('w1','u1','WhatsApp','s1',NULL,NULL,'{T}','{T}')")
    q(f"INSERT INTO schedule_groups VALUES ('g_active','u1','manual','s1','+55 14 99111-0001','João Ativo','5514991110001@c.us','America/Sao_Paulo','{FUTURE}',3,'{T}','{T}')")
    q(f"INSERT INTO schedule_groups VALUES ('g_done','u1','manual','s1','+55 11 98888-7777','Maria Encerrada','5511988887777@c.us','America/Sao_Paulo','{T}',3,'{T}','{T}')")
    q(f"INSERT INTO schedules VALUES ('s_active','u1','g_active',0,'s1','+55 14 99111-0001','5514991110001@c.us','mensagem ativa secreta','America/Sao_Paulo','{FUTURE}',NULL,1,3,'{T}','{T}')")
    q(f"INSERT INTO schedules VALUES ('s_done','u1','g_done',0,'s1','+55 11 98888-7777','5511988887777@c.us','mensagem enviada secreta','America/Sao_Paulo','{T}',NULL,0,3,'{T}','{T}')")
    q(f"INSERT INTO schedules VALUES ('s_fail','u1','g_done',1,'s1','+55 11 98888-7777','5511988887777@c.us','outra enviada secreta','America/Sao_Paulo','{T}',NULL,0,3,'{T}','{T}')")
    q(f"INSERT INTO dispatches VALUES ('d_active','s_active','{FUTURE}','pending',0,NULL,NULL,NULL,'{T}','{T}')")
    q(f"INSERT INTO dispatches VALUES ('d_done','s_done','{T}','sent',0,NULL,'true_5511988887777@c.us_3EB0ABC','{T}','{T}','{T}')")
    q(f"""INSERT INTO dispatches VALUES ('d_fail','s_fail','{T}','failed',3,'WAHA respondeu 400 em POST /api/sendText: {{"chatId":"5511988887777@c.us","text":"outra enviada secreta"}}',NULL,NULL,'{T}','{T}')""")
    q(f"INSERT INTO events VALUES ('e1','u1','internal',NULL,NULL,NULL,'Consulta','', '{FUTURE}','{FUTURE}','America/Sao_Paulo',0,'confirmed',NULL,'{T}','{T}')")
    q(f"INSERT INTO automations VALUES ('a1','e1',1,'hours','before',NULL,NULL,3,'{T}','{T}')")
    q(f"INSERT INTO automation_messages VALUES ('m1','a1',0,'texto automação secreta','{T}','{T}')")
    q(f"INSERT INTO automation_schedules VALUES ('as1','a1','m1','s_active','5514991110001@c.us','{T}')")
    q(f"INSERT INTO cached_messages VALUES ('MID1','u1','5514991110001@c.us',1760000000,0,'conversa recebida secreta','chat',0,NULL,'{T}')")
    q(f"INSERT INTO cached_messages VALUES ('MID2','u1','5514991110001@c.us',1760000001,1,'resposta enviada secreta','chat',0,NULL,'{T}')")
    q(f"INSERT INTO billing_profiles VALUES ('b1','u1','','','','','','','','','','{T}','{T}')")
    q(f"INSERT INTO billing_profiles VALUES ('b2','u2','Fulano Legal','01310100','Rua Secreta','10','','Centro','Cidade X','SP','BR','{T}','{T}')")
    q(f"INSERT INTO login_audit_events VALUES ('l1',NULL,'login_failed','digitado@example.com','203.0.113.1','UA','{T}')")


@pytest.fixture
def migrated():
    _reset_to_v13()
    with get_engine().begin() as conn:
        _seed(conn)
    init_db()
    yield
    _drop_everything()


def _columns(table: str) -> set[str]:
    with get_engine().connect() as conn:
        return {r[1] for r in conn.execute(text(f"PRAGMA table_info({table})"))}


def test_plaintext_columns_and_conversation_cache_are_gone(migrated):
    assert not {"text", "recipient_input", "chat_id"} & _columns("schedules")
    assert not {"recipient_input", "recipient_name", "chat_id"} & _columns("schedule_groups")
    assert "text" not in _columns("automation_messages")
    assert "recipient_chat_id" not in _columns("automation_schedules")
    assert "waha_message_id" not in _columns("dispatches")
    assert not {"legal_name", "postal_code", "address", "number", "complement", "neighborhood", "city"} & _columns("billing_profiles")
    with get_engine().connect() as conn:
        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert "cached_messages" not in tables


def test_no_plaintext_left_anywhere(migrated):
    for needle in ("secreta", "99111", "98888", "João Ativo", "Maria Encerrada", "Fulano Legal", "Rua Secreta",
                   "01310100", "digitado@example.com", "3EB0ABC"):
        assert db_locations_containing(needle) == [], needle


def test_active_data_is_encrypted_and_still_usable(migrated):
    with Session(get_engine()) as db:
        active = db.get(Schedule, "s_active")
        assert privacy.schedule_message(active) == "mensagem ativa secreta"
        assert privacy.schedule_recipient(active) == "5514991110001@c.us"
        assert active.recipient_phone_hash == privacy.recipient_hash("u1", "5514991110001@c.us")
        info = privacy.group_recipient(db.get(ScheduleGroup, "g_active"))
        assert (info.name, info.input) == ("João Ativo", "+55 14 99111-0001")
        assert privacy.automation_message(db.get(AutomationMessage, "m1")) == "texto automação secreta"


def test_finished_data_is_purged_but_metrics_survive(migrated):
    with Session(get_engine()) as db:
        done = db.get(Schedule, "s_done")
        assert done.message_ciphertext is None and done.recipient_phone_encrypted is None and done.content_purged_at
        assert done.recipient_phone_hash  # só o HMAC, por 30 dias (retenção)
        group = db.get(ScheduleGroup, "g_done")
        assert group.recipient_encrypted is None and group.recipient_phone_hash
        sent = db.get(Dispatch, "d_done")
        assert sent.status == "sent" and sent.waha_message_hash == privacy.waha_message_hash("u1", "true_5511988887777@c.us_3EB0ABC")
        failed = db.get(Dispatch, "d_fail")
        assert failed.failure_code == "waha_rejected" and "5511988887777" not in failed.last_error


def test_billing_profiles_empty_removed_filled_encrypted(migrated):
    with Session(get_engine()) as db:
        profiles = db.exec(select(BillingProfile)).all()
        assert [p.id for p in profiles] == ["b2"]
        b2 = profiles[0]
        assert privacy.open_field("billing_profiles", "full_name", b2.id, b2.full_name_encrypted) == "Fulano Legal"
        assert privacy.open_field("billing_profiles", "address", b2.id, b2.address_encrypted) == "Rua Secreta — Centro"
        assert b2.state == "SP"


def test_migration_is_recorded_and_idempotent(migrated):
    with get_engine().connect() as conn:
        versions = [r[0] for r in conn.execute(text("SELECT version FROM schema_migrations"))]
    assert versions == ["2026.09.29-v1.4-privacy"]
    init_db()  # de novo: nada a fazer, nada quebra
    assert migrations.run_migrations(get_engine()) == []


def test_migration_is_atomic_on_failure(monkeypatch):
    """Se algo falha no meio, NADA é aplicado (o texto puro não é perdido sem cifrar)."""
    _reset_to_v13()
    with get_engine().begin() as conn:
        _seed(conn)
    calls = {"n": 0}
    real = privacy.seal_automation_message

    def boom(*args, **kwargs):
        calls["n"] += 1
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(privacy, "seal_automation_message", boom)
    with pytest.raises(RuntimeError):
        init_db()
    assert "text" in _columns("schedules")  # nada foi removido
    with get_engine().connect() as conn:
        assert conn.execute(text("SELECT text FROM schedules WHERE id='s_active'")).scalar() == "mensagem ativa secreta"
        assert conn.execute(text("SELECT message_ciphertext FROM schedules WHERE id='s_active'")).scalar() is None
        assert not conn.execute(text("SELECT version FROM schema_migrations")).all()
    monkeypatch.setattr(privacy, "seal_automation_message", real)
    init_db()  # na próxima subida, aplica inteira
    assert "text" not in _columns("schedules") and calls["n"] == 1
    _drop_everything()
