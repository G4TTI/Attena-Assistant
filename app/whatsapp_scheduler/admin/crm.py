"""CRM administrativo: status comercial, tags e notas internas de cada cliente.

São dados da RELAÇÃO COMERCIAL com o cliente do Attena — nunca cópia do que
ele conversa no WhatsApp. As notas são cifradas em repouso, têm limite de
tamanho e recusam texto com cara de conversa exportada do WhatsApp.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from .. import privacy
from ..clock import utcnow
from ..errors import ValidationError
from ..models import CrmNote, CrmProfile, CrmTag, CrmUserTag, User

# Configuráveis aqui (um lugar só): chave -> rótulo.
CRM_STATUSES: dict[str, str] = {
    "lead": "Lead",
    "trial": "Trial",
    "ativo": "Ativo",
    "inadimplente": "Inadimplente",
    "cancelado": "Cancelado",
    "churn": "Churn",
    "suspenso": "Suspenso",
}
DEFAULT_TAGS = ("Early adopter", "Empresa", "Personal trainer", "Academia", "Beta tester")
NOTE_MAX_LENGTH = 2000
TAG_MAX_LENGTH = 40

# "[29/09/2026 10:15] Fulano: ..." / "29/09/2026 10:15 - Fulano: ..." (exportação de conversa)
_CHAT_EXPORT = re.compile(r"(\[\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}(:\d{2})?\]|\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2} - )[^:\n]{1,60}:")


def seed_default_tags(db: Session) -> None:
    if db.exec(select(func.count()).select_from(CrmTag)).one():
        return
    for name in DEFAULT_TAGS:
        db.add(CrmTag(name=name))
    db.commit()


def status_of(db: Session, user_id: str) -> str:
    profile = db.get(CrmProfile, user_id)
    return profile.status if profile else "lead"


def set_status(db: Session, user_id: str, status: str, admin: User) -> tuple[str, str]:
    if status not in CRM_STATUSES:
        raise ValidationError("Status de CRM inválido.")
    profile = db.get(CrmProfile, user_id) or CrmProfile(user_id=user_id)
    previous = profile.status if profile.status else "lead"
    profile.status = status
    profile.updated_at = utcnow()
    profile.updated_by = admin.id
    db.add(profile)
    db.commit()
    return previous, status


def list_tags(db: Session) -> list[CrmTag]:
    return list(db.exec(select(CrmTag).order_by(col(CrmTag.name))).all())


def user_tags(db: Session, user_id: str) -> list[CrmTag]:
    return list(
        db.exec(
            select(CrmTag)
            .join(CrmUserTag, col(CrmUserTag.tag_id) == col(CrmTag.id))
            .where(col(CrmUserTag.user_id) == user_id)
            .order_by(col(CrmTag.name))
        ).all()
    )


def get_or_create_tag(db: Session, name: str, admin: User) -> tuple[CrmTag, bool]:
    name = " ".join((name or "").split())
    if not name:
        raise ValidationError("Informe o nome da tag.")
    if len(name) > TAG_MAX_LENGTH:
        raise ValidationError(f"A tag pode ter no máximo {TAG_MAX_LENGTH} caracteres.")
    existing = next((t for t in list_tags(db) if t.name.lower() == name.lower()), None)
    if existing is not None:
        return existing, False
    tag = CrmTag(name=name, created_by=admin.id)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag, True


def add_tag(db: Session, user_id: str, tag: CrmTag, admin: User) -> bool:
    if db.get(CrmUserTag, (user_id, tag.id)) is not None:
        return False
    db.add(CrmUserTag(user_id=user_id, tag_id=tag.id, created_by=admin.id))
    db.commit()
    return True


def remove_tag(db: Session, user_id: str, tag_id: str) -> CrmTag | None:
    link = db.get(CrmUserTag, (user_id, tag_id))
    if link is None:
        return None
    tag = db.get(CrmTag, tag_id)
    db.delete(link)
    db.commit()
    return tag


def delete_tag(db: Session, tag_id: str) -> CrmTag | None:
    tag = db.get(CrmTag, tag_id)
    if tag is None:
        return None
    for link in db.exec(select(CrmUserTag).where(col(CrmUserTag.tag_id) == tag_id)).all():
        db.delete(link)
    db.delete(tag)
    db.commit()
    return tag


def _clean_note(body: str) -> str:
    body = (body or "").strip()
    if not body:
        raise ValidationError("A nota não pode ficar vazia.")
    if len(body) > NOTE_MAX_LENGTH:
        raise ValidationError(f"A nota pode ter no máximo {NOTE_MAX_LENGTH} caracteres.")
    if _CHAT_EXPORT.search(body):
        raise ValidationError(
            "Parece o trecho de uma conversa do WhatsApp. Notas do CRM são só sobre a relação comercial — "
            "não copie conteúdo de conversas dos clientes."
        )
    return body


@dataclass
class NoteView:
    id: str
    body: str
    created_at: datetime
    created_by: str | None
    updated_at: datetime | None
    updated_by: str | None


def list_notes(db: Session, user_id: str) -> list[NoteView]:
    notes = db.exec(select(CrmNote).where(col(CrmNote.user_id) == user_id).order_by(col(CrmNote.created_at).desc())).all()
    authors = {
        u.id: u.name
        for u in db.exec(
            select(User).where(col(User.id).in_({n.created_by for n in notes} | {n.updated_by for n in notes if n.updated_by}))
        ).all()
    } if notes else {}
    return [
        NoteView(
            id=n.id, body=privacy.crm_note_body(n), created_at=n.created_at, created_by=authors.get(n.created_by or "", "—"),
            updated_at=n.updated_at, updated_by=authors.get(n.updated_by or "") if n.updated_by else None,
        )
        for n in notes
    ]


def add_note(db: Session, user_id: str, body: str, admin: User) -> CrmNote:
    note = CrmNote(user_id=user_id, body_encrypted="", created_by=admin.id)
    privacy.seal_crm_note(note, _clean_note(body))
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_note(db: Session, user_id: str, note_id: str, body: str, admin: User) -> CrmNote | None:
    note = db.get(CrmNote, note_id)
    if note is None or note.user_id != user_id:
        return None
    privacy.seal_crm_note(note, _clean_note(body))
    note.updated_at = utcnow()
    note.updated_by = admin.id
    db.add(note)
    db.commit()
    return note


def delete_note(db: Session, user_id: str, note_id: str) -> bool:
    note = db.get(CrmNote, note_id)
    if note is None or note.user_id != user_id:
        return False
    db.delete(note)
    db.commit()
    return True
