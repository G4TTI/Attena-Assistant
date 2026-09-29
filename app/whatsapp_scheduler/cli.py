"""Comandos de operação — rodam NO SERVIDOR, por quem tem acesso a ele:

    docker compose exec app python -m whatsapp_scheduler.cli <comando>

  generate-keys            imprime chaves novas para o .env (não grava nada)
  setup-owner              cria/redefine a CONTA PRINCIPAL (e-mail de ADMIN_OWNER_EMAIL);
                           a senha é lida da entrada padrão (nunca como argumento)
  revoke-admin <e-mail>    emergência: remove o acesso de um administrador
  reset-link <e-mail>      gera um link de redefinição de senha (sem provedor de e-mail)
  verify-link <e-mail>     gera um link de verificação de e-mail
  rotate-keys              recifra tudo com a versão ativa de DATA_ENCRYPTION_KEYS
  privacy-cleanup          roda a limpeza de retenção uma vez
  privacy-report           contagens do que existe cifrado/expurgado (nunca conteúdo)

A conta principal só nasce aqui (servidor). Todo outro administrador é
concedido POR ELA, no painel (plano "Administrador") — não há comando para
promover alguém direto a admin.
Links e chaves vão para a saída do terminal de quem rodou o comando — nunca
para o log da aplicação.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from sqlmodel import Session, col, select

from . import auth, privacy, retention
from .admin.access import revoke_admin
from .auth_service import create_email_verification_link, create_password_reset_link, setup_owner
from .config import settings
from .db import get_engine, init_db
from .models import (
    AutomationMessage,
    BillingProfile,
    CrmNote,
    Schedule,
    ScheduleGroup,
    User,
)


def _user(db: Session, email: str) -> User:
    user = db.exec(select(User).where(col(User.email) == auth.normalize_email(email))).first()
    if user is None:
        print(f"Nenhum usuário com o e-mail {email!r}.", file=sys.stderr)
        raise SystemExit(1)
    return user


def cmd_generate_keys(_args) -> None:
    print("# Chaves NOVAS — guarde no .env do servidor (nunca no Git).")
    print("# Gere um par diferente para cada ambiente (desenvolvimento, teste, produção).")
    print(f"DATA_ENCRYPTION_KEYS=1:{privacy.generate_key()}")
    print(f"DATA_HASH_KEY={privacy.generate_key()}")


def _read_password() -> str:
    """Senha pela entrada padrão (pipe) ou digitada duas vezes no terminal —
    nunca como argumento de linha de comando (ficaria no histórico/`ps`)."""
    if not sys.stdin.isatty():
        return sys.stdin.readline().rstrip("\n")
    first = getpass.getpass("Senha da conta principal: ")
    if first != getpass.getpass("Repita a senha: "):
        print("As senhas não coincidem.", file=sys.stderr)
        raise SystemExit(1)
    return first


def cmd_setup_owner(args) -> None:
    email = args.email or settings.admin_owner_email
    password = _read_password()
    with Session(get_engine()) as db:
        try:
            _user, created, demoted = setup_owner(db, email=email, password=password, name=args.name)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
    print(f"conta principal {'criada' if created else 'redefinida'}: {email}")
    print(f"administradores anteriores rebaixados: {demoted} (conceda de novo pelo painel, se quiser)")


def cmd_revoke_admin(args) -> None:
    with Session(get_engine()) as db:
        user = _user(db, args.email)
        if user.role == "owner":
            print("A conta principal não é rebaixada por aqui; use setup-owner com outro e-mail.", file=sys.stderr)
            raise SystemExit(1)
        changed = revoke_admin(db, user)
        auth.revoke_all_sessions(db, user)
    print(f"{args.email}: " + ("acesso de administrador removido (sessões encerradas)" if changed else "não era administrador"))


def cmd_reset_link(args) -> None:
    with Session(get_engine()) as db:
        path = create_password_reset_link(db, _user(db, args.email))
    print(args.base_url.rstrip("/") + path)
    print(f"(expira em {settings.password_reset_ttl_minutes} min; entregue só ao dono da conta)")


def cmd_verify_link(args) -> None:
    with Session(get_engine()) as db:
        path = create_email_verification_link(db, _user(db, args.email))
    print(args.base_url.rstrip("/") + path)


def _rotate_sealed(obj, open_fn, seal_fn) -> bool:
    if not obj.message_ciphertext or obj.encryption_key_version == privacy.active_key_version():
        return False
    seal_fn(obj, open_fn(obj))
    return True


def cmd_rotate_keys(_args) -> None:
    counts = {"schedules": 0, "groups": 0, "automation_messages": 0, "billing": 0, "crm_notes": 0}
    with Session(get_engine()) as db:
        for s in db.exec(select(Schedule)).all():
            changed = _rotate_sealed(s, privacy.schedule_message, privacy.seal_schedule_message)
            if s.recipient_phone_encrypted and privacy.envelope_version(s.recipient_phone_encrypted) != privacy.active_key_version():
                chat_id = privacy.schedule_recipient(s)
                hash_before = s.recipient_phone_hash
                privacy.seal_schedule_recipient(s, chat_id)
                s.recipient_phone_hash = hash_before  # o HMAC não depende da chave de cifra
                changed = True
            if changed:
                db.add(s)
                counts["schedules"] += 1
        for g in db.exec(select(ScheduleGroup)).all():
            if g.recipient_encrypted and privacy.envelope_version(g.recipient_encrypted) != privacy.active_key_version():
                info = privacy.group_recipient(g)
                hash_before = g.recipient_phone_hash
                privacy.seal_group_recipient(g, chat_id=info.chat_id, recipient_input=info.input, recipient_name=info.name)
                g.recipient_phone_hash = hash_before
                db.add(g)
                counts["groups"] += 1
        for m in db.exec(select(AutomationMessage)).all():
            if _rotate_sealed(m, privacy.automation_message, privacy.seal_automation_message):
                db.add(m)
                counts["automation_messages"] += 1
        for b in db.exec(select(BillingProfile)).all():
            changed = False
            for field in ("full_name", "cpf", "phone", "postal_code", "address", "address_number", "address_complement", "city"):
                attr = f"{field}_encrypted"
                value = getattr(b, attr)
                if value and privacy.envelope_version(value) != privacy.active_key_version():
                    plain = privacy.open_field("billing_profiles", field, b.id, value)
                    setattr(b, attr, privacy.seal_field("billing_profiles", field, b.id, plain))
                    changed = True
            if changed:
                db.add(b)
                counts["billing"] += 1
        for n in db.exec(select(CrmNote)).all():
            if n.body_encrypted and privacy.envelope_version(n.body_encrypted) != privacy.active_key_version():
                privacy.seal_crm_note(n, privacy.crm_note_body(n))
                db.add(n)
                counts["crm_notes"] += 1
        db.commit()
    print("recifrado com a versão", privacy.active_key_version(), counts)


def cmd_privacy_cleanup(_args) -> None:
    counts = asyncio.run(retention.run_cleanup_async(None))
    print("records_cleaned:", sum(counts.values()), counts)


def cmd_privacy_report(_args) -> None:
    from sqlalchemy import func, text

    with Session(get_engine()) as db:
        tables = {r[0] for r in db.exec(text("SELECT name FROM sqlite_master WHERE type='table'")).all()}

        def count(query) -> int:
            return int(db.exec(query).one())

        report = {
            "tabela cached_messages (histórico de conversas)": "existe" if "cached_messages" in tables else "não existe",
            "mensagens programadas com conteúdo cifrado": count(
                select(func.count()).select_from(Schedule).where(col(Schedule.message_ciphertext).is_not(None))
            ),
            "mensagens com conteúdo expurgado": count(
                select(func.count()).select_from(Schedule).where(col(Schedule.content_purged_at).is_not(None))
            ),
            "encerradas que ainda têm conteúdo (deveria ser 0)": count(
                select(func.count()).select_from(Schedule)
                .where(~retention.schedule_active_clause())
                .where(col(Schedule.message_ciphertext).is_not(None))
            ),
            "destinatários cifrados (agendamentos)": count(
                select(func.count()).select_from(ScheduleGroup).where(col(ScheduleGroup.recipient_encrypted).is_not(None))
            ),
            "perfis de faturamento": count(select(func.count()).select_from(BillingProfile)),
            "conta principal": count(select(func.count()).select_from(User).where(col(User.role) == "owner")),
            "administradores concedidos": count(select(func.count()).select_from(User).where(col(User.role) == "admin")),
        }
    for key, value in report.items():
        print(f"{key}: {value}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m whatsapp_scheduler.cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate-keys").set_defaults(func=cmd_generate_keys, needs_db=False)
    p = sub.add_parser("setup-owner")
    p.add_argument("--email", default="", help="padrão: ADMIN_OWNER_EMAIL")
    p.add_argument("--name", default="Administrador")
    p.set_defaults(func=cmd_setup_owner, needs_db=True)
    p = sub.add_parser("revoke-admin")
    p.add_argument("email")
    p.set_defaults(func=cmd_revoke_admin, needs_db=True)
    for name, fn in (("reset-link", cmd_reset_link), ("verify-link", cmd_verify_link)):
        p = sub.add_parser(name)
        p.add_argument("email")
        p.add_argument("--base-url", default="", help="ex.: https://app.exemplo.com (padrão: só o caminho)")
        p.set_defaults(func=fn, needs_db=True)
    sub.add_parser("rotate-keys").set_defaults(func=cmd_rotate_keys, needs_db=True)
    sub.add_parser("privacy-cleanup").set_defaults(func=cmd_privacy_cleanup, needs_db=True)
    sub.add_parser("privacy-report").set_defaults(func=cmd_privacy_report, needs_db=True)
    args = parser.parse_args(argv)
    if args.needs_db:
        privacy.check_configuration()
        init_db()
    args.func(args)


if __name__ == "__main__":
    main()
