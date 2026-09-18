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
from sqlmodel import Session, SQLModel, col, create_engine

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
    ("cached_messages", "user_id", "ALTER TABLE cached_messages ADD COLUMN user_id TEXT"),
    # Onboarding (v1.3) — NULL = ainda não terminou; `onboarding_service.
    # migrate_legacy_users` marca retroativamente quem já existia como
    # concluído, então só conta nova de verdade fica pendente.
    ("users", "onboarding_completed_at", "ALTER TABLE users ADD COLUMN onboarding_completed_at TEXT"),
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
        cursor.close()

    return engine


def _apply_column_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        for table, column, ddl in _COLUMN_MIGRATIONS:
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if column not in existing:
                conn.execute(text(ddl))


# Índices compostos para as consultas quentes (grade/agenda do calendário e o
# tick do scheduler) — `create_all` não adiciona índice a tabela que já
# existe, então entram aqui, idempotentes e aditivos (não mexem em dado).
_INDEX_MIGRATIONS: list[str] = [
    "CREATE INDEX IF NOT EXISTS ix_events_user_start ON events (user_id, start_utc)",
    "CREATE INDEX IF NOT EXISTS ix_dispatches_status_scheduled ON dispatches (status, scheduled_at_utc)",
    "CREATE INDEX IF NOT EXISTS ix_dispatches_schedule_status ON dispatches (schedule_id, status)",
]


def _apply_index_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        for ddl in _INDEX_MIGRATIONS:
            conn.execute(text(ddl))


def init_db() -> None:
    # importa os modelos para registrar as tabelas no metadata
    from . import models  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _apply_column_migrations(engine)
    _apply_index_migrations(engine)


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
    from .models import AppSetting, CalendarConnection, CachedMessage, Event, Schedule

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

    db.exec(
        sa_update(Schedule)
        .where(col(Schedule.user_id).is_(None))
        .values(user_id=user.id, session=user.waha_session)
    )
    db.exec(sa_update(CalendarConnection).where(col(CalendarConnection.user_id).is_(None)).values(user_id=user.id))
    db.exec(sa_update(Event).where(col(Event.user_id).is_(None)).values(user_id=user.id))
    db.exec(sa_update(CachedMessage).where(col(CachedMessage.user_id).is_(None)).values(user_id=user.id))
    db.add(AppSetting(key=_ORPHAN_CLAIM_SETTING_KEY, value=user.id, updated_at=utcnow()))
    db.commit()
    return True
