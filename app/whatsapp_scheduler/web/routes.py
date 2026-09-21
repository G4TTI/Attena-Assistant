"""UI web (Jinja2 + htmx, sem build step)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from .. import app_settings, auth, schedule_views, timing, whatsapp_service
from ..chatsvc import cached_chat_name, get_history, list_chats, send_now
from ..clock import utcnow
from ..db import get_session
from ..errors import ValidationError
from ..models import ScheduleSource, User
from ..recipients import RecipientError, normalize_recipient
from ..recurrence import utc_to_local
from ..service import cancel_group, cancel_schedule, create_sequence, run_group_now, update_sequence
from ..waha import WahaError

# Teto de destinatários por envio do formulário (cada um vira um agendamento).
MAX_RECIPIENTS_PER_REQUEST = 50

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _localtime(dt: datetime | None, tz: str) -> str:
    if not isinstance(dt, datetime):
        return "—"
    return utc_to_local(dt, tz).strftime("%d/%m/%Y %H:%M")


templates.env.filters["localtime"] = _localtime
templates.env.globals["tz_label"] = timing.tz_label
templates.env.filters["wa_sig"] = whatsapp_service.status_signature


_STATUS_LABELS = {
    "pending": "pendente",
    "processing": "processando",
    "sent": "enviado",
    "failed": "falhou",
    "canceled": "cancelado",
    "skipped": "ignorado",
}


def _status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


templates.env.filters["status_label"] = _status_label


def _engine_label(session: dict | None) -> str:
    if not isinstance(session, dict):
        return "—"
    engine = session.get("engine")
    if isinstance(engine, dict):
        return str(engine.get("engine") or engine.get("name") or "—")
    if isinstance(engine, str) and engine:
        return engine
    return "—"


templates.env.filters["engine_label"] = _engine_label


# --------------------------------------------------------------------------- #
# Contextos e entradas compartilhados
# --------------------------------------------------------------------------- #
def _base_ctx(request: Request, nav: str, current_user: User) -> dict:
    return {"request": request, "nav": nav, "current_user": current_user}


def _recipient_key(value: str) -> str:
    """Mesmo critério do JS do ContactPicker (`rcKey`): dígitos do número, senão o
    texto — só pra não repetir na tela; a validação de verdade é `normalize_recipient`."""
    head = value.split("@", 1)[0]
    digits = "".join(ch for ch in head if ch.isdigit())
    return digits or value.lower()


def pair_recipients(values: list[str], names: list[str]) -> list[dict]:
    """`recipients` + `recipient_names` (campos gêmeos do ContactPicker, mesma
    ordem) -> [{value, label}] sem repetir o mesmo destinatário."""
    out: list[dict] = []
    seen: set[str] = set()
    for i, value in enumerate(values):
        value = (value or "").strip()
        if not value:
            continue
        key = _recipient_key(value)
        if key in seen:
            continue
        seen.add(key)
        out.append({"value": value, "label": ((names[i] if i < len(names) else "") or "").strip()})
    return out


def unique_chats(picked: list[dict]) -> list[tuple[str, dict]]:
    """Valida TODOS os destinatários antes de criar qualquer agendamento e junta
    os que resolvem pro mesmo chat (ex.: um contato e o mesmo número digitado)."""
    if len(picked) > MAX_RECIPIENTS_PER_REQUEST:
        raise ValidationError(f"No máximo {MAX_RECIPIENTS_PER_REQUEST} destinatários por vez.")
    unique: dict[str, dict] = {}
    for item in picked:
        try:
            chat_id = normalize_recipient(item["value"])
        except (RecipientError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        unique.setdefault(chat_id, item)
    return list(unique.items())


def _start_from_form(send_date: str, send_time: str, send_at: str) -> datetime:
    """Data + horário digitados (`send_date` + `send_time`), ou o antigo
    `send_at` ISO — sempre o horário de parede do usuário."""
    if send_date or send_time:
        return timing.parse_local_input(send_date, send_time)
    return timing.parse_send_at(send_at)


def _form_start_values(start: datetime | None, tz_name: str) -> tuple[str, str]:
    start = start or timing.suggest_start_local(utcnow(), tz_name)
    return start.strftime("%Y-%m-%d"), start.strftime("%H:%M")


def _schedule_form_ctx(db: Session, current_user: User, **overrides: object) -> dict:
    """Estado do formulário de agendamento (criar ou editar). O horário vem do
    que o usuário já digitou (`overrides`) e só cai numa sugestão quando o
    formulário é realmente novo."""
    tz_name = app_settings.user_timezone(current_user)
    sessions = whatsapp_service.list_sessions(db, current_user.id)
    send_date, send_time = _form_start_values(None, tz_name)
    primary = sessions[0].id if sessions else ""
    form: dict = {
        "mode": "create",
        "action": "/ui/schedules",
        "target": "#schedule-form-wrap",
        "swap": "outerHTML",
        "recipients": [],
        "recipient_label": None,
        "messages": [""],
        "send_date": send_date,
        "send_time": send_time,
        "min_date": utc_to_local(utcnow(), tz_name).strftime("%Y-%m-%d"),
        "whatsapp_session_id": primary,
        "recurrence": "",
        "error": None,
        "ok": None,
        "advanced_open": False,
        "tz_label": timing.tz_label(tz_name),
        "whatsapp_sessions": sessions,
    }
    form.update(overrides)
    return form


def _table_ctx(request: Request, db: Session, user_id: str, tz_name: str, *, oob: bool = False) -> dict:
    return {
        "request": request,
        "groups": schedule_views.list_group_views(db, user_id, tz_name),
        "oob": oob,
        "tz_label": timing.tz_label(tz_name),
    }


# --------------------------------------------------------------------------- #
# Páginas
# --------------------------------------------------------------------------- #
@router.get("/agendamentos", response_class=HTMLResponse)
async def page_schedules(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    tz_name = app_settings.user_timezone(current_user)
    ctx = {
        **_base_ctx(request, "agendamentos", current_user),
        **_table_ctx(request, db, current_user.id, tz_name),
        "form": _schedule_form_ctx(db, current_user),
    }
    return templates.TemplateResponse("schedules.html", ctx)


@router.get("/conversas", response_class=HTMLResponse)
async def page_chats(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    primary = whatsapp_service.primary_session(db, current_user.id)
    if primary is None:
        return templates.TemplateResponse(
            "conversas.html", {**_base_ctx(request, "conversas", current_user), "session_id": None, "whatsapp_sessions": []}
        )
    return RedirectResponse(url=f"/conversas/{primary.id}", status_code=303)


@router.get("/conversas/{session_id}", response_class=HTMLResponse)
async def page_chats_session(
    request: Request,
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    session = whatsapp_service.get_session(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="WhatsApp não encontrado.")
    return templates.TemplateResponse(
        "conversas.html",
        {
            **_base_ctx(request, "conversas", current_user),
            "session_id": session.id,
            "whatsapp_sessions": whatsapp_service.list_sessions(db, current_user.id),
            "default_timezone": app_settings.user_timezone(current_user),
        },
    )


# --------------------------------------------------------------------------- #
# Parciais (htmx)
# --------------------------------------------------------------------------- #
@router.get("/ui/sidebar-status", response_class=HTMLResponse)
async def ui_sidebar_status(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    sessions = whatsapp_service.list_sessions(db, current_user.id)
    overall = await whatsapp_service.overall_status(request.app.state.waha, sessions)
    return templates.TemplateResponse("_sidebar_status.html", {"request": request, "overall": overall})


# ---- Agendamentos ----------------------------------------------------------- #
def _table_response(request: Request, db: Session, current_user: User) -> HTMLResponse:
    """A lista de agendamentos. Quando o pedido veio de um modal (`#modal-root`),
    a resposta é o trecho "fora de banda": o htmx aplica a lista e limpa o modal."""
    oob = request.headers.get("HX-Target") == "modal-root"
    return templates.TemplateResponse(
        "_table.html", _table_ctx(request, db, current_user.id, app_settings.user_timezone(current_user), oob=oob)
    )


@router.get("/ui/schedules", response_class=HTMLResponse)
async def ui_schedules(
    request: Request, db: Session = Depends(get_session), current_user: User = Depends(auth.require_user_web)
) -> HTMLResponse:
    return _table_response(request, db, current_user)


def _form_state_from_input(
    db: Session, current_user: User, *, recipients: list[dict], texts: list[str], send_date: str, send_time: str,
    whatsapp_session_id: str, recurrence: str, **extra: object,
) -> dict:
    return _schedule_form_ctx(
        db, current_user, recipients=recipients, messages=texts or [""], send_date=send_date, send_time=send_time,
        whatsapp_session_id=whatsapp_session_id, recurrence=recurrence, advanced_open=bool(recurrence), **extra,
    )


@router.post("/ui/schedules", response_class=HTMLResponse)
async def ui_create(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
    recipients: list[str] = Form([]),
    recipient_names: list[str] = Form([]),
    recipient: str = Form(""),
    messages: list[str] = Form([]),
    text: str = Form(""),
    send_date: str = Form(""),
    send_time: str = Form(""),
    send_at: str = Form(""),
    whatsapp_session_id: str = Form(""),
    recurrence: str = Form(""),
) -> HTMLResponse:
    tz_name = app_settings.user_timezone(current_user)
    picked = pair_recipients(recipients + ([recipient] if recipient.strip() else []), recipient_names)
    texts = messages if messages else ([text] if text.strip() else [])
    try:
        if not picked:
            raise ValidationError("Selecione ao menos um destinatário.")
        wa_session = whatsapp_service.get_session(db, whatsapp_session_id, current_user.id) if whatsapp_session_id else (
            whatsapp_service.primary_session(db, current_user.id)
        )
        if wa_session is None:
            raise ValidationError("Conecte um WhatsApp antes de criar um agendamento.")
        chats = unique_chats(picked)
        start = _start_from_form(send_date, send_time, send_at)
        await whatsapp_service.require_session_ready(request.app.state.waha, wa_session)

        def _create_all() -> None:
            for _chat_id, item in chats:
                create_sequence(
                    db,
                    user_id=current_user.id,
                    session=wa_session.session_name,
                    recipient=item["value"],
                    recipient_name=item["label"] or None,
                    messages=texts,
                    start=start,
                    timezone=tz_name,
                    source=ScheduleSource.manual,
                    recurrence=recurrence or None,
                    allow_past=False,
                    dedupe=True,
                )

        await asyncio.to_thread(_create_all)
    except ValidationError as exc:
        form = _form_state_from_input(
            db, current_user, recipients=picked, texts=texts, send_date=send_date, send_time=send_time,
            whatsapp_session_id=whatsapp_session_id, recurrence=recurrence, error=str(exc),
        )
        return templates.TemplateResponse("_schedule_form.html", {"request": request, "form": form})

    # Sucesso: formulário novo, mas o horário/WhatsApp escolhidos continuam (dá pra agendar
    # a próxima mensagem sem digitar tudo de novo); a lista é atualizada na mesma resposta.
    count = len(chats)
    form = _schedule_form_ctx(
        db, current_user, send_date=start.strftime("%Y-%m-%d"), send_time=start.strftime("%H:%M"),
        whatsapp_session_id=wa_session.id,
        ok="Agendamento criado." if count == 1 else f"{count} agendamentos criados (um por destinatário).",
    )
    return templates.TemplateResponse(
        "_schedule_form_response.html",
        {"request": request, "form": form, **_table_ctx(request, db, current_user.id, tz_name, oob=True)},
    )


def _owned_group_view(db: Session, group_id: str, current_user: User) -> schedule_views.GroupView:
    view = schedule_views.get_group_view(db, group_id, current_user.id, app_settings.user_timezone(current_user))
    if view is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return view


@router.get("/ui/schedules/{group_id}", response_class=HTMLResponse)
async def ui_schedule_detail(
    request: Request,
    group_id: str,
    notice: str | None = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    view = _owned_group_view(db, group_id, current_user)
    return templates.TemplateResponse(
        "_schedule_detail_modal.html", {"request": request, "g": view, "notice": notice, "tz_label": timing.tz_label(view.tz_name)}
    )


def _edit_form_ctx(db: Session, current_user: User, view: schedule_views.GroupView, **overrides: object) -> dict:
    group = view.group
    wa = whatsapp_service.session_by_name(db, current_user.id, group.session)
    base = dict(
        mode="edit",
        action=f"/ui/schedules/{group.id}/edit",
        target="#modal-root",
        swap="innerHTML",
        recipient_label=view.recipient,
        messages=[m.text for m in view.messages],
        send_date=group.start_local.strftime("%Y-%m-%d"),
        send_time=group.start_local.strftime("%H:%M"),
        whatsapp_session_id=wa.id if wa else "",
        recurrence=view.recurrence or "",
        advanced_open=bool(view.recurrence),
    )
    base.update(overrides)
    return _schedule_form_ctx(db, current_user, **base)


@router.get("/ui/schedules/{group_id}/edit", response_class=HTMLResponse)
async def ui_schedule_edit(
    request: Request,
    group_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    view = _owned_group_view(db, group_id, current_user)
    if not view.editable:
        return templates.TemplateResponse(
            "_schedule_detail_modal.html",
            {
                "request": request, "g": view, "tz_label": timing.tz_label(view.tz_name),
                "notice": "Este agendamento não pode mais ser editado (já começou a ser enviado, foi cancelado ou vem de uma automação do Calendário).",
            },
        )
    return templates.TemplateResponse(
        "_schedule_edit_modal.html", {"request": request, "g": view, "form": _edit_form_ctx(db, current_user, view)}
    )


@router.post("/ui/schedules/{group_id}/edit", response_class=HTMLResponse)
async def ui_schedule_update(
    request: Request,
    group_id: str,
    messages: list[str] = Form([]),
    send_date: str = Form(""),
    send_time: str = Form(""),
    whatsapp_session_id: str = Form(""),
    recurrence: str = Form(""),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    view = _owned_group_view(db, group_id, current_user)
    tz_name = app_settings.user_timezone(current_user)
    try:
        wa_session = whatsapp_service.get_session(db, whatsapp_session_id, current_user.id)
        if wa_session is None:
            raise ValidationError("Escolha por qual WhatsApp enviar.")
        start = _start_from_form(send_date, send_time, "")
        await whatsapp_service.require_session_ready(request.app.state.waha, wa_session)
        await asyncio.to_thread(
            update_sequence, db, group_id, user_id=current_user.id, session=wa_session.session_name,
            messages=messages, start=start, recurrence=recurrence or None,
        )
    except ValidationError as exc:
        form = _edit_form_ctx(
            db, current_user, view, messages=messages or [""], send_date=send_date, send_time=send_time,
            whatsapp_session_id=whatsapp_session_id, recurrence=recurrence, advanced_open=bool(recurrence), error=str(exc),
        )
        return templates.TemplateResponse("_schedule_edit_modal.html", {"request": request, "g": view, "form": form})
    return templates.TemplateResponse(
        "_table.html", _table_ctx(request, db, current_user.id, tz_name, oob=True)
    )


@router.post("/ui/schedules/{group_id}/cancel", response_class=HTMLResponse)
async def ui_cancel(
    request: Request,
    group_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    cancel_group(db, group_id, user_id=current_user.id)
    return _table_response(request, db, current_user)


@router.post("/ui/schedules/{group_id}/run-now", response_class=HTMLResponse)
async def ui_run_now(
    request: Request,
    group_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    """Antecipa o envio (teste ponta a ponta): a sequência inteira passa a começar agora."""
    _owned_group_view(db, group_id, current_user)  # 404 se não for do usuário
    run_group_now(db, group_id, user_id=current_user.id)
    return _table_response(request, db, current_user)


# ---- Conversas -------------------------------------------------------------- #
def _owned_wa_session(db: Session, session_id: str, user_id: str):
    session = whatsapp_service.get_session(db, session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="WhatsApp não encontrado.")
    return session


async def _chats_ctx(request: Request, db: Session, current_user: User, session_id: str, *, force: bool = False) -> dict:
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    try:
        chats = await list_chats(
            request.app.state.waha, wa_session.session_name, app_settings.user_timezone(current_user), force=force
        )
        return {"request": request, "session_id": session_id, "chats": chats, "chats_error": None}
    except WahaError as exc:
        return {"request": request, "session_id": session_id, "chats": [], "chats_error": str(exc)}


def _find_chat(chats: list[dict], chat_id: str) -> dict:
    for c in chats:
        if c["id"] == chat_id:
            return c
    return {"id": chat_id, "name": chat_id.split("@")[0], "picture": None, "is_group": chat_id.endswith("@g.us")}


@router.get("/ui/chats/{session_id}", response_class=HTMLResponse)
async def ui_chats(
    request: Request,
    session_id: str,
    refresh: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    return templates.TemplateResponse("_chat_list.html", await _chats_ctx(request, db, current_user, session_id, force=refresh))


def _scheduled_ctx(db: Session, current_user: User, wa_session, chat_id: str) -> dict:
    items, _sent_ids = schedule_views.conversation_items(
        db, current_user.id, wa_session.session_name, chat_id, app_settings.user_timezone(current_user)
    )
    return {"scheduled_items": items, "open_count": sum(1 for m in items if m.status in ("scheduled", "sending"))}


def _chat_schedule_form(db: Session, current_user: User, **overrides: object) -> dict:
    form = _schedule_form_ctx(db, current_user, target="#chat-view", swap="innerHTML", **overrides)
    form.setdefault("open", False)
    return form


async def _render_chat_view(
    request: Request,
    db: Session,
    current_user: User,
    session_id: str,
    chat: str,
    *,
    ok: str | None = None,
    schedule_form: dict | None = None,
) -> HTMLResponse:
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    chats = (await _chats_ctx(request, db, current_user, session_id))["chats"]
    return templates.TemplateResponse(
        "_chat_view.html",
        {
            "request": request,
            "session_id": session_id,
            "chat_id": chat,
            "chat": _find_chat(chats, chat),
            "default_timezone": app_settings.user_timezone(current_user),
            "tz_label": timing.tz_label(app_settings.user_timezone(current_user)),
            "wa_name": wa_session.name,
            "ok": ok,
            "schedule_form": schedule_form or _chat_schedule_form(db, current_user),
            **_scheduled_ctx(db, current_user, wa_session, chat),
        },
    )


@router.get("/ui/chats/{session_id}/view", response_class=HTMLResponse)
async def ui_chat_view(
    request: Request,
    session_id: str,
    chat: str = Query(...),
    ok: str | None = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    return await _render_chat_view(request, db, current_user, session_id, chat, ok=ok)


@router.get("/ui/chats/{session_id}/messages", response_class=HTMLResponse)
async def ui_chat_messages(
    request: Request,
    session_id: str,
    chat: str = Query(...),
    refresh: bool = Query(False),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    tz_name = app_settings.user_timezone(current_user)
    hist = await get_history(
        db, request.app.state.waha, current_user.id, wa_session.session_name, chat, tz_name, force=refresh,
    )
    _items, sent_ids = schedule_views.conversation_items(db, current_user.id, wa_session.session_name, chat, tz_name)
    return templates.TemplateResponse(
        "_chat_messages.html",
        {
            "request": request, "chat_id": chat, "hist": hist, "sent_ids": sent_ids,
            "synced_local": _sync_label(hist.synced_at, tz_name),
        },
    )


@router.get("/ui/chats/{session_id}/scheduled", response_class=HTMLResponse)
async def ui_chat_scheduled(
    request: Request,
    session_id: str,
    chat: str = Query(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    """Só as mensagens agendadas da conversa (atualizadas sozinhas a cada poucos
    segundos) — vêm do banco, então aparecem na hora, sem esperar o WhatsApp."""
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    return templates.TemplateResponse(
        "_chat_scheduled.html",
        {"request": request, "session_id": session_id, "chat_id": chat, **_scheduled_ctx(db, current_user, wa_session, chat)},
    )


@router.post("/ui/chats/{session_id}/scheduled/{schedule_id}/cancel", response_class=HTMLResponse)
async def ui_chat_scheduled_cancel(
    request: Request,
    session_id: str,
    schedule_id: str,
    chat: str = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    """Cancela UMA mensagem agendada (pelo mecanismo de sempre, `service.cancel_schedule`):
    ela fica como "Cancelada" na conversa e não é enviada. As outras da sequência continuam."""
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    cancel_schedule(db, schedule_id, user_id=current_user.id)
    return templates.TemplateResponse(
        "_chat_scheduled.html",
        {"request": request, "session_id": session_id, "chat_id": chat, **_scheduled_ctx(db, current_user, wa_session, chat)},
    )


@router.post("/ui/chats/{session_id}/send", response_class=HTMLResponse)
async def ui_chat_send(
    request: Request,
    session_id: str,
    chat: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    text = text.strip()
    ok = None
    if not text:
        ok = "erro:Mensagem vazia."
    else:
        try:
            await send_now(db, request.app.state.waha, current_user.id, wa_session.session_name, chat, text)
            ok = "Mensagem enviada."
        except WahaError as exc:
            ok = f"erro:{exc}"
    return await _render_chat_view(request, db, current_user, session_id, chat, ok=ok)


@router.post("/ui/chats/{session_id}/schedule", response_class=HTMLResponse)
async def ui_chat_schedule(
    request: Request,
    session_id: str,
    chat: str = Form(...),
    messages: list[str] = Form([]),
    text: str = Form(""),
    send_date: str = Form(""),
    send_time: str = Form(""),
    send_at: str = Form(""),
    recurrence: str = Form(""),
    db: Session = Depends(get_session),
    current_user: User = Depends(auth.require_user_web),
) -> HTMLResponse:
    """Agenda UMA sequência de mensagens para esta conversa. Data e horário são o
    INÍCIO da sequência e são preservados: depois de salvar o painel volta com o
    mesmo horário; se der erro, volta aberto e com tudo o que foi digitado."""
    wa_session = _owned_wa_session(db, session_id, current_user.id)
    tz_name = app_settings.user_timezone(current_user)
    texts = messages if messages else ([text] if text.strip() else [])
    try:
        start = _start_from_form(send_date, send_time, send_at)
        await whatsapp_service.require_session_ready(request.app.state.waha, wa_session)
        name = cached_chat_name(wa_session.session_name, chat)
        await asyncio.to_thread(
            create_sequence,
            db,
            user_id=current_user.id,
            session=wa_session.session_name,
            recipient=chat,
            recipient_name=name,
            messages=texts,
            start=start,
            timezone=tz_name,
            source=ScheduleSource.conversation,
            recurrence=recurrence or None,
            allow_past=False,
            dedupe=True,
        )
    except ValidationError as exc:
        form = _chat_schedule_form(
            db, current_user, messages=texts or [""], send_date=send_date or _form_start_values(None, tz_name)[0],
            send_time=send_time or _form_start_values(None, tz_name)[1], recurrence=recurrence,
            advanced_open=bool(recurrence), whatsapp_session_id=wa_session.id,
        )
        form["open"] = True
        return await _render_chat_view(
            request, db, current_user, session_id, chat, ok=f"erro:{exc}", schedule_form=form
        )
    count = len([t for t in texts if t.strip()])
    form = _chat_schedule_form(
        db, current_user, send_date=start.strftime("%Y-%m-%d"), send_time=start.strftime("%H:%M"),
        whatsapp_session_id=wa_session.id,
    )
    return await _render_chat_view(
        request, db, current_user, session_id, chat,
        ok="Agendamento criado." if count == 1 else f"Agendamento criado — {count} mensagens.",
        schedule_form=form,
    )


def _sync_label(dt: datetime | None, tz_name: str) -> str:
    if dt is None:
        return ""
    return utc_to_local(dt, tz_name).strftime("%d/%m %H:%M:%S")
