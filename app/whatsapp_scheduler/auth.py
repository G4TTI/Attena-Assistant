"""Primitivas de autenticação: hash de senha, sessão (cookie httponly) e
tokens de uso único (reset de senha / verificação de e-mail).

Separado de `auth_service.py` (regra de negócio: cadastro, login, fluxo de
recuperação) do mesmo jeito que `crypto.py` fica separado de
`calendar_service.py` — este módulo não sabe nada sobre e-mail, formulário
ou UI, só sobre como gerar/validar credenciais com segurança.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from fastapi import Depends, Request, Response
from sqlmodel import Session, col, select

from .clock import utcnow
from .config import settings
from .db import get_session
from .models import User, UserSession

_hasher = PasswordHasher()

# Sessão "tocada" no máximo 1x a cada 5min — evita um UPDATE a cada request.
_TOUCH_MIN_INTERVAL = timedelta(minutes=5)


class NotAuthenticated(Exception):
    """Levantada por `require_user_web` — main.py converte em redirect pro login."""

    def __init__(self, next_path: str = "/") -> None:
        self.next_path = next_path


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash):
        return False


def generate_token() -> str:
    """Token opaco de alta entropia — usado tanto pro cookie de sessão quanto
    pelos links de reset/verificação. Nunca persistido em texto puro (ver
    `hash_token`)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """SHA-256 é suficiente aqui (não Argon2id): o "segredo" já é um token
    aleatório de 256 bits, não uma senha de usuário sujeita a força bruta por
    dicionário — o mesmo padrão usado por sessões "remember me" na maioria
    dos frameworks. Um vazamento do banco não permite reconstruir o token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def client_ip(request: Request) -> str | None:
    if settings.client_ip_header:
        forwarded = request.headers.get(settings.client_ip_header, "")
        # X-Forwarded-For pode trazer "cliente, proxy1, proxy2": o primeiro é o visitante.
        first = forwarded.split(",")[0].strip()[:64]
        if first:
            return first
    return request.client.host if request.client else None


def client_user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:300] if ua else None


# --------------------------------------------------------------------------- #
# Sessão (cookie httponly)
# --------------------------------------------------------------------------- #
def create_user_session(db: Session, user: User, request: Request) -> tuple[UserSession, str]:
    raw_token = generate_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utcnow() + timedelta(days=settings.session_ttl_days),
        user_agent=client_user_agent(request),
        ip_address=client_ip(request),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token


def set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")


def _touch_session(db: Session, session: UserSession) -> None:
    now = utcnow()
    if now - session.last_seen_at < _TOUCH_MIN_INTERVAL:
        return
    session.last_seen_at = now
    db.add(session)
    db.commit()


def get_current_session(request: Request, db: Session) -> UserSession | None:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        return None
    session = db.exec(select(UserSession).where(col(UserSession.token_hash) == hash_token(raw_token))).first()
    if session is None or session.revoked_at is not None or session.expires_at < utcnow():
        return None
    return session


def revoke_session(db: Session, session: UserSession) -> None:
    session.revoked_at = utcnow()
    db.add(session)
    db.commit()


def revoke_other_sessions(db: Session, user: User, *, keep_session_id: str) -> int:
    others = db.exec(
        select(UserSession)
        .where(col(UserSession.user_id) == user.id)
        .where(col(UserSession.revoked_at).is_(None))
        .where(col(UserSession.id) != keep_session_id)
    ).all()
    now = utcnow()
    for session in others:
        session.revoked_at = now
        db.add(session)
    db.commit()
    return len(others)


def revoke_all_sessions(db: Session, user: User) -> int:
    """Usado após redefinição de senha — nenhuma sessão antiga sobrevive a
    uma senha comprometida (mesmo que o próprio dono nunca tenha percebido)."""
    sessions = db.exec(
        select(UserSession)
        .where(col(UserSession.user_id) == user.id)
        .where(col(UserSession.revoked_at).is_(None))
    ).all()
    now = utcnow()
    for session in sessions:
        session.revoked_at = now
        db.add(session)
    db.commit()
    return len(sessions)


# --------------------------------------------------------------------------- #
# Dependencies do FastAPI
# --------------------------------------------------------------------------- #
def get_current_user_optional(request: Request, db: Session = Depends(get_session)) -> User | None:
    session = get_current_session(request, db)
    if session is None:
        return None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    _touch_session(db, session)
    return user


def require_user_web(request: Request, db: Session = Depends(get_session)) -> User:
    user = get_current_user_optional(request, db)
    if user is None:
        raise NotAuthenticated(next_path=request.url.path)
    return user


def require_user_api(request: Request, db: Session = Depends(get_session)) -> User:
    from fastapi import HTTPException

    user = get_current_user_optional(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return user
