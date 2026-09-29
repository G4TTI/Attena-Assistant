"""Controle de acesso do /admin — tudo no servidor.

- Papel lido do BANCO a cada requisição (`User.role == "admin"`); nada de
  cookie/header/query/localStorage decide isso. Sem papel = 404 (a área nem
  "existe" para quem não é admin).
- Sessão de admin tem idade máxima (`ADMIN_SESSION_MAX_AGE_HOURS`): passou
  disso, precisa entrar de novo (reautenticação — ponto onde o MFA entrará).
- Rate limit por admin.
- POSTs exigem token CSRF ligado à sessão (HMAC), além do SameSite=Lax do
  cookie e da checagem de Origin global (main.py).
- O papel admin só é concedido pelo CLI no servidor (`cli grant-admin`).
"""

from __future__ import annotations

import hmac
import json
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from .. import auth, privacy
from ..clock import utcnow
from ..config import settings
from ..db import get_session
from ..models import AdminAuditLog, User, UserSession
from ..ratelimit import RateLimitExceeded, check_rate_limit, record_attempt


class AdminReauthRequired(Exception):
    """Sessão de admin antiga demais — main.py converte em logout + tela de login."""

    def __init__(self, next_path: str = "/admin") -> None:
        self.next_path = next_path


def _next_path(request: Request) -> str:
    return request.url.path + (f"?{request.url.query}" if request.url.query else "")


def _check(request: Request, db: Session) -> tuple[User, UserSession]:
    session = auth.get_current_session(request, db)
    user = auth.get_current_user_optional(request, db) if session is not None else None
    if session is None or user is None:
        raise auth.NotAuthenticated(next_path=_next_path(request))
    if user.role != "admin" or not user.is_active:
        raise HTTPException(status_code=404, detail="Not Found")
    if session.created_at < utcnow() - timedelta(hours=settings.admin_session_max_age_hours):
        from ..auth_service import AuditEventType, log_event

        log_event(db, AuditEventType.admin_reauth_required, user_id=user.id, request=request)
        auth.revoke_session(db, session)
        raise AdminReauthRequired(next_path=_next_path(request))
    key = f"admin:{user.id}"
    try:
        check_rate_limit(key, max_attempts=settings.admin_rate_limit_requests, window_seconds=settings.admin_rate_limit_window_seconds)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=f"Muitas requisições. Tente de novo em {exc.retry_after_seconds}s.") from exc
    record_attempt(key)
    request.state.admin_session_token_hash = session.token_hash
    return user, session


def require_admin(request: Request, db: Session = Depends(get_session)) -> User:
    user, _session = _check(request, db)
    return user


# --------------------------------------------------------------------------- #
# CSRF: token = HMAC(chave de hash, hash do token da sessão). Muda a cada login,
# não precisa ser guardado e não revela nada da sessão.
# --------------------------------------------------------------------------- #
def csrf_token(request: Request) -> str:
    token_hash = getattr(request.state, "admin_session_token_hash", "")
    return privacy.blind_index("admin-csrf", token_hash)


async def verify_csrf(request: Request) -> None:
    form = await request.form()
    sent = str(form.get("csrf_token") or "")
    if not sent or not hmac.compare_digest(sent, csrf_token(request)):
        raise HTTPException(status_code=403, detail="Token de segurança inválido. Recarregue a página e tente de novo.")


# --------------------------------------------------------------------------- #
# Auditoria
# --------------------------------------------------------------------------- #
def audit(
    db: Session,
    admin: User,
    action: str,
    *,
    target_type: str,
    target_id: str | None,
    detail: dict | None = None,
) -> None:
    """Registra uma ação administrativa. `detail` deve ser curto e NÃO sensível
    (nunca texto de nota, CPF, conteúdo...). Faz commit."""
    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=json.dumps(detail, ensure_ascii=False)[:500] if detail else None,
        )
    )
    db.commit()
