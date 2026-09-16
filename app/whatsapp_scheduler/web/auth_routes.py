"""UI web de autenticação: login, cadastro, logout, recuperação de senha e
verificação de e-mail. Sem rail (usuário ainda não está autenticado) — ver
`auth_base.html`.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from .. import auth, auth_service
from ..db import get_session
from ..ratelimit import RateLimitExceeded, check_rate_limit, record_attempt
from ..service import ValidationError

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _safe_next(next_path: str | None) -> str:
    """Só aceita caminho relativo interno — nunca um redirect pra fora do app."""
    if not next_path or not next_path.startswith("/") or next_path.startswith("//"):
        return "/"
    return next_path


# --------------------------------------------------------------------------- #
# Login / logout
# --------------------------------------------------------------------------- #
@router.get("/login", response_class=HTMLResponse)
def page_login(
    request: Request,
    next: str | None = Query(None),
    error: str | None = Query(None),
    ok: str | None = Query(None),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    if auth.get_current_user_optional(request, db) is not None:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "next": _safe_next(next), "error": error, "ok": ok, "email_value": ""},
    )


@router.post("/login", response_class=HTMLResponse)
def do_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    ip = auth.client_ip(request) or "unknown"
    rl_key = f"login:{ip}:{email.strip().lower()}"
    try:
        check_rate_limit(rl_key)
    except RateLimitExceeded as exc:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "next": _safe_next(next),
                "email_value": email,
                "error": f"Muitas tentativas. Tente de novo em {exc.retry_after_seconds}s.",
            },
            status_code=429,
        )

    record_attempt(rl_key)
    try:
        user = auth_service.authenticate_user(db, email=email, password=password, request=request)
    except auth_service.AuthenticationError as exc:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "next": _safe_next(next), "email_value": email, "error": str(exc)},
            status_code=401,
        )

    session, raw_token = auth.create_user_session(db, user, request)
    resp = RedirectResponse(url=_safe_next(next), status_code=303)
    auth.set_session_cookie(resp, raw_token)
    return resp


@router.post("/logout")
def do_logout(request: Request, db: Session = Depends(get_session)) -> RedirectResponse:
    session = auth.get_current_session(request, db)
    if session is not None:
        auth_service.log_event(db, auth_service.AuditEventType.logout, user_id=session.user_id, request=request)
        auth.revoke_session(db, session)
    resp = RedirectResponse(url="/login", status_code=303)
    auth.clear_session_cookie(resp)
    return resp


# --------------------------------------------------------------------------- #
# Cadastro
# --------------------------------------------------------------------------- #
@router.get("/cadastro", response_class=HTMLResponse)
def page_cadastro(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "cadastro.html", {"request": request, "error": None, "name_value": "", "email_value": ""}
    )


@router.post("/cadastro", response_class=HTMLResponse)
def do_cadastro(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    ip = auth.client_ip(request) or "unknown"
    rl_key = f"cadastro:{ip}"
    try:
        check_rate_limit(rl_key)
    except RateLimitExceeded as exc:
        return templates.TemplateResponse(
            "cadastro.html",
            {
                "request": request, "name_value": name, "email_value": email,
                "error": f"Muitas tentativas. Tente de novo em {exc.retry_after_seconds}s.",
            },
            status_code=429,
        )
    record_attempt(rl_key)

    try:
        user = auth_service.register_user(
            db, name=name, email=email, password=password, password_confirm=password_confirm, request=request
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            "cadastro.html",
            {"request": request, "name_value": name, "email_value": email, "error": str(exc)},
            status_code=422,
        )

    session, raw_token = auth.create_user_session(db, user, request)
    resp = RedirectResponse(url="/", status_code=303)
    auth.set_session_cookie(resp, raw_token)
    return resp


# --------------------------------------------------------------------------- #
# Recuperação de senha
# --------------------------------------------------------------------------- #
_NEUTRAL_RESET_MESSAGE = "Se existir uma conta associada a este e-mail, enviaremos as instruções de redefinição."


@router.get("/esqueci-senha", response_class=HTMLResponse)
def page_esqueci_senha(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("esqueci_senha.html", {"request": request, "ok": None, "error": None})


@router.post("/esqueci-senha", response_class=HTMLResponse)
def do_esqueci_senha(request: Request, email: str = Form(...), db: Session = Depends(get_session)) -> HTMLResponse:
    ip = auth.client_ip(request) or "unknown"
    rl_key = f"forgot:{ip}:{email.strip().lower()}"
    try:
        check_rate_limit(rl_key)
    except RateLimitExceeded as exc:
        return templates.TemplateResponse(
            "esqueci_senha.html",
            {"request": request, "ok": None, "error": f"Muitas tentativas. Tente de novo em {exc.retry_after_seconds}s."},
            status_code=429,
        )
    record_attempt(rl_key)

    auth_service.request_password_reset(db, email=email, request=request)
    # Mensagem sempre a mesma, exista ou não a conta (Parte 39).
    return templates.TemplateResponse("esqueci_senha.html", {"request": request, "ok": _NEUTRAL_RESET_MESSAGE, "error": None})


@router.get("/redefinir-senha/{token}", response_class=HTMLResponse)
def page_redefinir_senha(request: Request, token: str) -> HTMLResponse:
    return templates.TemplateResponse("redefinir_senha.html", {"request": request, "token": token, "error": None})


@router.post("/redefinir-senha/{token}", response_class=HTMLResponse)
def do_redefinir_senha(
    request: Request,
    token: str,
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    db: Session = Depends(get_session),
) -> HTMLResponse:
    try:
        auth_service.reset_password(
            db, token=token, new_password=new_password, new_password_confirm=new_password_confirm, request=request
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            "redefinir_senha.html", {"request": request, "token": token, "error": str(exc)}, status_code=422
        )
    return RedirectResponse(url="/login?ok=" + quote("Senha redefinida. Entre com a nova senha."), status_code=303)


# --------------------------------------------------------------------------- #
# Verificação de e-mail
# --------------------------------------------------------------------------- #
@router.get("/verificar-email/{token}")
def verificar_email(token: str, db: Session = Depends(get_session)) -> RedirectResponse:
    try:
        auth_service.verify_email(db, token=token)
    except ValidationError as exc:
        return RedirectResponse(url="/login?error=" + quote(str(exc)), status_code=303)
    return RedirectResponse(url="/login?ok=" + quote("E-mail verificado. Entre na sua conta."), status_code=303)


@router.post("/verificar-email/reenviar")
def reenviar_verificacao(
    request: Request, current_user=Depends(auth.require_user_web), db: Session = Depends(get_session)
) -> RedirectResponse:
    auth_service.resend_email_verification(db, current_user)
    return RedirectResponse(
        url="/configuracoes?ok=" + quote("Link de verificação reenviado (veja o log do servidor)."), status_code=303
    )
