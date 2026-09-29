"""Área administrativa: controle de acesso real no servidor, CRM, auditoria e
— principalmente — nenhuma forma de ler conteúdo privado dos clientes."""

import asyncio
import re
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.conftest import FakeWaha, db_locations_containing, register_and_login, whatsapp_session_id
from whatsapp_scheduler import cli, plans
from whatsapp_scheduler.billing import metrics as billing_metrics
from whatsapp_scheduler.billing import service as billing_service
from whatsapp_scheduler.billing.validation import validate_form
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import AdminAuditLog, CrmNote, Payment, User, UserSession, WhatsAppSession
from whatsapp_scheduler.service import create_sequence

SECRET = "conteúdo privadíssimo da mensagem"
PHONE = "+55 14 99111-0001"


def _make_admin(email: str) -> None:
    cli.main(["grant-admin", email])


def _csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([0-9a-f]{64})"', html)
    assert match, "formulário do admin sem token CSRF"
    return match.group(1)


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        yield c


@pytest.fixture
def customer(client):
    """Um cliente com mensagem programada, contato e dados de faturamento."""
    user = register_and_login(client, name="Cliente Um", email="cliente@example.com")
    sid = whatsapp_session_id(client)
    with Session(get_engine()) as db:
        session_name = db.get(WhatsAppSession, sid).session_name
        create_sequence(db, user_id=user.id, session=session_name, recipient=PHONE, recipient_name="Paciente Fulano",
                        messages=[SECRET], start=utcnow() + timedelta(days=30), timezone="America/Sao_Paulo")
        u = db.get(User, user.id)
        billing_service.save_profile(db, u, validate_form({
            "full_name": "Cliente Um da Silva", "cpf": "529.982.247-25", "phone": "(11) 98888-7777",
            "postal_code": "01310-100", "address": "Av. Paulista", "address_number": "1000",
            "address_complement": "", "city": "São Paulo", "state": "SP",
        }, has_saved_cpf=False))
    client.cookies.clear()
    return user


@pytest.fixture
def admin_client(client, customer):
    register_and_login(client, name="Admin", email="admin@example.com")
    _make_admin("admin@example.com")
    return client


# --------------------------------------------------------------------------- #
# Controle de acesso
# --------------------------------------------------------------------------- #
ADMIN_PAGES = ["/admin", "/admin/usuarios", "/admin/crm", "/admin/planos", "/admin/faturamento",
               "/admin/agendamentos", "/admin/logins", "/admin/auditoria"]


def test_anonymous_is_sent_to_login(client):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


def test_regular_user_gets_404_everywhere_even_forging_role(client, customer):
    register_and_login(client, name="Comum", email="comum@example.com")
    forged = {"X-Role": "admin", "X-User-Role": "admin", "Cookie-Role": "admin"}
    client.cookies.set("role", "admin")
    for path in ADMIN_PAGES + [f"/admin/usuarios/{customer.id}"]:
        assert client.get(path, headers=forged, params={"role": "admin", "admin": "1"}).status_code == 404, path
    r = client.post(f"/admin/usuarios/{customer.id}/suspender", data={"csrf_token": "x", "role": "admin"})
    assert r.status_code == 404
    with Session(get_engine()) as db:
        assert db.get(User, customer.id).is_active is True
    # o link de atalho nem aparece para quem não é admin
    assert 'href="/admin"' not in client.get("/planos").text


def test_admin_role_is_read_from_the_database_every_request(admin_client):
    assert admin_client.get("/admin").status_code == 200
    cli.main(["revoke-admin", "admin@example.com"])  # também encerra as sessões
    assert admin_client.get("/admin", follow_redirects=False).status_code in (303, 404)


def test_every_admin_page_renders_for_admin(admin_client):
    for path in ADMIN_PAGES:
        r = admin_client.get(path)
        assert r.status_code == 200, path
        assert "ADMIN" in r.text
    assert 'href="/admin"' in admin_client.get("/planos").text  # atalho para admins


def test_old_admin_session_must_log_in_again(admin_client):
    with Session(get_engine()) as db:
        for session in db.exec(select(UserSession)).all():
            session.created_at = utcnow() - timedelta(hours=13)
            db.add(session)
        db.commit()
    r = admin_client.get("/admin", follow_redirects=False)
    assert r.status_code == 303 and "/login" in r.headers["location"]
    assert admin_client.get("/configuracoes", follow_redirects=False).status_code == 303  # sessão encerrada


def test_admin_posts_require_csrf_token(admin_client, customer):
    r = admin_client.post(f"/admin/usuarios/{customer.id}/crm/status", data={"status": "ativo"})
    assert r.status_code == 403
    r = admin_client.post(f"/admin/usuarios/{customer.id}/crm/status", data={"status": "ativo", "csrf_token": "0" * 64})
    assert r.status_code == 403


def test_cross_site_post_is_rejected_by_origin_check(admin_client, customer):
    token = _csrf(admin_client.get(f"/admin/usuarios/{customer.id}").text)
    r = admin_client.post(
        f"/admin/usuarios/{customer.id}/crm/status", data={"status": "ativo", "csrf_token": token},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


def test_admin_rate_limit(admin_client, monkeypatch):
    from whatsapp_scheduler.config import settings

    monkeypatch.setattr(settings, "admin_rate_limit_requests", 3)
    codes = [admin_client.get("/admin/logins").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[-1] == 429


# --------------------------------------------------------------------------- #
# Proibido no admin
# --------------------------------------------------------------------------- #
def test_no_admin_route_exposes_messages_conversations_or_media():
    forbidden = re.compile(r"messag|mensag|conversa|chat|histor|midia|media|audio|imag|document", re.I)
    admin_paths = [r.path for r in app.routes if getattr(r, "path", "").startswith("/admin")]
    assert admin_paths, "rotas do admin não registradas"
    assert [p for p in admin_paths if forbidden.search(p)] == []


def test_admin_code_never_touches_decryption_of_user_content():
    """Nada no pacote admin (nem nas rotas/templates dele) chama as funções que
    decifram mensagem, destinatário ou dado de faturamento."""
    root = Path(__file__).resolve().parents[1] / "whatsapp_scheduler"
    sources = list((root / "admin").glob("*.py")) + [root / "web" / "admin_routes.py"]
    sources += list((root / "web" / "templates" / "admin").glob("*.html"))
    forbidden = ["schedule_message", "schedule_recipient", "group_recipient", "automation_message",
                 "open_field", "decrypt_field", "unseal", "owner_form_values", "message_ciphertext",
                 "recipient_phone_encrypted", "recipient_encrypted", "cpf_encrypted", "password_hash",
                 "access_token_enc", "refresh_token_enc"]
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for name in forbidden:
            assert name not in text, f"{path.name} usa {name}"


def test_admin_pages_never_show_content_phone_or_full_cpf(admin_client, customer):
    pages = [admin_client.get(p).text for p in ADMIN_PAGES]
    pages.append(admin_client.get(f"/admin/usuarios/{customer.id}").text)
    pages.append(admin_client.get("/admin/agendamentos", params={"status": "pending"}).text)
    blob = "\n".join(pages)
    for needle in (SECRET, "privadíssimo", "99111-0001", "991110001", "Paciente Fulano", "529.982.247-25",
                   "52998224725", "Av. Paulista", "01310-100"):
        assert needle not in blob, needle
    assert "***.***.***-25" in admin_client.get(f"/admin/usuarios/{customer.id}").text  # CPF só mascarado


def test_schedule_health_shows_only_metadata(admin_client, customer):
    html = admin_client.get("/admin/agendamentos").text
    assert "Cliente Um" in html and "pendente" in html
    assert SECRET not in html and "991110001" not in html


# --------------------------------------------------------------------------- #
# Usuários, filtros, CRM e auditoria
# --------------------------------------------------------------------------- #
def test_users_list_search_filter_sort_and_counts(admin_client, customer):
    html = admin_client.get("/admin/usuarios", params={"q": "cliente"}).text
    assert "Cliente Um" in html and "cliente@example.com" in html and "Admin" not in re.sub(r"<[^>]+>", " ", html.split("<tbody>")[1])
    row = html.split("cliente@example.com")[1].split("</tr>")[0]
    assert re.findall(r'<td class="num">(\d+)</td>', row) == ["1", "1"]  # 1 WhatsApp, 1 agendada
    assert "Gratuito" in html
    assert "Cliente Um" not in admin_client.get("/admin/usuarios", params={"status": "suspended"}).text
    assert "Cliente Um" in admin_client.get("/admin/usuarios", params={"activity": "24h", "sort": "email", "dir": "asc"}).text
    assert "Cliente Um" in admin_client.get("/admin/usuarios", params={"plan": "free", "subscription": "none"}).text
    assert "Cliente Um" not in admin_client.get("/admin/usuarios", params={"plan": "plus"}).text


def test_crm_status_tags_notes_are_audited(admin_client, customer):
    page = admin_client.get(f"/admin/usuarios/{customer.id}").text
    token = _csrf(page)
    assert "Não copie conteúdo de conversas" in page  # aviso na interface
    admin_client.post(f"/admin/usuarios/{customer.id}/crm/status", data={"status": "ativo", "csrf_token": token})
    admin_client.post(f"/admin/usuarios/{customer.id}/crm/tags", data={"new_tag": "Clínica Parceira", "csrf_token": token})
    r = admin_client.post(f"/admin/usuarios/{customer.id}/crm/notas",
                          data={"body": "Pediu proposta do plano empresarial.", "csrf_token": token})
    assert r.status_code == 200 and "Nota adicionada" in r.text
    assert "Pediu proposta do plano empresarial." in r.text and "Clínica Parceira" in r.text
    # nota cifrada no banco; a auditoria guarda só o id
    assert db_locations_containing("plano empresarial") == []
    with Session(get_engine()) as db:
        actions = [a.action for a in db.exec(select(AdminAuditLog)).all()]
        assert {"crm_status_changed", "crm_tag_created", "crm_tag_added", "crm_note_added"} <= set(actions)
        note = db.exec(select(CrmNote)).one()
        assert note.created_by is not None
        assert all("empresarial" not in (a.detail or "") for a in db.exec(select(AdminAuditLog)).all())
    audit_page = admin_client.get("/admin/auditoria").text
    assert "Adicionou nota" in audit_page and "Alterou status do CRM" in audit_page


def test_crm_note_refuses_pasted_whatsapp_conversation(admin_client, customer):
    token = _csrf(admin_client.get(f"/admin/usuarios/{customer.id}").text)
    r = admin_client.post(f"/admin/usuarios/{customer.id}/crm/notas",
                          data={"body": "[29/09/2026 10:15] Fulano: oi tudo bem?", "csrf_token": token})
    assert "Parece o trecho de uma conversa" in r.text
    with Session(get_engine()) as db:
        assert db.exec(select(CrmNote)).all() == []


def test_suspend_and_reactivate(admin_client, customer, client):
    token = _csrf(admin_client.get(f"/admin/usuarios/{customer.id}").text)
    r = admin_client.post(f"/admin/usuarios/{customer.id}/suspender", data={"csrf_token": token})
    assert "Conta suspensa" in r.text
    with Session(get_engine()) as db:
        assert db.get(User, customer.id).is_active is False
        assert all(s.revoked_at for s in db.exec(select(UserSession).where(UserSession.user_id == customer.id)).all())
    admin_client.post(f"/admin/usuarios/{customer.id}/reativar", data={"csrf_token": token})
    with Session(get_engine()) as db:
        assert db.get(User, customer.id).is_active is True
        assert {"user_suspended", "user_reactivated"} <= {a.action for a in db.exec(select(AdminAuditLog)).all()}


def test_admin_cannot_suspend_self(admin_client):
    with Session(get_engine()) as db:
        admin = db.exec(select(User).where(User.email == "admin@example.com")).one()
    token = _csrf(admin_client.get(f"/admin/usuarios/{admin.id}").text)
    r = admin_client.post(f"/admin/usuarios/{admin.id}/suspender", data={"csrf_token": token})
    assert "não pode suspender a própria conta" in r.text


def test_manual_plan_change_is_not_revenue(admin_client, customer):
    token = _csrf(admin_client.get(f"/admin/usuarios/{customer.id}").text)
    with Session(get_engine()) as db:
        plus = plans.get_plan(db, "plus")
    r = admin_client.post(f"/admin/usuarios/{customer.id}/plano", data={"plan_id": plus.id, "csrf_token": token})
    assert "cortesia" in r.text
    with Session(get_engine()) as db:
        assert plans.current_plan(db, db.get(User, customer.id)).code == "plus"
        summary = billing_metrics.summary(db)
        assert summary.mrr_cents == 0 and summary.revenue_total_cents == 0 and summary.manual_subscriptions == 1
    assert "R$ 0,00" in admin_client.get("/admin/faturamento").text


def test_edit_plan_catalog_is_audited(admin_client):
    with Session(get_engine()) as db:
        plus = plans.get_plan(db, "plus")
    page = admin_client.get("/admin/planos", params={"edit": plus.id}).text
    token = _csrf(page)
    r = admin_client.post(f"/admin/planos/{plus.id}", data={
        "name": "Plus", "price": "39,90", "billing_period": "monthly", "description": "d", "features": "A\nB",
        "limit_whatsapp_connections": "5", "limit_pending_messages": "", "limit_calendar_connections": "2",
        "is_active": "on", "is_public": "on", "csrf_token": token,
    })
    assert "atualizado" in r.text
    with Session(get_engine()) as db:
        plus = plans.get_plan(db, "plus")
        assert plus.price_cents == 3990 and plans.limits(plus)["pending_messages"] is None
        assert plans.features(plus) == ["A", "B"]
        assert db.exec(select(AdminAuditLog).where(AdminAuditLog.action == "plan_updated")).first() is not None


def test_logins_page_lists_success_and_failure_without_ip(admin_client, customer):
    from whatsapp_scheduler.models import AuditEventType, LoginAuditEvent

    with Session(get_engine()) as db:
        db.add(LoginAuditEvent(user_id=customer.id, event_type=AuditEventType.login_success, ip_address="198.51.100.7"))
        db.add(LoginAuditEvent(user_id=customer.id, event_type=AuditEventType.login_failed, ip_address="198.51.100.7"))
        db.commit()
    html = admin_client.get("/admin/logins").text
    assert "falhou" in html and "sucesso" in html and "cliente@example.com" in html
    assert "198.51.100.7" not in html  # IP não aparece no admin


def test_dashboard_counts_do_not_need_content(admin_client, customer):
    admin_client.waha.listed = []
    html = admin_client.get("/admin").text
    assert "Total de usuários" in html and "Mensagens agendadas" in html and "MRR" in html
    assert "Nenhum pagamento registrado" in html
