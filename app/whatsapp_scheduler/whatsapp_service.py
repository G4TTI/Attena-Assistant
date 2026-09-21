"""Regra de negócio de conexões WhatsApp (v1.3: um usuário pode ter várias).
Equivalente a `calendar_service.py`, mas para `WhatsAppSession` — o cliente
WAHA em si (start/restart/QR/status) continua chamado diretamente pela rota,
mesmo padrão que `web/routes.py` já usa hoje para a sessão única.
"""

from __future__ import annotations

import asyncio
import hashlib

from sqlmodel import Session, col, select

from .clock import utcnow
from .models import Schedule, User, WhatsAppSession
from .service import ValidationError, cancel_schedules
from .waha import WahaClient, WahaError


def ensure_first_session(db: Session, user: User) -> WhatsAppSession | None:
    """Cria a primeira `WhatsAppSession` de um usuário reaproveitando
    `User.waha_session` (nunca gera um `session_name` novo aqui) — usada
    tanto no cadastro de conta nova quanto na migração de contas legadas
    (`migrate_legacy_sessions`), pra nunca existirem dois nomes de sessão
    WAHA "perdidos" pro mesmo usuário. Não faz nada (retorna `None`) se o
    usuário já tem alguma sessão, mesmo desconectada."""
    already_has = db.exec(
        select(WhatsAppSession.id).where(col(WhatsAppSession.user_id) == user.id)
    ).first()
    if already_has is not None:
        return None
    session = WhatsAppSession(user_id=user.id, name="WhatsApp", session_name=user.waha_session)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def migrate_legacy_sessions(db: Session) -> None:
    """Idempotente, chamada no boot (main.py lifespan) — mesmo padrão de
    `calendar_service.migrate_legacy_automations`. Cria, para cada usuário
    que ainda não tem nenhuma `WhatsAppSession`, uma primeira linha usando o
    `User.waha_session` (v1.2, único por usuário) já existente — preserva o
    pareamento já feito, sem exigir escanear QR de novo. Contas criadas
    depois que `WhatsAppSession` já existia ganham a sua no próprio cadastro
    (ver `auth_service.register_user`), então isto só importa de fato pra
    quem já existia antes desta versão.
    """
    users = db.exec(select(User)).all()
    for user in users:
        ensure_first_session(db, user)


def list_sessions(db: Session, user_id: str) -> list[WhatsAppSession]:
    return list(
        db.exec(
            select(WhatsAppSession)
            .where(col(WhatsAppSession.user_id) == user_id)
            .where(col(WhatsAppSession.disconnected_at).is_(None))
            .order_by(col(WhatsAppSession.created_at))
        ).all()
    )


def primary_session(db: Session, user_id: str) -> WhatsAppSession | None:
    """A conexão mais antiga ainda ativa do usuário — só um valor-padrão de
    conveniência pra pré-selecionar em formulários (ex.: 1 clique quando só
    existe uma). Nunca é um "WhatsApp ativo" persistido/lembrado: cada
    automação/agendamento sempre grava explicitamente qual sessão escolheu
    (`Schedule.session`), então isto é recalculado a cada chamada, nunca lido
    de volta como fonte de verdade de nada."""
    sessions = list_sessions(db, user_id)
    return sessions[0] if sessions else None


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
    cancel_schedules(db, [schedule.id for schedule in open_schedules], user_id=user_id)

    session.disconnected_at = utcnow()
    session.updated_at = utcnow()
    db.add(session)
    db.commit()
    return True


def status_signature(rows: list[dict] | dict | None) -> str:
    """Impressão digital curta do que a tela de conexão (onboarding / Configurações →
    Conexões) MOSTRA: cada WhatsApp, o nome, o status, o número e o erro. A tela consulta
    o servidor a cada poucos segundos mandando esta assinatura; se nada mudou o servidor
    responde 204 e o navegador não mexe em nada — antes o passo inteiro era recriado a cada
    consulta, e era isso que fazia botão e QR piscarem."""
    if rows is None:
        rows = []
    elif isinstance(rows, dict):
        rows = [rows]
    parts: list[str] = []
    for row in rows:
        session = row.get("session")
        info = row.get("status") or {}
        me = info.get("me") if isinstance(info.get("me"), dict) else {}
        parts.append(
            "|".join(
                str(x)
                for x in (
                    getattr(session, "id", ""),
                    getattr(session, "name", ""),
                    info.get("status", ""),
                    me.get("id", ""),
                    row.get("status_error") or "",
                )
            )
        )
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()[:12]


NOT_STARTED_MESSAGE = "Esta conexão ainda não foi iniciada. Clique em “Iniciar / reconectar” pra gerar o QR."


async def status_rows(
    waha: WahaClient, sessions: list[WhatsAppSession], *, ensure: bool = False
) -> list[dict]:
    """Status ao vivo (nunca cacheado — mesma escolha da sessão única antes)
    de cada conexão, uma chamada ao WAHA por sessão. Usado pela página
    `/whatsapps`, pelo card do Dashboard e pela sidebar.

    `ensure=True` cria no WAHA a sessão que ainda não existir (onboarding e
    aba Conexões, onde o usuário está ali pra conectar). Fica desligado nos
    consumidores passivos (sidebar/dashboard, que pesquisam a cada poucos
    segundos): eles nunca devem sair criando Chromium por conta própria."""
    # Em paralelo: a sidebar consulta isto a cada poucos segundos, e com N
    # WhatsApps a versão sequencial somava a latência de todos (ou o timeout
    # inteiro de cada um que estivesse fora do ar).
    fetch = waha.ensure_session if ensure else waha.get_session_status

    async def _one(session: WhatsAppSession) -> dict:
        try:
            info = await fetch(session.session_name)
            return {"session": session, "status": info, "status_error": None}
        except WahaError as exc:
            message = NOT_STARTED_MESSAGE if exc.status_code == 404 else str(exc)
            return {"session": session, "status": None, "status_error": message}

    return list(await asyncio.gather(*(_one(s) for s in sessions)))


async def overall_status(waha: WahaClient, sessions: list[WhatsAppSession]) -> str:
    """"ok" | "pending" | "error" | "none" — resumo de todas as conexões num
    indicador só (dot da sidebar). "ok" se qualquer uma estiver WORKING."""
    if not sessions:
        return "none"
    rows = await status_rows(waha, sessions)
    statuses = [str((row["status"] or {}).get("status") or "").upper() for row in rows]
    if "WORKING" in statuses:
        return "ok"
    if any(s in ("SCAN_QR_CODE", "STARTING") for s in statuses):
        return "pending"
    return "error"


def labels_by_session_name(db: Session, user_id: str) -> dict[str, str]:
    """`Schedule.session` -> nome de exibição, incluindo conexões já
    desconectadas (histórico antigo ainda precisa mostrar qual WhatsApp foi
    usado — Parte 17)."""
    rows = db.exec(select(WhatsAppSession).where(col(WhatsAppSession.user_id) == user_id)).all()
    return {row.session_name: row.name for row in rows}


# --------------------------------------------------------------------------- #
# Seletor "Enviar através de" (WhatsAppSessionPicker) e checagem antes de agendar
# --------------------------------------------------------------------------- #
# WORKING = pronto. STARTING é transitório (o scheduler adia o envio até ficar
# pronto), então ainda dá pra agendar. O resto (QR pendente, parada, falha) é
# "desconectado": não dá pra agendar por ali.
_READY_STATUSES = ("WORKING", "STARTING")
_STATUS_TEXT = {
    "WORKING": "conectado",
    "STARTING": "conectando",
    "SCAN_QR_CODE": "desconectado — escaneie o QR",
    "STOPPED": "desconectado",
    "FAILED": "desconectado (falha)",
}


def _phone_of(info: dict | None) -> str:
    me = (info or {}).get("me") or {}
    ident = me.get("id") if isinstance(me, dict) else None
    return "+" + str(ident).split("@")[0] if ident else ""


async def picker_options(waha: WahaClient, sessions: list[WhatsAppSession], *, timeout: float = 4.0) -> list[dict]:
    """Uma entrada por WhatsApp do usuário, com status pra o seletor. Nunca
    demora mais que `timeout`: se o WAHA não respondeu, o status fica
    "unknown" (selecionável — a checagem definitiva é `require_session_ready`
    na hora de salvar)."""
    try:
        rows = await asyncio.wait_for(status_rows(waha, sessions), timeout=timeout)
    except asyncio.TimeoutError:
        rows = [{"session": s, "status": None, "status_error": "sem resposta"} for s in sessions]
    out: list[dict] = []
    for row in rows:
        session, info = row["session"], row["status"]
        status = str((info or {}).get("status") or "").upper()
        if info is None:
            level, text = "unknown", "status indisponível"
        elif status == "WORKING":
            level, text = "ok", _STATUS_TEXT["WORKING"]
        elif status == "STARTING":
            level, text = "warn", _STATUS_TEXT["STARTING"]
        else:
            level, text = "err", _STATUS_TEXT.get(status, "desconectado")
        out.append(
            {
                "id": session.id,
                "name": session.name,
                "session_name": session.session_name,
                "phone": _phone_of(info),
                "level": level,
                "status_text": text,
                "selectable": level != "err",
            }
        )
    return out


async def require_session_ready(waha: WahaClient, session: WhatsAppSession) -> None:
    """Impede agendar por um WhatsApp desconectado — o erro aparece AGORA, no
    formulário, e não só quando o envio falhar horas depois."""
    if session.disconnected_at is not None:
        # Um formulário aberto antes de a conexão ser removida ainda pode mandar o id dela.
        raise ValidationError(
            f"O WhatsApp “{session.name}” foi desconectado. Escolha outro ou conecte-o de novo em Configurações → Conexões."
        )
    try:
        info = await waha.get_session_status(session.session_name)
    except WahaError as exc:
        raise ValidationError(
            f"Não consegui verificar o WhatsApp “{session.name}” agora ({exc}). Tente novamente em instantes."
        ) from exc
    status = str(info.get("status") or "").upper()
    if status not in _READY_STATUSES:
        raise ValidationError(
            f"O WhatsApp “{session.name}” está {_STATUS_TEXT.get(status, 'desconectado')}. "
            "Reconecte-o em Configurações → Conexões antes de agendar."
        )
