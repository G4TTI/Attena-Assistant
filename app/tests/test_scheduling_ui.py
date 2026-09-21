"""Telas de Agendamentos, Conversas e Calendário sobre o modelo único: formulário limpo, seletores
compartilhados, horário preservado, mensagens dentro da conversa, intervalo personalizado e o
fluxo completo (contato -> WhatsApp -> horário -> mensagens -> job -> envio -> conversa)."""

import asyncio
import re
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from tests.conftest import FakeWaha, register_and_login, whatsapp_session_id
from whatsapp_scheduler import calendar_service, calendar_sync, crypto, timing
from whatsapp_scheduler.calendar_providers.base import OAuthTokens, RemoteEvent
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.config import settings
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import (
    Automation,
    Calendar,
    CalendarConnection,
    CalendarConnectionStatus,
    CachedMessage,
    Dispatch,
    Event,
    EventSource,
    Schedule,
    ScheduleGroup,
    ScheduleSource,
    WhatsAppSession,
)
from whatsapp_scheduler.scheduler import SchedulerService

TZ = "America/Sao_Paulo"
LEO = "5514991110001@c.us"
GUI = "5511982220002@c.us"
PIC = "data:image/png;base64,iVBORw0KGgo="
CHATS = [
    {"id": LEO, "name": "Leonardo Silva", "picture": PIC, "lastMessage": {"body": "oi", "timestamp": 1_800_000_000, "fromMe": False}},
    {"id": GUI, "name": "Guilherme Souza", "picture": None, "lastMessage": {"body": "blz", "timestamp": 1_800_000_100, "fromMe": True}},
]


@pytest.fixture
def client():
    waha = FakeWaha()
    waha.chats = CHATS
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        c.user = register_and_login(c)
        yield c


def _groups() -> list[ScheduleGroup]:
    with Session(get_engine()) as db:
        return list(db.exec(select(ScheduleGroup).order_by(col(ScheduleGroup.created_at))).all())


def _schedules(group_id: str | None = None) -> list[Schedule]:
    with Session(get_engine()) as db:
        q = select(Schedule).order_by(col(Schedule.group_id), col(Schedule.position))
        if group_id:
            q = q.where(col(Schedule.group_id) == group_id)
        return list(db.exec(q).all())


def _form(**overrides) -> dict:
    data = {
        "recipients": [LEO], "recipient_names": ["Leonardo Silva"],
        "messages": ["Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."],
        "whatsapp_session_id": "", "send_date": "2999-09-20", "send_time": "18:00", "recurrence": "",
    }
    data.update(overrides)
    return data


def _second_whatsapp(client) -> WhatsAppSession:
    with Session(get_engine()) as db:
        wa = WhatsAppSession(user_id=client.user.id, name="WhatsApp Trabalho")
        db.add(wa)
        db.commit()
        db.refresh(wa)
        return wa


# --------------------------------------------------------------------------- #
# Agendamentos: formulário limpo
# --------------------------------------------------------------------------- #
def test_agendamentos_form_is_clean_and_uses_shared_components(client):
    html = client.get("/agendamentos").text
    for expected in ("Destinatário", "Primeiro envio", "Enviar através de", "Mensagens", "Adicionar mensagem",
                     "Opções avançadas", 'class="contact-picker"', 'class="wa-picker"', 'name="send_date"',
                     'name="send_time"', "Fuso horário: São Paulo", "Resumo"):
        assert expected in html, expected
    # Parte 4: timezone e tentativas NÃO são campos do formulário
    assert 'name="timezone"' not in html and 'name="max_attempts"' not in html
    assert "Tentativas" not in html
    # recorrência só dentro das opções avançadas
    assert html.index("Opções avançadas") < html.index('name="recurrence"')
    # o destinatário deixou de ser um campo de texto livre
    assert 'id="recipient"' not in html


def test_create_multi_message_schedule_keeps_the_typed_time(client):
    """Testes 1-3 pela tela: hora digitada = hora gravada; 3 mensagens no mesmo agendamento."""
    r = client.post("/ui/schedules", data=_form(whatsapp_session_id=whatsapp_session_id(client)))
    assert r.status_code == 200 and "Agendamento criado." in r.text
    (group,) = _groups()
    assert (group.start_local, group.timezone, group.source, group.recipient_name) == (
        datetime(2999, 9, 20, 18, 0), TZ, ScheduleSource.manual, "Leonardo Silva")
    rows = _schedules(group.id)
    assert [s.text for s in rows] == ["Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."]
    assert rows[0].first_run_local == datetime(2999, 9, 20, 18, 0)
    # o formulário devolvido mantém data, horário e WhatsApp (nada volta pra "agora"/vazio/00:00)
    assert 'value="2999-09-20"' in r.text and 'value="18:00"' in r.text
    # e a lista já mostra o agendamento limpo
    assert "20/09/2999 · 18:00" in r.text and "3 mensagens" in r.text and "Agendado" in r.text


def test_manual_number_and_contact_are_accepted_and_duplicates_collapse(client):
    """Teste 9 + Parte 5: número manual aceito; contato + o mesmo número digitado = 1 agendamento só."""
    r = client.post("/ui/schedules", data=_form(
        recipients=[LEO, "+55 14 99111-0001", "+55 11 98222-0002"],
        recipient_names=["Leonardo Silva", "+55 14 99111-0001", "+55 11 98222-0002"], messages=["oi"]))
    assert r.status_code == 200 and "2 agendamentos criados" in r.text
    assert sorted(g.chat_id for g in _groups()) == sorted([LEO, GUI])


def test_error_keeps_everything_the_user_typed(client):
    wa_id = whatsapp_session_id(client)
    r = client.post("/ui/schedules", data=_form(
        recipients=[LEO], recipient_names=["Leonardo Silva"], messages=["primeira", "segunda"],
        send_date="2999-09-20", send_time="", whatsapp_session_id=wa_id))
    assert "Informe a data e o horário" in r.text
    assert "primeira" in r.text and "segunda" in r.text and 'value="2999-09-20"' in r.text
    assert 'name="recipients" value="' + LEO + '"' in r.text
    assert _groups() == []

    empty = client.post("/ui/schedules", data=_form(recipients=[], recipient_names=[]))
    assert "Selecione ao menos um destinatário" in empty.text

    past = client.post("/ui/schedules", data=_form(send_date="2001-01-01"))
    assert "já passou" in past.text and _groups() == []


def test_recurrence_allowed_for_one_message_but_not_for_a_sequence(client):
    ok = client.post("/ui/schedules", data=_form(messages=["oi"], recurrence="daily 09:00"))
    assert "Agendamento criado." in ok.text
    bad = client.post("/ui/schedules", data=_form(recurrence="daily 09:00"))
    assert "única mensagem" in bad.text
    assert len(_groups()) == 1


def test_schedule_goes_through_the_whatsapp_selected_in_the_form(client):
    """Teste 10 pela tela."""
    wa_b = _second_whatsapp(client)
    client.post("/ui/schedules", data=_form(whatsapp_session_id=wa_b.id, messages=["pelo B"]))
    (group,) = _groups()
    assert group.session == wa_b.session_name
    assert {s.session for s in _schedules(group.id)} == {wa_b.session_name}


# --------------------------------------------------------------------------- #
# WhatsApp: só os do usuário, status, desconectado
# --------------------------------------------------------------------------- #
def test_picker_lists_only_own_sessions_with_live_status(client):
    other = register_second_user(client)
    html = client.get("/ui/whatsapp-picker-options").text
    assert html.count("<option") == 1 and "WhatsApp" in html and "🟢" in html
    assert other["session_name"] not in html and other["name"] not in html


def register_second_user(client) -> dict:
    """Cria (direto no banco) outro usuário com um WhatsApp — pra provar que nunca aparece pro primeiro."""
    from whatsapp_scheduler.auth import hash_password
    from whatsapp_scheduler.models import User

    with Session(get_engine()) as db:
        user = User(name="Outro", email="outro@example.com", password_hash=hash_password("x" * 12))
        db.add(user)
        db.commit()
        db.refresh(user)
        wa = WhatsAppSession(user_id=user.id, name="WhatsApp do Outro")
        db.add(wa)
        db.commit()
        db.refresh(wa)
        return {"id": wa.id, "name": wa.name, "session_name": wa.session_name, "user_id": user.id}


def test_disconnected_whatsapp_is_flagged_and_blocks_scheduling(client):
    """Teste 11: alerta ANTES do agendamento — nada é criado."""
    client.waha.status = "SCAN_QR_CODE"
    options = client.get("/ui/whatsapp-picker-options").text
    assert "🔴" in options and 'data-level="err"' in options and "Nenhum dos seus WhatsApps está conectado" in options
    r = client.post("/ui/schedules", data=_form(whatsapp_session_id=whatsapp_session_id(client)))
    assert "desconectado" in r.text and "Reconecte" in r.text
    assert _groups() == []
    client.waha.status = "WORKING"
    assert "Agendamento criado." in client.post("/ui/schedules", data=_form()).text


def test_cannot_schedule_through_another_users_whatsapp(client):
    other = register_second_user(client)
    r = client.post("/ui/schedules", data=_form(whatsapp_session_id=other["id"]))
    assert "Conecte um WhatsApp" in r.text or "Escolha" in r.text
    assert _groups() == []


# --------------------------------------------------------------------------- #
# Detalhe / edição / cancelamento + isolamento (Teste 12)
# --------------------------------------------------------------------------- #
def _create_group(client, **overrides) -> ScheduleGroup:
    before = {g.id for g in _groups()}
    client.post("/ui/schedules", data=_form(**overrides))
    return next(g for g in _groups() if g.id not in before)


def test_detail_edit_and_cancel_flow(client):
    group = _create_group(client)
    detail = client.get(f"/ui/schedules/{group.id}").text
    for expected in ("20/09/2999 às 18:00", "Fuso horário: São Paulo", "Leonardo Silva", "Olá Leonardo!", "18:00:03",
                     "18:00:06", "Agendado", "Editar", "Cancelar"):
        assert expected in detail, expected

    edit_form = client.get(f"/ui/schedules/{group.id}/edit").text
    assert 'value="18:00"' in edit_form and "Olá Leonardo!" in edit_form

    r = client.post(f"/ui/schedules/{group.id}/edit", data={
        "messages": ["Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."],
        "send_date": "2999-09-20", "send_time": "19:00", "whatsapp_session_id": whatsapp_session_id(client), "recurrence": ""})
    assert r.status_code == 200 and "19:00" in r.text and 'hx-swap-oob="true"' in r.text
    rows = _schedules(group.id)
    assert [s.first_run_local for s in rows] == [
        datetime(2999, 9, 20, 19, 0, 0), datetime(2999, 9, 20, 19, 0, 3), datetime(2999, 9, 20, 19, 0, 6)]

    r = client.post(f"/ui/schedules/{group.id}/cancel", headers={"HX-Target": "modal-root"})
    assert r.status_code == 200 and "Cancelado" in r.text
    assert not any(s.enabled for s in _schedules(group.id))
    # cancelado: não dá mais pra editar, e o detalhe explica
    assert "não pode mais ser editado" in client.get(f"/ui/schedules/{group.id}/edit").text


def test_edit_error_keeps_the_form_and_does_not_change_anything(client):
    group = _create_group(client)
    r = client.post(f"/ui/schedules/{group.id}/edit", data={
        "messages": ["novo texto"], "send_date": "2001-01-01", "send_time": "10:00",
        "whatsapp_session_id": whatsapp_session_id(client), "recurrence": ""})
    assert "já passou" in r.text and "novo texto" in r.text
    assert [s.text for s in _schedules(group.id)][0] == "Olá Leonardo!"


def test_user_a_cannot_open_edit_or_cancel_user_bs_schedule(client):
    """Teste 12."""
    group = _create_group(client)
    token_a = client.cookies.get(settings.session_cookie_name)
    client.cookies.clear()
    register_and_login(client, name="B", email="b@example.com")
    assert client.get(f"/ui/schedules/{group.id}").status_code == 404
    assert client.get(f"/ui/schedules/{group.id}/edit").status_code == 404
    r = client.post(f"/ui/schedules/{group.id}/edit", data={
        "messages": ["hack"], "send_date": "2999-01-01", "send_time": "10:00", "whatsapp_session_id": "x", "recurrence": ""})
    assert r.status_code == 404
    client.post(f"/ui/schedules/{group.id}/cancel")
    client.post(f"/ui/schedules/{group.id}/run-now")
    assert "Leonardo" not in client.get("/agendamentos").text and "Olá Leonardo!" not in client.get("/ui/schedules").text
    assert all(s.enabled for s in _schedules(group.id)) and _schedules(group.id)[0].text == "Olá Leonardo!"
    client.cookies.set(settings.session_cookie_name, token_a)
    assert client.get(f"/ui/schedules/{group.id}").status_code == 200


# --------------------------------------------------------------------------- #
# Contatos: foto / avatar (Testes 7 e 8) — mesma origem do Calendário
# --------------------------------------------------------------------------- #
def test_contacts_show_photo_when_there_is_one_and_default_avatar_otherwise(client):
    html = client.get("/ui/calendario/contacts", params={"whatsapp_session_id": whatsapp_session_id(client)}).text
    blocks = {m.group(1): m.group(0) for m in re.finditer(r'<label class="contact-option" data-name="([^"]+)".*?</label>', html, re.S)}
    leo, gui = blocks["Leonardo Silva"], blocks["Guilherme Souza"]
    assert f'src="{PIC}"' in leo and "+5514991110001" in leo          # Teste 7: foto carregada
    assert "<img" not in gui and ">G<" in gui and "+5511982220002" in gui  # Teste 8: avatar padrão (inicial), sem <img>


def test_agendamentos_uses_the_same_contact_endpoint_as_the_calendar(client):
    html = client.get("/agendamentos").text
    assert 'hx-get="/ui/calendario/contacts?whatsapp_session_id=' in html


# --------------------------------------------------------------------------- #
# Conversas: sequência, horário preservado (o bug), mensagens dentro da conversa
# --------------------------------------------------------------------------- #
def _chat_post(client, **overrides):
    sid = whatsapp_session_id(client)
    data = {"chat": LEO, "messages": ["Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."],
            "send_date": "2999-09-20", "send_time": "18:00", "recurrence": ""}
    data.update(overrides)
    return sid, client.post(f"/ui/chats/{sid}/schedule", data=data)


def test_chat_schedule_creates_one_group_with_the_whole_sequence(client):
    sid, r = _chat_post(client)
    assert r.status_code == 200 and "Agendamento criado — 3 mensagens." in r.text
    (group,) = _groups()
    assert (group.source, group.chat_id, group.start_local) == (ScheduleSource.conversation, LEO, datetime(2999, 9, 20, 18, 0))
    assert [s.position for s in _schedules(group.id)] == [0, 1, 2]
    with Session(get_engine()) as db:
        wa = db.get(WhatsAppSession, sid)
        assert group.session == wa.session_name


def test_chat_schedule_form_never_loses_the_time_after_saving(client):
    """O bug original: depois de agendar, o painel voltava com o horário atual/vazio."""
    _, r = _chat_post(client)
    pop = r.text.split('id="schedule-pop"')[1]
    assert 'value="2999-09-20"' in pop and 'value="18:00"' in pop
    # em erro, o painel volta ABERTO e com tudo o que foi digitado
    _, err = _chat_post(client, messages=["a", "b"], send_date="2001-01-01", send_time="09:15")
    pop = err.text.split('id="schedule-pop"')[1]
    assert 'value="2001-01-01"' in pop and 'value="09:15"' in pop and ">a</textarea>" in pop and ">b</textarea>" in pop
    assert "hidden" not in err.text.split('id="schedule-pop"')[1].split(">")[0]
    assert "já passou" in err.text


def test_scheduled_messages_appear_inside_the_conversation_one_bubble_each(client):
    sid, _ = _chat_post(client)
    view = client.get(f"/ui/chats/{sid}/view", params={"chat": LEO}).text
    scheduled = view.split('id="chat-scheduled"')[1].split('id="schedule-pop"')[0]
    bubbles = re.findall(r'<div class="bubble me scheduled (\w+)"', scheduled)
    assert bubbles == ["scheduled"] * 3
    for text in ("Olá Leonardo!", "Passando para lembrar da nossa avaliação.", "Nos vemos às 20h."):
        assert text in scheduled
    assert scheduled.count("20/09/2999 · 18:00") == 3 and scheduled.count("Agendada") == 3
    assert scheduled.count("cancelar") >= 3
    # e só aparecem na conversa certa
    other = client.get(f"/ui/chats/{sid}/scheduled", params={"chat": GUI}).text
    assert "Olá Leonardo!" not in other


def test_scheduled_bubbles_do_not_wait_for_the_slow_whatsapp_history(client):
    sid, _ = _chat_post(client)

    async def slow(*a, **k):
        raise AssertionError("o painel de mensagens agendadas não pode depender do histórico")

    client.waha.get_messages = slow
    assert "Olá Leonardo!" in client.get(f"/ui/chats/{sid}/scheduled", params={"chat": LEO}).text


def test_cancel_one_message_from_the_conversation(client):
    sid, _ = _chat_post(client)
    middle = _schedules()[1]
    r = client.post(f"/ui/chats/{sid}/scheduled/{middle.id}/cancel", data={"chat": LEO})
    assert r.status_code == 200
    statuses = re.findall(r'<div class="bubble me scheduled (\w+)"', r.text)
    assert statuses == ["scheduled", "canceled", "scheduled"]
    assert "Cancelada" in r.text
    assert [s.enabled for s in _schedules()] == [True, False, True]


def test_cannot_cancel_another_users_scheduled_message_from_a_chat(client):
    sid, _ = _chat_post(client)
    target = _schedules()[0]
    client.cookies.clear()
    register_and_login(client, name="B", email="b2@example.com")
    sid_b = whatsapp_session_id(client)
    client.post(f"/ui/chats/{sid_b}/scheduled/{target.id}/cancel", data={"chat": LEO})
    assert client.post(f"/ui/chats/{sid}/scheduled/{target.id}/cancel", data={"chat": LEO}).status_code == 404
    assert all(s.enabled for s in _schedules())


def test_chat_schedule_still_accepts_the_old_single_text_fields(client):
    sid = whatsapp_session_id(client)
    r = client.post(f"/ui/chats/{sid}/schedule", data={"chat": LEO, "text": "lembrete", "send_at": "2999-01-01T09:00"})
    assert "Agendamento criado." in r.text
    (group,) = _groups()
    assert group.start_local == datetime(2999, 1, 1, 9, 0) and _schedules(group.id)[0].text == "lembrete"


def test_disconnected_whatsapp_blocks_scheduling_from_a_chat(client):
    client.waha.status = "STOPPED"
    _, r = _chat_post(client)
    assert "desconectado" in r.text and _groups() == []


# --------------------------------------------------------------------------- #
# Fluxo completo: agenda -> job -> WhatsApp certo -> conversa -> histórico
# --------------------------------------------------------------------------- #
def test_end_to_end_conversation_sequence_is_sent_and_shown(client):
    """Parte 19, 1º fluxo. O horário é "agora" (minuto atual), então o job reconhece que venceu."""
    wa_b = _second_whatsapp(client)
    now_local = timing.to_local(utcnow(), TZ)
    sid = wa_b.id
    r = client.post(f"/ui/chats/{sid}/schedule", data={
        "chat": LEO, "messages": ["um", "dois", "três"], "send_date": now_local.strftime("%Y-%m-%d"),
        "send_time": now_local.strftime("%H:%M")})
    assert "Agendamento criado" in r.text
    asyncio.run(SchedulerService(client.waha).run_once())
    assert [m["text"] for m in client.waha.sent] == ["um", "dois", "três"]
    assert {m["session"] for m in client.waha.sent} == {wa_b.session_name}   # o WhatsApp escolhido, não o principal
    # A conversa mostra as mensagens (cache local, sem ir ao WAHA) marcadas como vindas de agendamento…
    hist = client.get(f"/ui/chats/{sid}/messages", params={"chat": LEO}).text
    assert hist.count("agendada") == 3 and "três" in hist
    # …e o painel de agendadas não repete (já são bolhas reais do histórico)
    assert "bubble me scheduled" not in client.get(f"/ui/chats/{sid}/scheduled", params={"chat": LEO}).text
    # Histórico/lista: o agendamento aparece como enviado
    assert "Enviado" in client.get("/ui/schedules").text
    with Session(get_engine()) as db:
        assert len(db.exec(select(CachedMessage).where(col(CachedMessage.chat_id) == LEO)).all()) == 3


# --------------------------------------------------------------------------- #
# Calendário: intervalo personalizado (Testes 5, 6, 16) e mesma experiência
# --------------------------------------------------------------------------- #
def _event(client, hour=20) -> Event:
    with Session(get_engine()) as db:
        event = Event(user_id=client.user.id, source=EventSource.internal, title="Avaliação",
                      start_utc=timing.to_utc(datetime(2999, 9, 20, hour, 0), TZ),
                      end_utc=timing.to_utc(datetime(2999, 9, 20, hour + 1, 0), TZ), timezone=TZ)
        db.add(event)
        db.commit()
        db.refresh(event)
        return event


def _preview(client, event_id, **params) -> str:
    return client.get(f"/ui/calendario/events/{event_id}/automation-preview", params=params).text


def test_preview_before_and_after_with_custom_interval(client):
    event = _event(client)
    before = _preview(client, event.id, offset_direction="before", offset_interval="custom", custom_interval="1:45")
    assert "18:15 — 20/09/2999" in before and "Antes do evento · 1h45 antes · 18:15" in before   # Teste 5
    after = _preview(client, event.id, offset_direction="after", offset_interval="custom", custom_interval="1:45")
    assert "21:45 — 20/09/2999" in after and "Depois do evento · 1h45 depois · 21:45" in after   # Teste 6
    at = _preview(client, event.id, offset_direction="at", offset_interval="custom", custom_interval="1:45")
    assert "20:00 — 20/09/2999" in at and "No momento do evento" in at
    preset = _preview(client, event.id, offset_direction="before", offset_interval="30:minutes")
    assert "19:30" in preset and "30min antes" in preset


@pytest.mark.parametrize("bad, message", [("99:99", "minutos"), ("abc", "HH:MM"), ("-1:30", "negativo"), ("0:00", "maior que 0"), ("1:5", "HH:MM")])
def test_preview_shows_a_clear_validation_error(client, bad, message):
    event = _event(client)
    html = _preview(client, event.id, offset_direction="before", offset_interval="custom", custom_interval=bad)
    assert message in html and 'id="au_custom_interval_error"' in html
    assert "hidden" not in html.split('id="au_custom_interval_error"')[1].split(">")[0]


def test_create_automation_with_custom_interval_and_edit_keeps_it(client):
    event = _event(client)
    wa_id = whatsapp_session_id(client)
    r = client.post(f"/ui/calendario/events/{event.id}/automation", data={
        "recipients": [LEO], "recipient_names": ["Leonardo Silva"], "messages": ["Lembrete", "Segunda"],
        "offset_direction": "before", "offset_interval": "custom", "custom_interval": "1:45",
        "whatsapp_session_id": wa_id, "year": 2999, "month": 9})
    assert r.status_code == 200 and 'id="calendar-grid"' in r.text
    with Session(get_engine()) as db:
        (automation,) = db.exec(select(Automation)).all()
        assert (automation.offset_amount, str(automation.offset_unit), automation.custom_interval) == (105, "minutes", "1:45")
    (group,) = _groups()
    assert (group.source, group.recipient_name) == (ScheduleSource.calendar, "Leonardo Silva")
    rows = _schedules(group.id)
    assert rows[0].first_run_local == datetime(2999, 9, 20, 18, 15) and rows[1].first_run_local == datetime(2999, 9, 20, 18, 15, 3)
    assert group.timezone == TZ and group.session == rows[0].session
    # detalhe do evento e edição mostram "Personalizado · 1:45"
    detail = client.get(f"/ui/calendario/events/{event.id}", params={"year": 2999, "month": 9}).text
    assert "Antes do evento · 1h45 antes" in detail and "18:15" in detail and "Leonardo Silva" in detail
    edit = client.get(f"/ui/calendario/automations/{automation.id}/edit", params={"year": 2999, "month": 9}).text
    assert '<option value="custom" selected>' in edit and 'value="1:45"' in edit
    assert 'value="before" selected' in edit


def test_automation_invalid_custom_interval_keeps_the_form_filled(client):
    event = _event(client)
    r = client.post(f"/ui/calendario/events/{event.id}/automation", data={
        "recipients": [LEO], "recipient_names": ["Leonardo Silva"], "messages": ["Meu texto"],
        "offset_direction": "before", "offset_interval": "custom", "custom_interval": "99:99",
        "whatsapp_session_id": whatsapp_session_id(client), "year": 2999, "month": 9})
    assert "Os minutos devem estar entre 00 e 59" in r.text
    assert "Meu texto" in r.text and 'value="99:99"' in r.text and "Leonardo Silva" in r.text
    assert _groups() == []


def test_automation_blocked_when_whatsapp_is_disconnected(client):
    event = _event(client)
    client.waha.status = "SCAN_QR_CODE"
    r = client.post(f"/ui/calendario/events/{event.id}/automation", data={
        "recipients": [LEO], "messages": ["x"], "offset_direction": "before", "offset_interval": "1:hours",
        "whatsapp_session_id": whatsapp_session_id(client), "year": 2999, "month": 9})
    assert "desconectado" in r.text and _groups() == []


def test_calendar_and_schedule_forms_share_the_same_components(client):
    event = _event(client)
    modal = client.get(f"/ui/calendario/events/{event.id}/automation/new", params={"year": 2999, "month": 9}).text
    page = client.get("/agendamentos").text
    for marker in ('class="contact-picker"', 'class="wa-picker"', 'class="message-composer"', "Adicionar mensagem"):
        assert marker in modal and marker in page, marker
    assert "Personalizado…" in modal and "Horário fixo no dia do evento" in modal


def test_automation_custom_interval_via_api(client):
    event = _event(client)
    r = client.post(f"/api/calendar/events/{event.id}/automations", json={
        "recipients": ["+55 14 99111-0001"], "messages": ["oi"], "offset_amount": 0, "offset_unit": "minutes",
        "offset_direction": "after", "custom_interval": "1:45", "whatsapp_session_id": whatsapp_session_id(client)})
    assert r.status_code == 201 and r.json()["custom_interval"] == "1:45"
    (group,) = _groups()
    assert _schedules(group.id)[0].first_run_local == datetime(2999, 9, 20, 21, 45)
    bad = client.post(f"/api/calendar/events/{event.id}/automations", json={
        "recipients": ["+55 14 99111-0001"], "messages": ["oi"], "offset_amount": 0, "offset_unit": "minutes",
        "offset_direction": "after", "custom_interval": "99:99", "whatsapp_session_id": whatsapp_session_id(client)})
    assert bad.status_code == 422


# --------------------------------------------------------------------------- #
# Fluxo completo do Calendário: evento Google -> automação -> regra personalizada -> WhatsApp
# --------------------------------------------------------------------------- #
async def test_end_to_end_google_event_custom_rule_to_whatsapp(db, test_user, fake_google, fake_waha, monkeypatch):
    """Parte 19, 2º fluxo: 20:00, "1:45 antes" => 18:15, pela sessão escolhida, na ordem, com o horário exibido = o real."""
    frozen = datetime(2026, 9, 20, 20, 0, 0)  # 17:00 em São Paulo
    monkeypatch.setattr("whatsapp_scheduler.clock.utcnow", lambda: frozen)
    conn = CalendarConnection(user_id=test_user.id, provider="google", account_identifier="u@example.com",
                              access_token_enc=crypto.encrypt("a"), refresh_token_enc=crypto.encrypt("r"),
                              token_expires_at=frozen + timedelta(hours=1), status=CalendarConnectionStatus.active)
    db.add(conn)
    db.commit()
    cal = Calendar(connection_id=conn.id, external_id="primary", name="Agenda", time_zone=TZ, enabled=True)
    db.add(cal)
    db.commit()
    start_utc = timing.to_utc(datetime(2026, 9, 20, 20, 0), TZ)  # evento às 20:00 locais
    fake_google.events_by_calendar["primary"] = [RemoteEvent(
        external_id="g1", title="Avaliação", description="", start_utc=start_utc, end_utc=start_utc + timedelta(hours=1),
        timezone=TZ, all_day=False, cancelled=False)]
    tokens = OAuthTokens(access_token="a", refresh_token="r", expires_at=frozen + timedelta(hours=1))
    await calendar_sync.sync_calendar(db, fake_google, tokens, cal, conn.user_id)
    event = db.exec(select(Event).where(col(Event.external_id) == "g1")).one()

    rule = timing.build_offset_rule("before", "custom", "1:45")
    calendar_service.create_event_automation(
        db, event_id=event.id, user_id=test_user.id, waha_session=test_user.waha_session, recipients=[LEO],
        recipient_names=["Leonardo Silva"], messages=["Lembrete 1", "Lembrete 2"], offset_amount=rule.amount,
        offset_unit=rule.unit, offset_direction=rule.direction, custom_interval=rule.custom_interval, timezone_name=TZ)
    group = db.exec(select(ScheduleGroup)).one()
    assert (group.source, group.start_local) == (ScheduleSource.calendar, datetime(2026, 9, 20, 18, 15))
    first = db.exec(select(Dispatch).join(Schedule, col(Dispatch.schedule_id) == col(Schedule.id))
                    .where(col(Schedule.group_id) == group.id).where(col(Schedule.position) == 0)).one()
    assert first.scheduled_at_utc == datetime(2026, 9, 20, 21, 15)   # 18:15 em SP

    # Google remarca o evento: o mesmo agendamento acompanha (sem duplicar), preservando a regra "1h45 antes"
    moved = start_utc + timedelta(hours=1)  # 21:00 locais
    fake_google.events_by_calendar["primary"] = [RemoteEvent(
        external_id="g1", title="Avaliação", description="", start_utc=moved, end_utc=moved + timedelta(hours=1),
        timezone=TZ, all_day=False, cancelled=False)]
    await calendar_sync.sync_calendar(db, fake_google, tokens, cal, conn.user_id)
    db.expire_all()
    group = db.exec(select(ScheduleGroup)).one()
    assert group.start_local == datetime(2026, 9, 20, 19, 15)
    assert len(db.exec(select(ScheduleGroup)).all()) == 1 and len(db.exec(select(Schedule)).all()) == 2

    # O horário chegou: o job envia as 2 na ordem, pela sessão da automação
    monkeypatch.setattr("whatsapp_scheduler.clock.utcnow", lambda: datetime(2026, 9, 20, 22, 30, 0))  # 19:30 locais
    await SchedulerService(fake_waha).run_once()
    assert [m["text"] for m in fake_waha.sent] == ["Lembrete 1", "Lembrete 2"]
    assert {m["session"] for m in fake_waha.sent} == {test_user.waha_session}


# --------------------------------------------------------------------------- #
# Auditoria: achados que viraram teste
# --------------------------------------------------------------------------- #
def test_double_submit_of_the_form_creates_one_schedule(client):
    data = _form(whatsapp_session_id=whatsapp_session_id(client))
    client.post("/ui/schedules", data=data)
    r = client.post("/ui/schedules", data=data)
    assert r.status_code == 200 and "Agendamento criado." in r.text
    assert len(_groups()) == 1 and len(_schedules()) == 3
    sid, _ = _chat_post(client)
    _chat_post(client)
    assert len([g for g in _groups() if g.source == ScheduleSource.conversation]) == 1


def test_extreme_date_from_the_form_is_a_message_not_a_500(client):
    for date in ("0001-01-01", "9999-12-31"):
        r = client.post("/ui/schedules", data=_form(send_date=date))
        assert r.status_code == 200 and "intervalo aceito" in r.text
    assert _groups() == []
    assert client.post("/api/schedules", json={"recipient": "5511999998888", "text": "x",
                                                "send_at": "9999-12-31T23:59:00"}).status_code == 422


def test_recipient_cap_per_submit(client):
    numbers = [f"+55 11 9{n:04d}-0000" for n in range(51)]
    r = client.post("/ui/schedules", data=_form(recipients=numbers, recipient_names=numbers, messages=["oi"]))
    assert "No máximo 50" in r.text and _groups() == []


def test_removed_whatsapp_is_rejected_by_the_form(client):
    wa_id = whatsapp_session_id(client)
    with Session(get_engine()) as db:
        wa = db.get(WhatsAppSession, wa_id)
        wa.disconnected_at = utcnow()
        db.add(wa)
        db.commit()
    r = client.post("/ui/schedules", data=_form(whatsapp_session_id=wa_id))
    assert "foi desconectado" in r.text and _groups() == []


def test_run_now_from_the_detail_moves_the_whole_group(client):
    group = _create_group(client)
    client.post(f"/ui/schedules/{group.id}/run-now", headers={"HX-Target": "modal-root"})
    rows = _schedules(group.id)
    now_local = timing.to_local(utcnow(), TZ)
    assert all(abs((s.first_run_local - now_local).total_seconds()) < 60 for s in rows)
    with Session(get_engine()) as db:
        pending = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == rows[0].id)).one()
        assert timing.to_local(pending.scheduled_at_utc, TZ).date() == now_local.date()
