"""Conversas com muitas mensagens programadas: até 4 aparecem uma a uma, 5 ou mais viram um botão
("Ver mensagens programadas"), canceladas não poluem a conversa e ficam no painel "Mensagens
programadas" (filtros, contadores, ordem da sequência, paginação, cancelar uma / todas,
atualização e isolamento entre usuários). Os testes 1-14 são os do pedido, na mesma numeração."""

import asyncio
import re
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from tests.conftest import FakeWaha, register_and_login, whatsapp_session_id
from whatsapp_scheduler import schedule_views, timing
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import (
    Automation,
    AutomationMessage,
    AutomationSchedule,
    Dispatch,
    DispatchStatus,
    Event,
    EventSource,
    OffsetDirection,
    OffsetUnit,
    Schedule,
    ScheduleSource,
    WhatsAppSession,
)
from whatsapp_scheduler.scheduler import SchedulerService
from whatsapp_scheduler.service import cancel_group, create_sequence

TZ = "America/Sao_Paulo"
LEO = "5514991110001@c.us"
GUI = "5511982220002@c.us"
CHATS = [
    {"id": LEO, "name": "Leonardo Silva", "picture": None, "lastMessage": {"body": "oi", "timestamp": 1_800_000_000}},
    {"id": GUI, "name": "Guilherme Souza", "picture": None, "lastMessage": {"body": "blz", "timestamp": 1_800_000_100}},
]
FUTURE = datetime(2999, 9, 20, 18, 0)


@pytest.fixture
def client():
    waha = FakeWaha()
    waha.chats = CHATS
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        c.user = register_and_login(c)
        c.sid = whatsapp_session_id(c)
        yield c


# --------------------------------------------------------------------------- #
# Ajudantes
# --------------------------------------------------------------------------- #
def _session_name(sid: str) -> str:
    with Session(get_engine()) as db:
        return db.get(WhatsAppSession, sid).session_name


def _seq(client, n: int, *, chat=LEO, start=FUTURE, prefix="msg", source=ScheduleSource.conversation) -> str:
    """Cria um agendamento (sequência de `n` mensagens) direto pelo serviço de sempre; devolve o id."""
    with Session(get_engine()) as db:
        group, _ = create_sequence(
            db, user_id=client.user.id, session=_session_name(client.sid), recipient=chat,
            messages=[f"{prefix} {i + 1}" for i in range(n)], start=start, timezone=TZ, source=source,
        )
        return group.id


def _cancel(client, group_id: str) -> None:
    with Session(get_engine()) as db:
        assert cancel_group(db, group_id, user_id=client.user.id)


def _conversation(client, chat=LEO) -> str:
    return client.get(f"/ui/chats/{client.sid}/scheduled", params={"chat": chat}).text


def _panel(client, chat=LEO, **params) -> str:
    return client.get(f"/ui/chats/{client.sid}/scheduled/panel", params={"chat": chat, **params}).text


def _panel_list(client, chat=LEO, **params) -> str:
    return client.get(f"/ui/chats/{client.sid}/scheduled/panel/list", params={"chat": chat, **params}).text


def _bubbles(html: str) -> list[str]:
    return re.findall(r'<div class="bubble me scheduled (\w+)"', html)


def _items(html: str) -> list[str]:
    return re.findall(r'<li class="smp-msg (\w+)"', html)


def _texts(html: str) -> list[str]:
    return re.findall(r'<span class="msg-text">([^<]*)</span>', html)


def _counter(html: str, name: str) -> int:
    match = re.search(rf'<span id="smp-n-{name}"[^>]*>(\d+)</span>', html)
    assert match, f"contador {name} ausente"
    return int(match.group(1))


def _summary_button(html: str) -> str | None:
    match = re.search(r'<button type="button" class="sched-summary".*?</button>', html, re.S)
    return match.group(0) if match else None


# --------------------------------------------------------------------------- #
# Conversa: até 4 programadas individualmente, 5+ viram um botão
# --------------------------------------------------------------------------- #
def test_1_one_scheduled_message_shows_normally(client):
    _seq(client, 1)
    conv = _conversation(client)
    assert _bubbles(conv) == ["scheduled"] and _summary_button(conv) is None


def test_2_four_scheduled_messages_show_normally(client):
    _seq(client, 4)
    conv = _conversation(client)
    assert _bubbles(conv) == ["scheduled"] * 4 and _summary_button(conv) is None
    assert [f"msg {i}" in conv for i in range(1, 5)] == [True] * 4


def test_3_five_scheduled_messages_become_one_button(client):
    _seq(client, 5)
    conv = _conversation(client)
    button = _summary_button(conv)
    assert _bubbles(conv) == [] and "msg 1" not in conv
    assert button and "Ver mensagens programadas" in button and "5 mensagens" in button
    assert 'aria-label="Ver mensagens programadas (5)"' in button
    assert "próxima 20/09/2999 · 18:00" in button


def test_4_ten_scheduled_messages(client):
    _seq(client, 5)
    _seq(client, 5, start=FUTURE + timedelta(days=1))
    button = _summary_button(_conversation(client))
    assert button and "10 mensagens" in button and "(10)" in button


def test_5_ten_scheduled_plus_twenty_canceled_do_not_pollute(client):
    _seq(client, 10)
    _cancel(client, _seq(client, 20, prefix="cancelada"))
    conv = _conversation(client)
    assert "(10)" in _summary_button(conv) and "(30)" not in conv
    assert _bubbles(conv) == [] and "cancelada 1" not in conv
    assert "Ver mensagens canceladas" not in conv  # o botão já leva ao painel
    panel = _panel(client)
    assert (_counter(panel, "scheduled"), _counter(panel, "canceled")) == (10, 20)


def test_6_zero_scheduled_ten_canceled_do_not_pollute(client):
    _cancel(client, _seq(client, 10))
    conv = _conversation(client)
    assert _bubbles(conv) == [] and _summary_button(conv) is None
    assert "Ver mensagens programadas" not in conv
    assert "Ver mensagens canceladas (10)" in conv  # só a indicação discreta
    # Cancelamento antigo: nem a indicação aparece mais (o painel continua tendo o histórico).
    with Session(get_engine()) as db:
        db.exec(sa_update(Schedule).values(updated_at=utcnow() - timedelta(days=10)))
        db.commit()
    conv = _conversation(client)
    assert "Ver mensagens canceladas" not in conv and _bubbles(conv) == []
    assert _counter(_panel(client), "canceled") == 10


def test_few_scheduled_plus_many_canceled(client):
    """Item 23: 3 programadas + 20 canceladas -> as 3 normalmente e só um acesso secundário."""
    _seq(client, 3)
    _cancel(client, _seq(client, 20, prefix="cancelada"))
    conv = _conversation(client)
    assert _bubbles(conv) == ["scheduled"] * 3 and "cancelada 1" not in conv
    assert _summary_button(conv) is None and conv.count("Ver mensagens canceladas (20)") == 1


def test_failed_messages_stay_in_the_conversation_even_when_collapsed(client):
    """Falha é relevante (histórico real): continua como bolha; só as programadas viram o botão."""
    _seq(client, 5)
    failed_group = _seq(client, 1, prefix="falhou", start=FUTURE - timedelta(days=1))
    with Session(get_engine()) as db:
        (schedule,) = db.exec(select(Schedule).where(col(Schedule.group_id) == failed_group)).all()
        dispatch = db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule.id)).one()
        dispatch.status, dispatch.scheduled_at_utc, dispatch.last_error = DispatchStatus.failed, utcnow(), "sem conexão"
        schedule.enabled = False
        db.add_all([dispatch, schedule])
        db.commit()
    conv = _conversation(client)
    assert _bubbles(conv) == ["failed"] and "sem conexão" in conv and "(5)" in _summary_button(conv)


# --------------------------------------------------------------------------- #
# Painel "Mensagens programadas"
# --------------------------------------------------------------------------- #
def test_7_button_opens_the_panel(client):
    _seq(client, 5)
    client.get(f"/ui/chats/{client.sid}/view", params={"chat": LEO})  # como na tela: a lista de conversas carrega antes
    conv = _conversation(client)
    url = re.search(r'class="sched-summary".*?hx-get="([^"]+)"', conv, re.S).group(1).replace("&amp;", "&")
    panel = client.get(url).text
    assert 'role="dialog"' in panel and "Mensagens programadas" in panel
    assert '<p class="sub smp-contact">Leonardo Silva</p>' in panel
    assert _items(panel) == ["scheduled"] * 5


def test_8_default_filter_shows_only_scheduled(client):
    _seq(client, 5)
    _cancel(client, _seq(client, 2, prefix="cancelada"))
    panel = _panel(client)
    assert re.search(r'name="scheduled" value="1" checked', panel)
    assert re.search(r'name="canceled" value="1" >', panel)  # desmarcado
    assert _items(panel) == ["scheduled"] * 5 and "cancelada 1" not in panel
    # O acesso "Ver mensagens canceladas" abre com o filtro de canceladas.
    only_canceled = _panel(client, canceled=1)
    assert _items(only_canceled) == ["canceled"] * 2
    assert re.search(r'name="scheduled" value="1" >', only_canceled)


def test_9_both_filters_show_both(client):
    _seq(client, 5)
    _cancel(client, _seq(client, 2, prefix="cancelada"))
    html = _panel_list(client, scheduled=1, canceled=1)
    assert sorted(_items(html)) == ["canceled"] * 2 + ["scheduled"] * 5


def test_10_only_canceled_and_no_filter(client):
    _seq(client, 5)
    _cancel(client, _seq(client, 2, prefix="cancelada"))
    html = _panel_list(client, canceled=1)
    assert _items(html) == ["canceled"] * 2 and _texts(html) == ["cancelada 1", "cancelada 2"]
    assert "Cancelada" in html
    assert 'class="sched-cancel"' not in html and "Cancelar todas" not in html  # cancelada não cancela de novo
    empty = _panel_list(client)
    assert _items(empty) == [] and "Selecione pelo menos um filtro para visualizar as mensagens." in empty
    assert (_counter(empty, "scheduled"), _counter(empty, "canceled")) == (5, 2)


def test_11_cancel_one_message_from_the_panel_updates_counters_and_conversation(client):
    gid = _seq(client, 5)
    with Session(get_engine()) as db:
        third = db.exec(select(Schedule).where(col(Schedule.group_id) == gid, col(Schedule.position) == 2)).one()
    assert _summary_button(_conversation(client))
    r = client.post(f"/ui/chats/{client.sid}/scheduled/panel/messages/{third.id}/cancel",
                    data={"chat": LEO, "scheduled": 1, "canceled": 0, "limit": 30})
    assert r.status_code == 200
    assert _items(r.text) == ["scheduled"] * 4 and _texts(r.text) == ["msg 1", "msg 2", "msg 4", "msg 5"]
    assert (_counter(r.text, "scheduled"), _counter(r.text, "canceled")) == (4, 1)
    # A conversa por trás do painel volta sozinha às bolhas (5 -> 4) na mesma resposta.
    oob = r.text.split('<div id="chat-scheduled" hx-swap-oob="innerHTML">')[1]
    assert _bubbles(oob) == ["scheduled"] * 4 and _summary_button(oob) is None
    assert "Ver mensagens canceladas (1)" in oob


def test_cancel_all_from_the_panel_uses_the_existing_group_cancel(client):
    gid = _seq(client, 5)
    other = _seq(client, 5, start=FUTURE + timedelta(days=2), prefix="outra")
    panel = _panel(client)
    assert panel.count("Cancelar todas") == 2
    assert "Deseja cancelar todas as mensagens programadas desta sequência?" in panel
    assert ">Cancelar</button>" in panel and "Confirmar cancelamento" in panel
    assert "data-hold-poll hidden" in panel  # confirmação fechada até clicar
    r = client.post(f"/ui/chats/{client.sid}/scheduled/panel/groups/{gid}/cancel",
                    data={"chat": LEO, "scheduled": 1, "canceled": 1, "limit": 30})
    assert r.status_code == 200
    assert _items(r.text) == ["scheduled"] * 5 + ["canceled"] * 5  # a outra sequência continua valendo
    assert _texts(r.text)[:5] == [f"outra {i}" for i in range(1, 6)]
    assert (_counter(r.text, "scheduled"), _counter(r.text, "canceled")) == (5, 5)
    with Session(get_engine()) as db:
        rows = db.exec(select(Schedule.group_id, Schedule.enabled)).all()
    assert {(g, e) for g, e in rows} == {(gid, False), (other, True)}


def test_cancel_all_only_for_sequences_with_more_than_one_pending(client):
    _seq(client, 1)
    panel = _panel(client)
    assert "Cancelar todas" not in panel and ">Cancelar</button>" in panel


def test_12_sent_message_leaves_the_count_and_appears_in_history(client):
    _seq(client, 5)
    now_local = timing.to_local(utcnow(), TZ)
    _seq(client, 1, start=now_local, prefix="agora")
    before = _conversation(client)
    assert "(6)" in _summary_button(before) and 'data-last-sent="0"' in before
    asyncio.run(SchedulerService(client.waha).run_once())
    assert [m["text"] for m in client.waha.sent] == ["agora 1"]
    after = _conversation(client)
    assert "(5)" in _summary_button(after) and _bubbles(after) == []
    assert int(re.search(r'data-last-sent="(\d+)"', after).group(1)) > 0  # a tela recarrega o histórico
    assert "agora 1" not in _panel_list(client, scheduled=1, canceled=1)  # enviada não vai pro painel
    hist = client.get(f"/ui/chats/{client.sid}/messages", params={"chat": LEO}).text
    assert "agora 1" in hist and hist.count("agendada") == 1


def test_13_new_schedule_increases_the_counter(client):
    _seq(client, 4)
    assert _summary_button(_conversation(client)) is None
    r = client.post(f"/ui/chats/{client.sid}/schedule", data={
        "chat": LEO, "messages": ["mais uma"], "send_date": "2999-09-21", "send_time": "09:00"})
    assert "Agendamento criado." in r.text
    assert "(5)" in _summary_button(r.text.split('id="chat-scheduled"')[1])


def test_14_sequence_order_and_real_times_in_the_panel(client):
    _seq(client, 5, start=FUTURE + timedelta(days=1), prefix="depois")
    _seq(client, 5)
    panel = _panel(client)
    assert _texts(panel) == [f"msg {i}" for i in range(1, 6)] + [f"depois {i}" for i in range(1, 6)]
    assert re.findall(r'<span class="msg-num"[^>]*>(\d+)</span>', panel) == [str(i) for i in range(1, 6)] * 2
    gap = timing.DEFAULT_MESSAGE_GAP_SECONDS
    expected = [(FUTURE + timedelta(seconds=gap * i)).strftime("20/09/2999 · %H:%M:%S") for i in range(5)]
    assert re.findall(r'class="when"[^>]*>([^<]+)<', panel)[:5] == expected
    assert "Agendamento · 20/09/2999 · 18:00" in panel and "Conversa · 5 mensagens" in panel


def test_canceled_message_keeps_its_place_and_time_in_the_sequence(client):
    gid = _seq(client, 5)
    with Session(get_engine()) as db:
        second = db.exec(select(Schedule).where(col(Schedule.group_id) == gid, col(Schedule.position) == 1)).one()
    client.post(f"/ui/chats/{client.sid}/scheduled/panel/messages/{second.id}/cancel", data={"chat": LEO})
    html = _panel_list(client, scheduled=1, canceled=1)
    assert _items(html) == ["scheduled", "canceled", "scheduled", "scheduled", "scheduled"]
    gap = timing.DEFAULT_MESSAGE_GAP_SECONDS
    assert (FUTURE + timedelta(seconds=gap)).strftime("20/09/2999 · %H:%M:%S") in html


def test_panel_orders_pending_first_then_canceled_most_recent_first(client):
    _cancel(client, _seq(client, 1, start=FUTURE - timedelta(days=30), prefix="velha"))
    _cancel(client, _seq(client, 1, start=FUTURE - timedelta(days=1), prefix="recente"))
    _seq(client, 1, start=FUTURE + timedelta(days=5), prefix="depois")
    _seq(client, 1, start=FUTURE, prefix="antes")
    html = _panel_list(client, scheduled=1, canceled=1)
    assert _texts(html) == ["antes 1", "depois 1", "recente 1", "velha 1"]


def test_panel_pages_whole_sequences_and_keeps_the_state_on_refresh(client):
    for day in range(3):
        _seq(client, 20, start=FUTURE + timedelta(days=day), prefix=f"dia{day}")
    first = _panel(client)
    assert len(_items(first)) == 40 and _texts(first)[-1] == "dia1 20"  # sequências inteiras, nunca cortadas
    more = re.search(r'class="ghost smp-more"\s+hx-get="([^"]+)"', first).group(1).replace("&amp;", "&")
    assert "limit=60" in more
    second = client.get(more).text
    assert len(_items(second)) == 60 and "Carregar mais" not in second
    poll = re.search(r'<div id="smp-list"[^>]*hx-get="([^"]+)"', second).group(1)
    assert "limit=60" in poll and "scheduled=1" in poll and "canceled=0" in poll
    assert _counter(second, "scheduled") == 60


def test_calendar_automation_messages_follow_the_same_rule(client):
    """Item 36: evento "Consulta Leonardo", automação 2h antes com 5 mensagens."""
    with Session(get_engine()) as db:
        event = Event(user_id=client.user.id, source=EventSource.internal, title="Consulta Leonardo",
                      start_utc=timing.to_utc(FUTURE + timedelta(hours=2), TZ),
                      end_utc=timing.to_utc(FUTURE + timedelta(hours=3), TZ), timezone=TZ)
        db.add(event)
        db.flush()
        automation = Automation(event_id=event.id, offset_amount=2, offset_unit=OffsetUnit.hours,
                                offset_direction=OffsetDirection.before)
        db.add(automation)
        db.flush()
        group, schedules = create_sequence(
            db, user_id=client.user.id, session=_session_name(client.sid), recipient=LEO,
            messages=[f"lembrete {i}" for i in range(1, 6)], start=FUTURE, timezone=TZ, source=ScheduleSource.calendar,
        )
        for s in schedules:
            message = AutomationMessage(automation_id=automation.id, position=s.position, text=s.text)
            db.add(message)
            db.flush()
            db.add(AutomationSchedule(automation_id=automation.id, message_id=message.id, schedule_id=s.id,
                                      recipient_chat_id=LEO))
        db.commit()
    assert "(5)" in _summary_button(_conversation(client))
    panel = _panel(client)
    assert _texts(panel) == [f"lembrete {i}" for i in range(1, 6)]
    assert "Calendário · Consulta Leonardo · 5 mensagens" in panel


def test_manual_schedules_follow_the_same_rule(client):
    """Item 37: tela Agendamentos, mesmo comportamento."""
    r = client.post("/ui/schedules", data={
        "recipients": [LEO], "recipient_names": ["Leonardo Silva"], "messages": [f"m{i}" for i in range(5)],
        "whatsapp_session_id": client.sid, "send_date": "2999-09-20", "send_time": "18:00"})
    assert "Agendamento criado." in r.text
    assert "(5)" in _summary_button(_conversation(client))
    assert "Agendamentos · 5 mensagens" in _panel(client)


# --------------------------------------------------------------------------- #
# Contagem no banco == status mostrado (fonte única)
# --------------------------------------------------------------------------- #
def test_sql_status_clauses_match_message_status(db, test_user):
    """`open_clause`/`canceled_clause` contam no banco o mesmo que `message_status` decide em Python."""
    now = utcnow()
    D = DispatchStatus
    cases = [
        (True, []), (False, []), (True, [D.pending]), (True, [D.processing]), (False, [D.sent]), (True, [D.sent]),
        (False, [D.failed]), (False, [D.skipped]), (False, [D.canceled]), (False, [D.sent, D.canceled]),
        (False, [D.canceled, D.sent]), (False, [D.canceled, D.pending]), (True, [D.sent, D.pending]),
        (False, [D.failed, D.canceled]), (True, [D.canceled]),
    ]
    for i, (enabled, statuses) in enumerate(cases):
        schedule = Schedule(user_id=test_user.id, session="s", recipient_input=LEO, chat_id=LEO, text=f"c{i}",
                            timezone=TZ, first_run_local=FUTURE, enabled=enabled)
        db.add(schedule)
        db.flush()
        for j, status in enumerate(statuses):
            db.add(Dispatch(schedule_id=schedule.id, scheduled_at_utc=now + timedelta(minutes=j), status=status))
    db.commit()

    def ids(clause) -> set[str]:
        return set(db.exec(select(Schedule.id).where(clause)).all())

    open_ids, canceled_ids = ids(schedule_views.open_clause()), ids(schedule_views.canceled_clause())
    for schedule in db.exec(select(Schedule)).all():
        dispatches = list(db.exec(select(Dispatch).where(col(Dispatch.schedule_id) == schedule.id)).all())
        status, _ = schedule_views.message_status(schedule, dispatches)
        assert (schedule.id in open_ids) == (status in ("scheduled", "sending")), (schedule.text, status)
        assert (schedule.id in canceled_ids) == (status == "canceled"), (schedule.text, status)


# --------------------------------------------------------------------------- #
# Isolamento entre usuários e entre conversas
# --------------------------------------------------------------------------- #
def test_panel_never_shows_or_cancels_another_users_messages(client):
    gid = _seq(client, 5)
    sid_a = client.sid
    with Session(get_engine()) as db:
        target = db.exec(select(Schedule).where(col(Schedule.group_id) == gid)).first()
    client.cookies.clear()
    register_and_login(client, name="B", email="b-panel@example.com")
    sid_b = whatsapp_session_id(client)
    assert client.get(f"/ui/chats/{sid_a}/scheduled/panel", params={"chat": LEO}).status_code == 404
    assert client.get(f"/ui/chats/{sid_a}/scheduled/panel/list", params={"chat": LEO, "scheduled": 1}).status_code == 404
    own = client.get(f"/ui/chats/{sid_b}/scheduled/panel", params={"chat": LEO}).text
    assert _items(own) == [] and _counter(own, "scheduled") == 0
    for url in (f"/ui/chats/{sid_b}/scheduled/panel/messages/{target.id}/cancel",
                f"/ui/chats/{sid_b}/scheduled/panel/groups/{gid}/cancel",
                f"/ui/chats/{sid_a}/scheduled/panel/messages/{target.id}/cancel",
                f"/ui/chats/{sid_a}/scheduled/panel/groups/{gid}/cancel"):
        assert client.post(url, data={"chat": LEO}).status_code == 404, url
    with Session(get_engine()) as db:
        assert all(s.enabled for s in db.exec(select(Schedule)).all())


def test_panel_cancel_is_scoped_to_the_open_conversation(client):
    other_chat = _seq(client, 5, chat=GUI)
    with Session(get_engine()) as db:
        target = db.exec(select(Schedule).where(col(Schedule.group_id) == other_chat)).first()
    assert client.post(f"/ui/chats/{client.sid}/scheduled/panel/groups/{other_chat}/cancel",
                       data={"chat": LEO}).status_code == 404
    assert client.post(f"/ui/chats/{client.sid}/scheduled/panel/messages/{target.id}/cancel",
                       data={"chat": LEO}).status_code == 404
    assert _items(_panel(client)) == [] and _items(_panel(client, chat=GUI)) == ["scheduled"] * 5
    # O "cancelar" de dentro da conversa segue a mesma regra.
    assert client.post(f"/ui/chats/{client.sid}/scheduled/{target.id}/cancel", data={"chat": LEO}).status_code == 404
    with Session(get_engine()) as db:
        assert all(s.enabled for s in db.exec(select(Schedule)).all())


def test_base_pauses_the_panel_refresh_while_a_confirmation_is_open():
    from pathlib import Path

    base = (Path(__file__).resolve().parent.parent / "whatsapp_scheduler" / "web" / "templates" / "base.html").read_text()
    assert "[data-hold-poll]:not([hidden])" in base and "function smpConfirm" in base
    assert "htmx:oobAfterSwap" in base and "__chatLastSent" in base
