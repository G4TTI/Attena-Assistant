"""Engine SQLite + helpers de sessão.

SQLite em modo WAL: leituras não bloqueiam a escrita e a escrita (única, feita
pelo poller) não bloqueia as leituras da API/UI. `busy_timeout` evita
`database is locked` sob concorrência leve.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy import update as sa_update
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, col, create_engine, select

from .clock import utcnow
from .config import settings

# Colunas adicionadas a tabelas já existentes depois do primeiro deploy —
# create_all() só cria tabelas novas, nunca altera uma que já existe (ver
# comentário em models.py). Lista (tabela, coluna, DDL) aplicada de forma
# idempotente em init_db(); aditiva e nullable, nunca toca dado existente.
_COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    ("automations", "custom_time_local", "ALTER TABLE automations ADD COLUMN custom_time_local TEXT"),
    # Colunas de dono adicionadas quando a autenticação chegou — nullable e
    # aditivas, nenhum dado existente é tocado. Linhas antigas (user_id NULL)
    # ficam invisíveis para todo mundo até `claim_orphan_data` associá-las ao
    # primeiro usuário cadastrado (ver essa função abaixo).
    ("schedules", "user_id", "ALTER TABLE schedules ADD COLUMN user_id TEXT"),
    ("calendar_connections", "user_id", "ALTER TABLE calendar_connections ADD COLUMN user_id TEXT"),
    ("events", "user_id", "ALTER TABLE events ADD COLUMN user_id TEXT"),
    # Onboarding (v1.3) — NULL = ainda não terminou; `onboarding_service.
    # migrate_legacy_users` marca retroativamente quem já existia como
    # concluído, então só conta nova de verdade fica pendente.
    ("users", "onboarding_completed_at", "ALTER TABLE users ADD COLUMN onboarding_completed_at TEXT"),
    # Agendamento único (v1.3.3): cada mensagem pertence a um `ScheduleGroup` e
    # tem uma posição na sequência. `service.backfill_groups` preenche as
    # linhas antigas no boot.
    ("schedules", "group_id", "ALTER TABLE schedules ADD COLUMN group_id TEXT"),
    ("schedules", "position", "ALTER TABLE schedules ADD COLUMN position INTEGER NOT NULL DEFAULT 0"),
    ("automations", "custom_interval", "ALTER TABLE automations ADD COLUMN custom_interval TEXT"),
    # v1.4 (privacidade): colunas cifradas + HMAC. A conversão dos dados antigos
    # (texto puro -> cifrado/expurgado) e a remoção das colunas em texto puro
    # ficam em migrations.py, que roda logo depois disto.
    ("schedules", "message_ciphertext", "ALTER TABLE schedules ADD COLUMN message_ciphertext TEXT"),
    ("schedules", "encryption_nonce", "ALTER TABLE schedules ADD COLUMN encryption_nonce TEXT"),
    ("schedules", "encryption_key_version", "ALTER TABLE schedules ADD COLUMN encryption_key_version INTEGER"),
    ("schedules", "recipient_phone_encrypted", "ALTER TABLE schedules ADD COLUMN recipient_phone_encrypted TEXT"),
    ("schedules", "recipient_phone_hash", "ALTER TABLE schedules ADD COLUMN recipient_phone_hash TEXT"),
    ("schedules", "content_purged_at", "ALTER TABLE schedules ADD COLUMN content_purged_at DATETIME"),
    ("schedule_groups", "recipient_encrypted", "ALTER TABLE schedule_groups ADD COLUMN recipient_encrypted TEXT"),
    ("schedule_groups", "recipient_phone_hash", "ALTER TABLE schedule_groups ADD COLUMN recipient_phone_hash TEXT"),
    ("schedule_groups", "content_purged_at", "ALTER TABLE schedule_groups ADD COLUMN content_purged_at DATETIME"),
    ("automation_messages", "message_ciphertext", "ALTER TABLE automation_messages ADD COLUMN message_ciphertext TEXT"),
    ("automation_messages", "encryption_nonce", "ALTER TABLE automation_messages ADD COLUMN encryption_nonce TEXT"),
    ("automation_messages", "encryption_key_version", "ALTER TABLE automation_messages ADD COLUMN encryption_key_version INTEGER"),
    ("automation_messages", "content_purged_at", "ALTER TABLE automation_messages ADD COLUMN content_purged_at DATETIME"),
    ("automation_schedules", "recipient_phone_hash", "ALTER TABLE automation_schedules ADD COLUMN recipient_phone_hash TEXT"),
    ("dispatches", "failure_code", "ALTER TABLE dispatches ADD COLUMN failure_code TEXT"),
    ("dispatches", "waha_message_hash", "ALTER TABLE dispatches ADD COLUMN waha_message_hash TEXT"),
    ("users", "role", "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"),
    ("users", "last_login_at", "ALTER TABLE users ADD COLUMN last_login_at DATETIME"),
    ("users", "last_activity_at", "ALTER TABLE users ADD COLUMN last_activity_at DATETIME"),
    ("users", "login_count", "ALTER TABLE users ADD COLUMN login_count INTEGER NOT NULL DEFAULT 0"),
    ("whatsapp_sessions", "waha_purged_at", "ALTER TABLE whatsapp_sessions ADD COLUMN waha_purged_at DATETIME"),
    ("billing_profiles", "full_name_encrypted", "ALTER TABLE billing_profiles ADD COLUMN full_name_encrypted TEXT"),
    ("billing_profiles", "cpf_encrypted", "ALTER TABLE billing_profiles ADD COLUMN cpf_encrypted TEXT"),
    ("billing_profiles", "cpf_last2", "ALTER TABLE billing_profiles ADD COLUMN cpf_last2 TEXT"),
    ("billing_profiles", "phone_encrypted", "ALTER TABLE billing_profiles ADD COLUMN phone_encrypted TEXT"),
    ("billing_profiles", "postal_code_encrypted", "ALTER TABLE billing_profiles ADD COLUMN postal_code_encrypted TEXT"),
    ("billing_profiles", "address_encrypted", "ALTER TABLE billing_profiles ADD COLUMN address_encrypted TEXT"),
    ("billing_profiles", "address_number_encrypted", "ALTER TABLE billing_profiles ADD COLUMN address_number_encrypted TEXT"),
    ("billing_profiles", "address_complement_encrypted", "ALTER TABLE billing_profiles ADD COLUMN address_complement_encrypted TEXT"),
    ("billing_profiles", "city_encrypted", "ALTER TABLE billing_profiles ADD COLUMN city_encrypted TEXT"),
]


@lru_cache
def get_engine() -> Engine:
    db_path = Path(settings.db_path)
    if db_path.parent and str(db_path.parent) not in ("", "."):
        db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        # NORMAL em WAL não faz fsync a cada commit (só nos checkpoints): a
        # recomendação padrão do SQLite pra WAL, sem risco de corromper o
        # banco — o pior caso numa queda de energia é perder os últimos
        # commits, nunca o arquivo. Com o banco num bind mount do Docker no
        # Windows, cada fsync custa dezenas de ms e criar/sincronizar dezenas
        # de registros virava segundos de servidor travado.
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        # Conteúdo apagado/sobrescrito (ex.: mensagem expurgada depois do
        # envio) é zerado no arquivo, em vez de ficar recuperável nas páginas
        # livres do SQLite.
        cursor.execute("PRAGMA secure_delete=ON")
        cursor.close()

    return engine


def _apply_column_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        for table, column, ddl in _COLUMN_MIGRATIONS:
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if existing and column not in existing:  # tabela inexistente: create_all já a criou nova (ou foi removida)
                conn.execute(text(ddl))


# Índices compostos para as consultas quentes (grade/agenda do calendário e o
# tick do scheduler) — `create_all` não adiciona índice a tabela que já
# existe, então entram aqui, idempotentes e aditivos (não mexem em dado).
_INDEX_MIGRATIONS: list[str] = [
    "CREATE INDEX IF NOT EXISTS ix_events_user_start ON events (user_id, start_utc)",
    "CREATE INDEX IF NOT EXISTS ix_dispatches_status_scheduled ON dispatches (status, scheduled_at_utc)",
    "CREATE INDEX IF NOT EXISTS ix_dispatches_schedule_status ON dispatches (schedule_id, status)",
    # Mesmo nome que o SQLAlchemy dá ao índice de `Schedule.group_id` (index=True):
    # banco novo já o cria; banco migrado (tabela pré-existente) só ganha aqui.
    "CREATE INDEX IF NOT EXISTS ix_schedules_group_id ON schedules (group_id)",
    "CREATE INDEX IF NOT EXISTS ix_schedules_user_recipient ON schedules (user_id, session, recipient_phone_hash)",
    "CREATE INDEX IF NOT EXISTS ix_schedules_recipient_phone_hash ON schedules (recipient_phone_hash)",
    "CREATE INDEX IF NOT EXISTS ix_schedule_groups_recipient_phone_hash ON schedule_groups (recipient_phone_hash)",
    "CREATE INDEX IF NOT EXISTS ix_automation_schedules_recipient_phone_hash ON automation_schedules (recipient_phone_hash)",
    "CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)",
]


def _apply_index_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        for ddl in _INDEX_MIGRATIONS:
            conn.execute(text(ddl))


def init_db() -> None:
    # importa os modelos para registrar as tabelas no metadata
    from . import models  # noqa: F401

    from .migrations import run_migrations

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _apply_column_migrations(engine)
    _apply_index_migrations(engine)
    run_migrations(engine)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


_ORPHAN_CLAIM_SETTING_KEY = "orphan_data_claimed_by"


def claim_orphan_data(db: Session, user) -> bool:  # user: models.User (evita import circular no topo)
    """Associa ao primeiro usuário cadastrado todo dado criado antes da
    autenticação existir (`user_id IS NULL`). Não roda no boot do processo —
    só quando alguém de fato se cadastra — porque não existe usuário nenhum
    pra reivindicar os dados antes disso (Parte 47: nunca criar uma conta
    admin/senha padrão automática). Guardado por uma flag em `AppSetting`,
    não por estado em memória: idempotente entre reinícios, e a segunda
    conta cadastrada depois não rouba os dados da primeira. Nenhuma linha é
    apagada — só ganha `user_id` (e os schedules órfãos passam a usar a
    sessão WAHA do usuário que os reivindicou, preservando o disparo).
    """
    from . import privacy
    from .models import AppSetting, CalendarConnection, Event, Schedule

    if db.get(AppSetting, _ORPHAN_CLAIM_SETTING_KEY) is not None:
        return False

    # A sessão WAHA já pareada antes de existir autenticação continua com o
    # nome vindo do .env (`settings.waha_session`, ex. "default") — o
    # primeiro usuário herda esse MESMO nome (não o gerado automaticamente
    # em User.waha_session) pra não perder o pareamento já feito e obrigar a
    # escanear o QR code de novo.
    user.waha_session = settings.waha_session
    user.updated_at = utcnow()
    db.add(user)

    # O hash do destinatário é por usuário: sem dono ele foi calculado com o
    # escopo vazio e precisa ser refeito com o id de quem reivindicou.
    for schedule in db.exec(select(Schedule).where(col(Schedule.user_id).is_(None))).all():
        schedule.user_id = user.id
        schedule.session = user.waha_session
        chat_id = privacy.schedule_recipient(schedule, safe=True)
        schedule.recipient_phone_hash = privacy.recipient_hash(user.id, chat_id) if chat_id else None
        db.add(schedule)
    db.exec(sa_update(CalendarConnection).where(col(CalendarConnection.user_id).is_(None)).values(user_id=user.id))
    db.exec(sa_update(Event).where(col(Event.user_id).is_(None)).values(user_id=user.id))
    db.add(AppSetting(key=_ORPHAN_CLAIM_SETTING_KEY, value=user.id, updated_at=utcnow()))
    db.commit()
    return True
