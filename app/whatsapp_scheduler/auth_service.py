"""Regra de negócio de autenticação: cadastro, login, recuperação de senha,
verificação de e-mail e auditoria. Equivalente a `calendar_service.py`, mas
para contas — usa as primitivas de `auth.py` (hash, token, sessão) sem
reimplementá-las.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import Request
from sqlmodel import Session, col, select

from . import auth
from .clock import utcnow
from .config import settings
from .db import claim_orphan_data
from .models import AuditEventType, BillingProfile, EmailVerificationToken, LoginAuditEvent, PasswordResetToken, User
from .service import ValidationError

logger = logging.getLogger("whatsapp_scheduler.auth")

_MIN_PASSWORD_LENGTH = 8


class AuthenticationError(ValueError):
    """Login inválido — mensagem sempre genérica (nunca diz se o e-mail
    existe ou não: Parte 39, proteção contra enumeração de usuários)."""


def log_event(
    db: Session,
    event_type: AuditEventType,
    *,
    user_id: str | None = None,
    request: Request | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        LoginAuditEvent(
            user_id=user_id,
            event_type=event_type,
            detail=detail,
            ip_address=auth.client_ip(request) if request else None,
            user_agent=auth.client_user_agent(request) if request else None,
        )
    )
    db.commit()


def _validate_password(password: str) -> None:
    if not password or len(password) < _MIN_PASSWORD_LENGTH:
        raise ValidationError(f"A senha precisa ter ao menos {_MIN_PASSWORD_LENGTH} caracteres.")


def _find_by_email(db: Session, email: str) -> User | None:
    return db.exec(select(User).where(col(User.email) == email)).first()


def register_user(
    db: Session, *, name: str, email: str, password: str, password_confirm: str, request: Request | None = None
) -> User:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Informe seu nome.")
    email_norm = auth.normalize_email(email)
    if not email_norm or "@" not in email_norm or "." not in email_norm.split("@")[-1]:
        raise ValidationError("E-mail inválido.")
    if password != password_confirm:
        raise ValidationError("As senhas não coincidem.")
    _validate_password(password)

    if _find_by_email(db, email_norm) is not None:
        # Diferente do "esqueci minha senha": aqui é normal e esperado dizer
        # que o e-mail já está em uso (senão o cadastro fica inutilizável).
        raise ValidationError("Já existe uma conta com este e-mail.")

    user = User(name=name, email=email_norm, password_hash=auth.hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(BillingProfile(user_id=user.id))
    db.commit()

    if claim_orphan_data(db, user):
        logger.info("dados anteriores à autenticação foram associados ao primeiro usuário cadastrado (%s)", user.email)

    request_email_verification(db, user)
    log_event(db, AuditEventType.register, user_id=user.id, request=request)
    return user


def authenticate_user(db: Session, *, email: str, password: str, request: Request | None = None) -> User:
    email_norm = auth.normalize_email(email)
    user = _find_by_email(db, email_norm)
    if user is None or not user.is_active or not auth.verify_password(password, user.password_hash):
        log_event(
            db, AuditEventType.login_failed, user_id=user.id if user else None, request=request, detail=email_norm
        )
        raise AuthenticationError("E-mail ou senha inválidos.")
    log_event(db, AuditEventType.login_success, user_id=user.id, request=request)
    return user


def change_password(db: Session, user: User, *, current_password: str, new_password: str, new_password_confirm: str) -> None:
    if not auth.verify_password(current_password, user.password_hash):
        raise ValidationError("Senha atual incorreta.")
    if new_password != new_password_confirm:
        raise ValidationError("As senhas novas não coincidem.")
    _validate_password(new_password)

    user.password_hash = auth.hash_password(new_password)
    user.updated_at = utcnow()
    db.add(user)
    db.commit()
    log_event(db, AuditEventType.password_changed, user_id=user.id)


# --------------------------------------------------------------------------- #
# Recuperação de senha
# --------------------------------------------------------------------------- #
def request_password_reset(db: Session, *, email: str, request: Request | None = None) -> None:
    """Sempre "silencioso" pro chamador: nunca revela se o e-mail existe. Sem
    provedor de e-mail configurado ainda, o link é registrado em log de
    servidor (nunca na resposta HTTP) — Parte 20: não fingir envio."""
    email_norm = auth.normalize_email(email)
    user = _find_by_email(db, email_norm)
    if user is None:
        return

    raw_token = auth.generate_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=auth.hash_token(raw_token),
            expires_at=utcnow() + timedelta(minutes=settings.password_reset_ttl_minutes),
        )
    )
    db.commit()
    logger.warning(
        "[sem provedor de e-mail configurado] link de redefinição de senha para %s: "
        "/redefinir-senha/%s (expira em %d min)",
        user.email,
        raw_token,
        settings.password_reset_ttl_minutes,
    )
    log_event(db, AuditEventType.password_reset_requested, user_id=user.id, request=request)


def reset_password(
    db: Session, *, token: str, new_password: str, new_password_confirm: str, request: Request | None = None
) -> User:
    if new_password != new_password_confirm:
        raise ValidationError("As senhas não coincidem.")
    _validate_password(new_password)

    token_hash = auth.hash_token(token)
    row = db.exec(select(PasswordResetToken).where(col(PasswordResetToken.token_hash) == token_hash)).first()
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise ValidationError("Link de redefinição inválido ou expirado. Solicite um novo.")

    user = db.get(User, row.user_id)
    if user is None:
        raise ValidationError("Link de redefinição inválido ou expirado. Solicite um novo.")

    user.password_hash = auth.hash_password(new_password)
    user.updated_at = utcnow()
    db.add(user)
    row.used_at = utcnow()
    db.add(row)
    db.commit()

    # Uma senha só é redefinida por quem não conseguia entrar — nenhuma sessão
    # antiga (possivelmente da conta comprometida) deveria sobreviver a isso.
    auth.revoke_all_sessions(db, user)
    log_event(db, AuditEventType.password_reset_completed, user_id=user.id, request=request)
    return user


# --------------------------------------------------------------------------- #
# Verificação de e-mail
# --------------------------------------------------------------------------- #
def request_email_verification(db: Session, user: User) -> None:
    raw_token = auth.generate_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=auth.hash_token(raw_token),
            expires_at=utcnow() + timedelta(hours=settings.email_verification_ttl_hours),
        )
    )
    db.commit()
    logger.warning(
        "[sem provedor de e-mail configurado] link de verificação de e-mail para %s: "
        "/verificar-email/%s (expira em %d h)",
        user.email,
        raw_token,
        settings.email_verification_ttl_hours,
    )


def resend_email_verification(db: Session, user: User) -> None:
    if user.email_verified:
        return
    request_email_verification(db, user)


def verify_email(db: Session, *, token: str) -> User:
    token_hash = auth.hash_token(token)
    row = db.exec(select(EmailVerificationToken).where(col(EmailVerificationToken.token_hash) == token_hash)).first()
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise ValidationError("Link de verificação inválido ou expirado.")
    user = db.get(User, row.user_id)
    if user is None:
        raise ValidationError("Link de verificação inválido ou expirado.")

    user.email_verified = True
    user.updated_at = utcnow()
    db.add(user)
    row.used_at = utcnow()
    db.add(row)
    db.commit()
    return user
