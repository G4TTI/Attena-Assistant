"""Progresso do onboarding de primeiros passos (v1.3, itens 20-26).

Deliberadamente sem tabela própria: o progresso de cada etapa é sempre
derivado do estado real (existe uma `WhatsAppSession` conectada? existe uma
`CalendarConnection`? `User.timezone` já foi escolhido?) em vez de guardado
num rastro paralelo que poderia dessincronizar. A única coisa que precisa ser
lembrada é "esse usuário já terminou (ou pulou até o fim)?" — daí a única
coluna nova, `User.onboarding_completed_at`.
"""

from __future__ import annotations

from sqlmodel import Session, col, select

from . import calendar_service, whatsapp_service
from .clock import utcnow
from .models import AppSetting, User
from .waha import WahaClient

_LEGACY_MIGRATION_KEY = "onboarding_legacy_users_migrated"


def migrate_legacy_users(db: Session) -> None:
    """Idempotente, roda uma única vez no boot desta versão (mesmo padrão de
    `db.claim_orphan_data`, com uma flag em `AppSetting`): marca como "já
    concluiu o onboarding" todo usuário que já existia ANTES do onboarding
    existir. Sem isso, quem já usa o Attena normalmente cairia do nada numa
    tela de "primeiros passos" no próximo login — uma regressão, não uma
    melhoria. Contas criadas depois desta migração começam com
    `onboarding_completed_at` NULL de verdade, e são essas que devem ver o
    assistente.
    """
    if db.get(AppSetting, _LEGACY_MIGRATION_KEY) is not None:
        return
    pending = db.exec(select(User).where(col(User.onboarding_completed_at).is_(None))).all()
    now = utcnow()
    for user in pending:
        user.onboarding_completed_at = now
        db.add(user)
    db.add(AppSetting(key=_LEGACY_MIGRATION_KEY, value="done"))
    db.commit()


async def progress(db: Session, waha: WahaClient, user: User) -> dict:
    """Estado ao vivo das 3 etapas — sempre recalculado, nunca cacheado
    (mesma escolha de `whatsapp_service.status_rows`)."""
    sessions = whatsapp_service.list_sessions(db, user.id)
    # ensure=True: o usuário novo ainda não tem sessão no WAHA — ela nasce
    # aqui, na primeira vez que a etapa do WhatsApp é aberta.
    rows = await whatsapp_service.status_rows(waha, sessions, ensure=True)
    whatsapp_connected = any(str((row["status"] or {}).get("status") or "").upper() == "WORKING" for row in rows)
    return {
        "whatsapp_connected": whatsapp_connected,
        "whatsapp_session": sessions[0] if sessions else None,
        "whatsapp_row": rows[0] if rows else None,
        "google_connected": bool(calendar_service.list_connections(db, user.id)),
        "timezone_set": user.timezone is not None,
    }


def first_incomplete_step(state: dict) -> int:
    """1=WhatsApp, 2=Google Agenda, 3=Fuso horário, 4=Concluído."""
    if not state["whatsapp_connected"]:
        return 1
    if not state["google_connected"]:
        return 2
    if not state["timezone_set"]:
        return 3
    return 4


def finish(db: Session, user: User) -> None:
    user.onboarding_completed_at = utcnow()
    user.updated_at = utcnow()
    db.add(user)
    db.commit()
