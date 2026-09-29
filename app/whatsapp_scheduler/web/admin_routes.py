"""Área administrativa (/admin). Toda rota passa por `admin.security.require_admin`
(papel lido do banco, sessão recente, rate limit) e todo POST exige token CSRF.

O que NÃO existe aqui, de propósito: nenhuma rota que leia conversas, mensagens,
histórico, mídia ou conteúdo de mensagem programada — nem para admin. As telas
mostram só metadados (contagens, datas, status, códigos de erro sanitizados).
"""

from __future__ import annotations

import asyncio
import math
import re
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, col, select

from .. import app_settings, auth, failures, plans
from ..admin import crm
from ..admin import service as admin_service
from ..admin.security import audit, csrf_token, require_admin, verify_csrf
from ..billing import service as billing
from ..billing.validation import UF_NAMES
from ..clock import utcnow
from ..db import get_session
from ..errors import ValidationError
from ..models import BillingPeriod, Plan, User, WhatsAppSession
from ..waha import WahaError
from .routes import templates

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

templates.env.globals["crm_statuses"] = crm.CRM_STATUSES
templates.env.globals["failure_labels"] = failures.LABELS


def _ctx(request: Request, admin: User, section: str, **extra) -> dict:
    return {
        "request": request,
        "current_user": admin,
        "section": section,
        "csrf_token": csrf_token(request),
        "admin_tz": app_settings.user_timezone(admin),
        "now": utcnow(),
        **extra,
    }


def _pages(total: int) -> int:
    return max(1, math.ceil(total / admin_service.PER_PAGE))


def _back(url: str, *, ok: str | None = None, error: str | None = None) -> RedirectResponse:
    params = {"ok": ok} if ok else {"error": error} if error else {}
    sep = "&" if "?" in url else "?"
    return RedirectResponse(url=url + (sep + urlencode(params) if params else ""), status_code=303)


def _target_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return user


# --------------------------------------------------------------------------- #
# Visão geral
# --------------------------------------------------------------------------- #
@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> HTMLResponse:
    metrics = await asyncio.to_thread(admin_service.dashboard, db)
    live = await admin_service.live_whatsapp_status(request.app.state.waha, admin_service.active_session_names(db))
    return templates.TemplateResponse(
        "admin/dashboard.html", _ctx(request, admin, "dashboard", m=metrics, live=live, page_title="Visão geral")
    )


# --------------------------------------------------------------------------- #
# Usuários
# --------------------------------------------------------------------------- #
@router.get("/usuarios", response_class=HTMLResponse)
def admin_users(
    request: Request,
    q: str = Query(""),
    plan: str = Query(""),
    status: str = Query(""),
    signup: str = Query(""),
    activity: str = Query(""),
    subscription: str = Query(""),
    crm_status: str = Query("", alias="crm"),
    tag: str = Query(""),
    sort: str = Query("created"),
    direction: str = Query("desc", alias="dir"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    filters = admin_service.UserFilters(
        q=q[:100], plan=plan, status=status, signup=signup, activity=activity, subscription=subscription,
        crm=crm_status, tag=tag, sort=sort if sort in (*admin_service.SORTS, "pending") else "created",
        direction="asc" if direction == "asc" else "desc", page=page,
    )
    rows, total = admin_service.list_users(db, filters)
    return templates.TemplateResponse(
        "admin/usuarios.html",
        _ctx(
            request, admin, "usuarios", page_title="Usuários", rows=rows, total=total, pages=_pages(total),
            filters=filters, plans_list=plans.list_plans(db), tags=crm.list_tags(db),
        ),
    )


@router.get("/usuarios/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(
    request: Request,
    user_id: str,
    ok: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    detail = admin_service.user_detail(db, user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    # Status ao vivo de cada WhatsApp do cliente: SÓ o status (nunca número/nome do perfil).
    names = dict(
        db.exec(
            select(WhatsAppSession.id, WhatsAppSession.session_name)
            .where(col(WhatsAppSession.user_id) == user_id)
            .where(col(WhatsAppSession.disconnected_at).is_(None))
        ).all()
    )

    async def _status(session_name: str) -> str:
        try:
            info = await request.app.state.waha.get_session_status(session_name)
            return str(info.get("status") or "desconhecido").upper()
        except WahaError:
            return "INDISPONÍVEL"

    statuses = await asyncio.gather(*(_status(name) for name in names.values()))
    live = dict(zip(names.keys(), statuses))
    return templates.TemplateResponse(
        "admin/usuario.html",
        _ctx(
            request, admin, "usuarios", page_title=detail.name, u=detail, live=live,
            connected=sum(1 for s in statuses if s == "WORKING"), ok=ok, error=error,
            plans_list=plans.list_plans(db), all_tags=crm.list_tags(db), uf_names=UF_NAMES,
        ),
    )


@router.post("/usuarios/{user_id}/crm/status")
async def admin_set_crm_status(
    request: Request, user_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    _target_user(db, user_id)
    status = str((await request.form()).get("status") or "")
    back = f"/admin/usuarios/{user_id}"
    try:
        previous, new = crm.set_status(db, user_id, status, admin)
    except ValidationError as exc:
        return _back(back, error=str(exc))
    audit(db, admin, "crm_status_changed", target_type="user", target_id=user_id, detail={"from": previous, "to": new})
    return _back(back, ok="Status do CRM atualizado.")


@router.post("/usuarios/{user_id}/crm/tags")
async def admin_add_tag(
    request: Request, user_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    _target_user(db, user_id)
    form = await request.form()
    back = f"/admin/usuarios/{user_id}"
    tag_id = str(form.get("tag_id") or "")
    new_name = str(form.get("new_tag") or "")
    try:
        if new_name.strip():
            tag, created = crm.get_or_create_tag(db, new_name, admin)
            if created:
                audit(db, admin, "crm_tag_created", target_type="tag", target_id=tag.id, detail={"name": tag.name})
        else:
            tag = next((t for t in crm.list_tags(db) if t.id == tag_id), None)
            if tag is None:
                raise ValidationError("Escolha uma tag.")
    except ValidationError as exc:
        return _back(back, error=str(exc))
    if crm.add_tag(db, user_id, tag, admin):
        audit(db, admin, "crm_tag_added", target_type="user", target_id=user_id, detail={"tag": tag.name})
    return _back(back, ok=f"Tag “{tag.name}” aplicada.")


@router.post("/usuarios/{user_id}/crm/tags/{tag_id}/remover")
async def admin_remove_tag(
    request: Request, user_id: str, tag_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    tag = crm.remove_tag(db, user_id, tag_id)
    if tag is not None:
        audit(db, admin, "crm_tag_removed", target_type="user", target_id=user_id, detail={"tag": tag.name})
    return _back(f"/admin/usuarios/{user_id}", ok="Tag removida.")


@router.post("/usuarios/{user_id}/crm/notas")
async def admin_add_note(
    request: Request, user_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    _target_user(db, user_id)
    body = str((await request.form()).get("body") or "")
    back = f"/admin/usuarios/{user_id}"
    try:
        note = crm.add_note(db, user_id, body, admin)
    except ValidationError as exc:
        return _back(back, error=str(exc))
    # Só o id da nota na auditoria — nunca o texto.
    audit(db, admin, "crm_note_added", target_type="user", target_id=user_id, detail={"note_id": note.id})
    return _back(back, ok="Nota adicionada.")


@router.post("/usuarios/{user_id}/crm/notas/{note_id}")
async def admin_update_note(
    request: Request, user_id: str, note_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    body = str((await request.form()).get("body") or "")
    back = f"/admin/usuarios/{user_id}"
    try:
        note = crm.update_note(db, user_id, note_id, body, admin)
    except ValidationError as exc:
        return _back(back, error=str(exc))
    if note is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    audit(db, admin, "crm_note_updated", target_type="user", target_id=user_id, detail={"note_id": note_id})
    return _back(back, ok="Nota atualizada.")


@router.post("/usuarios/{user_id}/crm/notas/{note_id}/excluir")
async def admin_delete_note(
    request: Request, user_id: str, note_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    if crm.delete_note(db, user_id, note_id):
        audit(db, admin, "crm_note_deleted", target_type="user", target_id=user_id, detail={"note_id": note_id})
    return _back(f"/admin/usuarios/{user_id}", ok="Nota excluída.")


@router.post("/usuarios/{user_id}/suspender")
async def admin_suspend(
    request: Request, user_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    user = _target_user(db, user_id)
    back = f"/admin/usuarios/{user_id}"
    if user.id == admin.id:
        return _back(back, error="Você não pode suspender a própria conta.")
    if user.is_active:
        user.is_active = False
        user.updated_at = utcnow()
        db.add(user)
        db.commit()
        revoked = auth.revoke_all_sessions(db, user)
        audit(db, admin, "user_suspended", target_type="user", target_id=user_id, detail={"sessions_revoked": revoked})
    return _back(back, ok="Conta suspensa: o acesso foi encerrado e as mensagens programadas não serão enviadas.")


@router.post("/usuarios/{user_id}/reativar")
async def admin_reactivate(
    request: Request, user_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    user = _target_user(db, user_id)
    if not user.is_active:
        user.is_active = True
        user.updated_at = utcnow()
        db.add(user)
        db.commit()
        audit(db, admin, "user_reactivated", target_type="user", target_id=user_id)
    return _back(f"/admin/usuarios/{user_id}", ok="Conta reativada.")


@router.post("/usuarios/{user_id}/plano")
async def admin_change_plan(
    request: Request, user_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    user = _target_user(db, user_id)
    plan = db.get(Plan, str((await request.form()).get("plan_id") or ""))
    back = f"/admin/usuarios/{user_id}"
    if plan is None:
        return _back(back, error="Escolha um plano.")
    previous = plans.current_plan(db, user)
    billing.grant_plan_manually(db, user, plan)
    audit(
        db, admin, "plan_changed_manually", target_type="user", target_id=user_id,
        detail={"from": previous.code if previous else None, "to": plan.code},
    )
    return _back(back, ok=f"Plano alterado para {plan.name} (cortesia — não conta como faturamento).")


# --------------------------------------------------------------------------- #
# CRM: tags
# --------------------------------------------------------------------------- #
@router.get("/crm", response_class=HTMLResponse)
def admin_crm(
    request: Request,
    ok: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    from sqlalchemy import func

    from ..models import CrmProfile, CrmUserTag

    total_users = db.exec(select(func.count()).select_from(User)).one()
    by_status = dict(db.exec(select(CrmProfile.status, func.count()).group_by(col(CrmProfile.status))).all())
    by_status["lead"] = by_status.get("lead", 0) + max(0, total_users - sum(by_status.values()))
    tag_counts = dict(db.exec(select(CrmUserTag.tag_id, func.count()).group_by(col(CrmUserTag.tag_id))).all())
    return templates.TemplateResponse(
        "admin/crm.html",
        _ctx(
            request, admin, "crm", page_title="CRM", by_status=by_status, tags=crm.list_tags(db), tag_counts=tag_counts,
            ok=ok, error=error,
        ),
    )


@router.post("/crm/tags")
async def admin_create_tag(request: Request, db: Session = Depends(get_session), admin: User = Depends(require_admin)) -> RedirectResponse:
    await verify_csrf(request)
    try:
        tag, created = crm.get_or_create_tag(db, str((await request.form()).get("name") or ""), admin)
    except ValidationError as exc:
        return _back("/admin/crm", error=str(exc))
    if created:
        audit(db, admin, "crm_tag_created", target_type="tag", target_id=tag.id, detail={"name": tag.name})
    return _back("/admin/crm", ok=f"Tag “{tag.name}” disponível.")


@router.post("/crm/tags/{tag_id}/excluir")
async def admin_delete_tag(
    request: Request, tag_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    tag = crm.delete_tag(db, tag_id)
    if tag is not None:
        audit(db, admin, "crm_tag_deleted", target_type="tag", target_id=tag_id, detail={"name": tag.name})
    return _back("/admin/crm", ok="Tag excluída.")


# --------------------------------------------------------------------------- #
# Planos
# --------------------------------------------------------------------------- #
@router.get("/planos", response_class=HTMLResponse)
def admin_plans(
    request: Request,
    ok: str | None = Query(None),
    error: str | None = Query(None),
    edit: str | None = Query(None),
    db: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    rows = admin_service.plan_rows(db)
    editing = next((r for r in rows if r["plan"].id == edit), None) if edit else None
    return templates.TemplateResponse(
        "admin/planos.html",
        _ctx(
            request, admin, "planos", page_title="Planos", rows=rows, editing=editing, ok=ok, error=error,
            limit_labels=plans.LIMIT_LABELS, periods={p.value: plans.PERIOD_LABELS[p] for p in BillingPeriod},
        ),
    )


_PRICE = re.compile(r"^\d{1,6}([.,]\d{1,2})?$")


@router.post("/planos/{plan_id}")
async def admin_update_plan(
    request: Request, plan_id: str, db: Session = Depends(get_session), admin: User = Depends(require_admin)
) -> RedirectResponse:
    await verify_csrf(request)
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")
    form = await request.form()
    back = f"/admin/planos?edit={plan_id}"
    name = " ".join(str(form.get("name") or "").split())[:60]
    price_raw = str(form.get("price") or "0").strip().replace("R$", "").replace(" ", "")
    if not name:
        return _back(back, error="Informe o nome do plano.")
    if not _PRICE.match(price_raw):
        return _back(back, error="Preço inválido. Use por exemplo 29,90.")
    period = str(form.get("billing_period") or "monthly")
    if period not in {p.value for p in BillingPeriod}:
        return _back(back, error="Período inválido.")
    limits: dict[str, int | None] = {}
    for key in plans.LIMIT_LABELS:
        raw = str(form.get(f"limit_{key}") or "").strip()
        if raw == "":
            limits[key] = None
        elif raw.isdigit():
            limits[key] = int(raw)
        else:
            return _back(back, error=f"Limite inválido em “{plans.LIMIT_LABELS[key]}”: use um número ou deixe vazio (ilimitado).")
    features = [line.strip()[:120] for line in str(form.get("features") or "").splitlines() if line.strip()][:20]
    import json

    before = {"price_cents": plan.price_cents, "is_active": plan.is_active, "is_public": plan.is_public}
    plan.name = name
    plan.description = str(form.get("description") or "").strip()[:200]
    plan.price_cents = round(float(price_raw.replace(",", ".")) * 100)
    plan.billing_period = BillingPeriod(period)
    plan.features_json = json.dumps(features, ensure_ascii=False)
    plan.limits_json = json.dumps(limits)
    plan.is_active = form.get("is_active") == "on"
    plan.is_public = form.get("is_public") == "on"
    plans.touch(plan)
    db.add(plan)
    db.commit()
    audit(
        db, admin, "plan_updated", target_type="plan", target_id=plan.id,
        detail={"code": plan.code, "before": before, "after": {"price_cents": plan.price_cents, "is_active": plan.is_active, "is_public": plan.is_public}},
    )
    return _back("/admin/planos", ok=f"Plano {plan.name} atualizado.")


# --------------------------------------------------------------------------- #
# Faturamento
# --------------------------------------------------------------------------- #
@router.get("/faturamento", response_class=HTMLResponse)
def admin_finance(request: Request, db: Session = Depends(get_session), admin: User = Depends(require_admin)) -> HTMLResponse:
    from ..billing import metrics as billing_metrics

    summary = billing_metrics.summary(db)
    series = billing_metrics.monthly_revenue(db)
    peak = max((m["cents"] for m in series), default=0)
    return templates.TemplateResponse(
        "admin/faturamento.html",
        _ctx(
            request, admin, "faturamento", page_title="Faturamento", f=summary, series=series, peak=peak,
            payments=admin_service.recent_payments(db), subscriptions=admin_service.recent_subscriptions(db),
        ),
    )


# --------------------------------------------------------------------------- #
# Agendamentos (saúde operacional — só metadados)
# --------------------------------------------------------------------------- #
@router.get("/agendamentos", response_class=HTMLResponse)
def admin_schedules(
    request: Request,
    status: str = Query(""),
    q: str = Query(""),
    date_from: str = Query("", alias="de"),
    date_to: str = Query("", alias="ate"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    filters = admin_service.DispatchFilters(status=status, q=q[:100], date_from=date_from[:10], date_to=date_to[:10], page=page)
    rows, total = admin_service.list_dispatches(db, filters)
    return templates.TemplateResponse(
        "admin/agendamentos.html",
        _ctx(
            request, admin, "agendamentos", page_title="Agendamentos", rows=rows, total=total, pages=_pages(total),
            filters=filters, summary=admin_service.dispatch_summary(db),
        ),
    )


# --------------------------------------------------------------------------- #
# Logins e auditoria
# --------------------------------------------------------------------------- #
@router.get("/logins", response_class=HTMLResponse)
def admin_logins(
    request: Request,
    result: str = Query(""),
    q: str = Query(""),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    filters = admin_service.LoginFilters(result=result, q=q[:100], page=page)
    rows, total = admin_service.login_events(db, filters)
    return templates.TemplateResponse(
        "admin/logins.html",
        _ctx(request, admin, "logins", page_title="Logins", rows=rows, total=total, pages=_pages(total), filters=filters),
    )


@router.get("/auditoria", response_class=HTMLResponse)
def admin_audit(
    request: Request,
    action: str = Query(""),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    filters = admin_service.AuditFilters(action=action, page=page)
    rows, total = admin_service.audit_entries(db, filters)
    return templates.TemplateResponse(
        "admin/auditoria.html",
        _ctx(
            request, admin, "auditoria", page_title="Auditoria", rows=rows, total=total, pages=_pages(total),
            filters=filters, actions=admin_service.ACTION_LABELS,
        ),
    )


def _qs(params: dict) -> str:
    return urlencode({k: v for k, v in params.items() if v not in ("", None)})


templates.env.filters["qs"] = _qs
templates.env.globals["quote"] = quote
