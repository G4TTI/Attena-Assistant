"""Regra de negócio de conexões WhatsApp (v1.3: um usuário pode ter várias).
Equivalente a `calendar_service.py`, mas para `WhatsAppSession` — o cliente
WAHA em si (start/restart/QR/status) continua chamado diretamente pela rota,
mesmo padrão que `web/routes.py` já usa hoje para a sessão única.
"""

from __future__ import annotations

from sqlmodel import Session, col, select

from .clock import utcnow
from .models import Schedule, User, WhatsAppSession
from .service import ValidationError, cancel_schedule


def migrate_legacy_sessions(db: Session) -> None:
    """Idempotente, chamada no boot (main.py lifespan) — mesmo padrão de
    `calendar_service.migrate_legacy_automations`. Cria, para cada usuário
    que ainda não tem nenhuma `WhatsAppSession`, uma primeira linha usando o
    `User.waha_session` (v1.2, único por usuário) já existente — preserva o
    pareamento já feito, sem exigir escanear QR de novo. Nunca cria uma
    segunda linha nem duplica: só roda para quem tem zero sessões.
    """
    users = db.exec(select(User)).all()
    if not users:
        return
    has_session = {
        row for row in db.exec(select(WhatsAppSession.user_id)).all()
    }
    migrated = 0
    for user in users:
        if user.id in has_session:
            continue
        db.add(
            WhatsAppSession(
                user_id=user.id,
                name="WhatsApp",
                session_name=user.waha_session,
            )
        )
        migrated += 1
    if migrated:
        db.commit()


def list_sessions(db: Session, user_id: str) -> list[WhatsAppSession]:
    return list(
        db.exec(
            select(WhatsAppSession)
            .where(col(WhatsAppSession.user_id) == user_id)
            .where(col(WhatsAppSession.disconnected_at).is_(None))
            .order_by(col(WhatsAppSession.created_at))
        ).all()
    )


def get_session(db: Session, session_id: str, user_id: str) -> WhatsAppSession | None:
    """Sempre valida o dono — nunca retorna a sessão de outro usuário mesmo
    que o `session_id` exista no banco (proteção contra IDOR, Parte 4/42)."""
    session = db.get(WhatsAppSession, session_id)
    if session is None or session.user_id != user_id:
        return None
    return session


def session_by_name(db: Session, user_id: str, session_name: str) -> WhatsAppSession | None:
    """Usada para validar, antes de gravar em `Schedule.session`, que um
    `session_name` recebido do cliente (formulário/API) realmente pertence ao
    usuário autenticado — nunca confia num nome de sessão cru vindo de fora."""
    return db.exec(
        select(WhatsAppSession)
        .where(col(WhatsAppSession.user_id) == user_id)
        .where(col(WhatsAppSession.session_name) == session_name)
        .where(col(WhatsAppSession.disconnected_at).is_(None))
    ).first()


def create_session(db: Session, user_id: str, name: str) -> WhatsAppSession:
    name = (name or "").strip() or "WhatsApp"
    session = WhatsAppSession(user_id=user_id, name=name)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def rename_session(db: Session, session_id: str, user_id: str, name: str) -> WhatsAppSession | None:
    session = get_session(db, session_id, user_id)
    if session is None:
        return None
    name = (name or "").strip()
    if not name:
        raise ValidationError("Informe um nome para esta conexão.")
    session.name = name
    session.updated_at = utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def disconnect_session(db: Session, session_id: str, user_id: str) -> bool:
    """Para novos disparos por esta conexão e cancela mensagens futuras ainda
    pendentes que a usavam — preserva histórico e mensagens já enviadas
    (mesmo padrão de `calendar_service.disconnect`)."""
    session = get_session(db, session_id, user_id)
    if session is None:
        return False

    open_schedules = db.exec(
        select(Schedule)
        .where(col(Schedule.user_id) == user_id)
        .where(col(Schedule.session) == session.session_name)
        .where(col(Schedule.enabled).is_(True))
    ).all()
    for schedule in open_schedules:
        cancel_schedule(db, schedule.id, user_id=user_id)

    session.disconnected_at = utcnow()
    session.updated_at = utcnow()
    db.add(session)
    db.commit()
    return True


def labels_by_session_name(db: Session, user_id: str) -> dict[str, str]:
    """`Schedule.session` -> nome de exibição, incluindo conexões já
    desconectadas (histórico antigo ainda precisa mostrar qual WhatsApp foi
    usado — Parte 17)."""
    rows = db.exec(select(WhatsAppSession).where(col(WhatsAppSession.user_id) == user_id)).all()
    return {row.session_name: row.name for row in rows}
