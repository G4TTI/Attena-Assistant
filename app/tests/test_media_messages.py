"""Agendamento de fotos, vídeos, áudios e PDFs — recurso exclusivo do plano mais caro.

Cobre: o recurso por plano (e a migração que o liga no plano mais caro), o upload
(tipo pelos bytes, tamanho, arquivo e nome cifrados), o envio pelo scheduler, o
expurgo quando a mensagem termina, rascunhos abandonados, edição, isolamento
entre usuários e o plano B do vídeo no WAHA."""

import asyncio
import base64
import json
import os
import time
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, col, select

from tests.conftest import FakeWaha, db_locations_containing, register_and_login, text_of
from whatsapp_scheduler import media, migrations, plans, retention
from whatsapp_scheduler.clock import utcnow
from whatsapp_scheduler.config import settings
from whatsapp_scheduler.db import get_engine
from whatsapp_scheduler.errors import ValidationError
from whatsapp_scheduler.main import app
from whatsapp_scheduler.models import (
    MediaAttachment,
    MediaKind,
    Schedule,
    ScheduleGroup,
    Subscription,
    SubscriptionStatus,
    User,
    WhatsAppSession,
)
from whatsapp_scheduler.scheduler import SchedulerService
from whatsapp_scheduler.service import create_sequence
from whatsapp_scheduler.waha import WahaClient

CHAT = "5514991110001@c.us"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"conteudo-da-foto-SEGREDO" * 40
PDF = b"%PDF-1.4\n" + b"laudo-do-paciente-SEGREDO" * 40
OGG = b"OggS\x00\x02" + b"\x00" * 20 + b"audio-SEGREDO" * 40
MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00" + b"video-SEGREDO" * 40


@pytest.fixture
def client():
    waha = FakeWaha()
    with TestClient(app) as c:
        c.app.state.waha = waha
        c.waha = waha
        c.user = register_and_login(c)
        yield c


@pytest.fixture(autouse=True)
def _empty_media_dir():
    """A pasta de anexos fica ao lado do banco de teste e sobrevive entre testes."""
    def wipe():
        for path in media.media_root().iterdir():
            path.unlink()

    wipe()
    yield
    wipe()


@pytest.fixture
def no_grace(monkeypatch):
    """Sem a carência de 5 min: o anexo some no mesmo commit em que a mensagem termina."""
    monkeypatch.setattr(retention, "_MEDIA_GRACE", timedelta(0))


def give_plan(user_id: str, code: str) -> None:
    with Session(get_engine()) as db:
        plan = plans.get_plan(db, code)
        db.add(Subscription(user_id=user_id, plan_id=plan.id, status=SubscriptionStatus.active, provider="manual"))
        db.commit()


def upload(client, data: bytes, filename: str, content_type: str = "application/octet-stream"):
    return client.post("/ui/media", files={"file": (filename, data, content_type)})


def session_name(user_id: str) -> str:
    with Session(get_engine()) as db:
        return db.exec(select(WhatsAppSession).where(col(WhatsAppSession.user_id) == user_id)).first().session_name


def session_id(user_id: str) -> str:
    with Session(get_engine()) as db:
        return db.exec(select(WhatsAppSession).where(col(WhatsAppSession.user_id) == user_id)).first().id


def schedule_form(client, *, messages, media_ids, when=None, recurrence=""):
    when = when or (utcnow() - timedelta(hours=3) + timedelta(days=2))  # horário de São Paulo, daqui a 2 dias
    return client.post(
        "/ui/schedules",
        data={
            "recipients": [CHAT], "recipient_names": ["Paciente"], "messages": messages, "media_ids": media_ids,
            "send_date": when.strftime("%Y-%m-%d"), "send_time": when.strftime("%H:%M"),
            "whatsapp_session_id": session_id(client.user.id), "recurrence": recurrence,
        },
    )


def media_row(media_id: str) -> MediaAttachment:
    with Session(get_engine()) as db:
        return db.get(MediaAttachment, media_id)


def schedules() -> list[Schedule]:
    with Session(get_engine()) as db:
        return list(db.exec(select(Schedule).order_by(col(Schedule.created_at), col(Schedule.position))).all())


def run_now_and_tick(client) -> None:
    with Session(get_engine()) as db:
        group = db.exec(select(ScheduleGroup)).first()
    client.post(f"/ui/schedules/{group.id}/run-now")
    asyncio.run(SchedulerService(client.waha).run_once())


# --------------------------------------------------------------------------- #
# Recurso por plano
# --------------------------------------------------------------------------- #
def test_only_the_most_expensive_plan_has_media_in_the_seeded_catalog(client):
    with Session(get_engine()) as db:
        catalog = {p.code: p for p in plans.list_plans(db)}
        assert plans.MEDIA_MESSAGES in plans.capabilities(catalog["pro"])
        assert plans.MEDIA_MESSAGES not in plans.capabilities(catalog["plus"])
        assert plans.MEDIA_MESSAGES not in plans.capabilities(catalog["free"])
        assert plans.MEDIA_MESSAGES in plans.capabilities(catalog["admin"])
        assert plans.CAPABILITY_LABELS[plans.MEDIA_MESSAGES] in plans.features(catalog["pro"])
        assert plans.upgrade_plan_for(db, plans.MEDIA_MESSAGES).code == "pro"


def test_free_plan_sees_the_locked_button_and_cannot_upload(client):
    page = client.get("/agendamentos").text
    assert "plan-badge" in page and "Pro" in page and 'type="file"' not in page
    r = upload(client, JPEG, "foto.jpg", "image/jpeg")
    assert r.status_code == 403
    assert "plano Pro" in r.json()["error"]
    assert not list(media.media_root().iterdir())


def test_plus_plan_is_not_enough_but_pro_is(client):
    give_plan(client.user.id, "plus")
    assert upload(client, JPEG, "foto.jpg").status_code == 403
    give_plan(client.user.id, "pro")
    assert upload(client, JPEG, "foto.jpg").status_code == 200
    assert 'type="file"' in client.get("/agendamentos").text


def test_capability_is_enforced_even_without_enforce_plan_limits(client, monkeypatch):
    monkeypatch.setattr(settings, "enforce_plan_limits", False)
    assert upload(client, JPEG, "foto.jpg").status_code == 403


def test_migration_turns_media_on_in_the_most_expensive_plan_only(client):
    with get_engine().begin() as conn:
        conn.execute(text("UPDATE plans SET capabilities_json='[]'"))
        conn.execute(text("UPDATE plans SET features_json='[\"Tudo do Plus\"]' WHERE code='pro'"))
        migrations._media_messages_capability(conn)
    with Session(get_engine()) as db:
        catalog = {p.code: p for p in plans.list_plans(db)}
        assert [c for c, p in catalog.items() if plans.MEDIA_MESSAGES in plans.capabilities(p)] == ["pro", "admin"]
        assert plans.features(catalog["pro"]) == ["Tudo do Plus", plans.CAPABILITY_LABELS[plans.MEDIA_MESSAGES]]


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #
def test_upload_is_encrypted_on_disk_and_the_name_is_not_in_the_database(client):
    give_plan(client.user.id, "pro")
    r = upload(client, JPEG, "foto-do-exame-joaquim.jpeg", "image/jpeg")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "image" and body["name"] == "foto-do-exame-joaquim.jpg" and body["kind_label"] == "Foto"
    row = media_row(body["id"])
    on_disk = (media.media_root() / row.storage_key).read_bytes()
    assert b"SEGREDO" not in on_disk and len(on_disk) == len(JPEG) + 16  # só ciphertext + tag GCM
    assert oct((media.media_root() / row.storage_key).stat().st_mode & 0o777) == "0o600"
    assert db_locations_containing("joaquim") == []
    assert media.load_bytes(row) == JPEG


def test_type_comes_from_the_bytes_not_from_the_name(client):
    give_plan(client.user.id, "pro")
    r = upload(client, b"MZ\x90\x00 programa", "foto.jpg", "image/jpeg")
    assert r.status_code == 422 and "Formato não suportado" in r.json()["error"]
    r = upload(client, PDF, "documento.exe")
    assert r.status_code == 200 and r.json()["kind"] == "document" and r.json()["name"] == "documento.pdf"
    assert upload(client, OGG, "voz.ogg").json()["kind"] == "audio"
    assert upload(client, MP4, "clipe.mp4").json()["kind"] == "video"
    assert upload(client, MP4, "nota.m4a", "audio/mp4").json()["kind"] == "audio"


def test_upload_size_limit(client, monkeypatch):
    give_plan(client.user.id, "pro")
    monkeypatch.setattr(settings, "media_max_bytes", 100)
    r = upload(client, JPEG, "grande.jpg")
    assert r.status_code == 413 and "limite" in r.json()["error"]
    assert upload(client, b"", "vazio.jpg").status_code in (400, 422)


def test_preview_is_only_for_the_owner(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    r = client.get(f"/ui/media/{media_id}")
    assert r.status_code == 200 and r.content == JPEG and r.headers["content-type"] == "image/jpeg"
    assert r.headers["cache-control"] == "no-store"
    client.cookies.clear()
    register_and_login(client, name="Outra", email="outra@example.com")
    assert client.get(f"/ui/media/{media_id}").status_code == 404


# --------------------------------------------------------------------------- #
# Agendar, enviar e expurgar
# --------------------------------------------------------------------------- #
def test_photo_with_caption_is_sent_and_then_purged(client, no_grace):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg", "image/jpeg").json()["id"]
    r = schedule_form(client, messages=["Segue a foto"], media_ids=[media_id])
    assert "Agendamento criado" in r.text, r.text
    [schedule] = schedules()
    assert schedule.media_id == media_id and text_of(schedule) == "Segue a foto"

    run_now_and_tick(client)
    [sent] = client.waha.sent
    assert sent["kind"] == "image" and sent["mimetype"] == "image/jpeg" and sent["data"] == JPEG
    assert sent["caption"] == "Segue a foto" and sent["filename"] == "foto.jpg" and sent["chatId"] == CHAT

    row = media_row(media_id)
    assert row.storage_key is None and row.filename_encrypted is None and row.content_purged_at is not None
    assert not list(media.media_root().iterdir())
    assert client.get(f"/ui/media/{media_id}").status_code == 404


def test_media_only_message_needs_no_text(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, PDF, "laudo.pdf").json()["id"]
    r = schedule_form(client, messages=["", "Qualquer dúvida, me chame."], media_ids=[media_id, ""])
    assert "Agendamento criado" in r.text, r.text
    first, second = schedules()
    assert (first.media_id, text_of(first)) == (media_id, "")
    assert (second.media_id, text_of(second)) == (None, "Qualquer dúvida, me chame.")


def test_empty_block_without_media_is_still_rejected(client):
    give_plan(client.user.id, "pro")
    r = schedule_form(client, messages=[""], media_ids=[""])
    assert "não pode ficar vazia" in r.text and not schedules()


def test_audio_with_text_becomes_voice_then_text(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, OGG, "voz.ogg").json()["id"]
    schedule_form(client, messages=["Ouça o áudio acima"], media_ids=[media_id])
    first, second = schedules()
    assert (first.media_id, text_of(first)) == (media_id, "")
    assert (second.media_id, text_of(second)) == (None, "Ouça o áudio acima")


def test_audio_with_text_and_recurrence_explains_why_not(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, OGG, "voz.ogg").json()["id"]
    r = schedule_form(client, messages=["texto"], media_ids=[media_id], recurrence="daily 09:00")
    assert "não aceita legenda em áudio" in r.text and not schedules()
    # O formulário volta com o anexo (não precisa mandar o arquivo de novo).
    assert media_id in r.text


def test_cancel_purges_the_attachment(client, no_grace):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    schedule_form(client, messages=["oi"], media_ids=[media_id])
    with Session(get_engine()) as db:
        group = db.exec(select(ScheduleGroup)).first()
    client.post(f"/ui/schedules/{group.id}/cancel")
    assert media_row(media_id).storage_key is None and not list(media.media_root().iterdir())


def test_attachment_shared_by_two_recipients_survives_until_the_last_one(client, no_grace):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    when = utcnow() + timedelta(days=2)
    client.post("/ui/schedules", data={
        "recipients": [CHAT, "5511982220002@c.us"], "recipient_names": ["A", "B"], "messages": ["oi"],
        "media_ids": [media_id], "send_date": when.strftime("%Y-%m-%d"), "send_time": "10:00",
        "whatsapp_session_id": session_id(client.user.id),
    })
    with Session(get_engine()) as db:
        first, second = db.exec(select(ScheduleGroup).order_by(col(ScheduleGroup.created_at))).all()
    client.post(f"/ui/schedules/{first.id}/cancel")
    assert media_row(media_id).storage_key is not None  # o outro destinatário ainda vai receber
    client.post(f"/ui/schedules/{second.id}/cancel")
    assert media_row(media_id).storage_key is None


def test_fresh_attachment_waits_for_the_cleanup_job(client):
    """Carência de 5 min (vários destinatários = vários commits): o anexo de uma
    mensagem que saiu logo após o upload some no privacy_cleanup seguinte."""
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    schedule_form(client, messages=["oi"], media_ids=[media_id])
    run_now_and_tick(client)
    assert media_row(media_id).storage_key is not None
    with Session(get_engine()) as db:
        row = db.get(MediaAttachment, media_id)
        row.created_at = utcnow() - timedelta(minutes=6)
        db.add(row)
        db.commit()
        counts = retention.run_cleanup(db)
    assert counts["media_files"] == 1 and media_row(media_id).storage_key is None


def test_failed_attempt_keeps_the_file_for_the_retry(client, no_grace):
    from whatsapp_scheduler.waha import WahaError

    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    schedule_form(client, messages=["oi"], media_ids=[media_id])
    client.waha.send_error = WahaError("WAHA respondeu 500", status_code=500)
    run_now_and_tick(client)
    assert media_row(media_id).storage_key is not None


def test_missing_file_fails_the_message_without_sending(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    schedule_form(client, messages=["oi"], media_ids=[media_id])
    (media.media_root() / media_row(media_id).storage_key).unlink()
    run_now_and_tick(client)
    assert client.waha.sent == []


def test_duplicate_submit_creates_one_schedule(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    schedule_form(client, messages=["oi"], media_ids=[media_id])
    schedule_form(client, messages=["oi"], media_ids=[media_id])
    assert len(schedules()) == 1


def test_detail_modal_shows_the_attachment_to_the_owner(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, PDF, "laudo-final.pdf").json()["id"]
    schedule_form(client, messages=["Seu laudo"], media_ids=[media_id])
    with Session(get_engine()) as db:
        group = db.exec(select(ScheduleGroup)).first()
    page = client.get(f"/ui/schedules/{group.id}").text
    assert "laudo-final.pdf" in page and f"/ui/media/{media_id}" in page and "Seu laudo" in page


# --------------------------------------------------------------------------- #
# Edição
# --------------------------------------------------------------------------- #
def test_edit_keeps_or_drops_the_attachment(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    schedule_form(client, messages=["oi"], media_ids=[media_id])
    with Session(get_engine()) as db:
        group = db.exec(select(ScheduleGroup)).first()
    edit_page = client.get(f"/ui/schedules/{group.id}/edit").text
    assert f'name="media_ids" value="{media_id}"' in edit_page

    when = utcnow() + timedelta(days=3)
    data = {"messages": ["oi de novo"], "send_date": when.strftime("%Y-%m-%d"), "send_time": "10:00",
            "whatsapp_session_id": session_id(client.user.id)}
    client.post(f"/ui/schedules/{group.id}/edit", data={**data, "media_ids": [media_id]})
    [schedule] = schedules()
    assert schedule.media_id == media_id and text_of(schedule) == "oi de novo"

    client.post(f"/ui/schedules/{group.id}/edit", data={**data, "media_ids": [""]})
    [schedule] = schedules()
    assert schedule.media_id is None
    assert media_row(media_id).storage_key is None  # tirado na edição: some na hora


# --------------------------------------------------------------------------- #
# Isolamento e plano
# --------------------------------------------------------------------------- #
def test_cannot_schedule_with_someone_elses_attachment(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    client.cookies.clear()
    other = register_and_login(client, name="Outra", email="outra@example.com")
    give_plan(other.id, "pro")
    with Session(get_engine()) as db, pytest.raises(ValidationError, match="Anexo não encontrado"):
        create_sequence(db, user_id=other.id, session=session_name(other.id), recipient=CHAT, messages=["x"],
                        media_ids=[media_id], start=utcnow() + timedelta(days=1))


def test_downgraded_user_cannot_schedule_an_old_upload(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    with Session(get_engine()) as db:
        for sub in db.exec(select(Subscription)).all():
            sub.status = SubscriptionStatus.cancelled
            db.add(sub)
        db.commit()
    r = schedule_form(client, messages=["oi"], media_ids=[media_id])
    assert "plano Pro" in r.text and not schedules()


def test_admin_has_the_feature_regardless_of_plan(client):
    with Session(get_engine()) as db:
        user = db.get(User, client.user.id)
        user.role = "admin"
        db.add(user)
        db.commit()
    assert upload(client, JPEG, "foto.jpg").status_code == 200


# --------------------------------------------------------------------------- #
# Retenção de rascunhos e arquivos órfãos
# --------------------------------------------------------------------------- #
def test_abandoned_upload_and_orphan_files_are_cleaned(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    stray = media.media_root() / "lixo.bin"
    stray.write_bytes(b"x")
    old = time.time() - 2 * 3600
    os.utime(stray, (old, old))
    with Session(get_engine()) as db:
        counts = retention.run_cleanup(db)
        assert counts["media_files"] == 0 and counts["media_orphan_files"] == 1  # rascunho ainda no prazo
        row = db.get(MediaAttachment, media_id)
        row.created_at = utcnow() - timedelta(minutes=settings.media_draft_ttl_minutes + 1)
        db.add(row)
        db.commit()
        counts = retention.run_cleanup(db)
    assert counts["media_files"] == 1
    assert media_row(media_id).storage_key is None and not list(media.media_root().iterdir())


def test_too_many_drafts(client, monkeypatch):
    give_plan(client.user.id, "pro")
    monkeypatch.setattr(media, "MAX_DRAFTS_PER_USER", 2)
    assert upload(client, JPEG, "1.jpg").status_code == 200
    assert upload(client, JPEG, "2.jpg").status_code == 200
    r = upload(client, JPEG, "3.jpg")
    assert r.status_code == 422 and "ainda não agendados" in r.json()["error"]


# --------------------------------------------------------------------------- #
# WAHA: endpoint por tipo e plano B do vídeo
# --------------------------------------------------------------------------- #
def _waha_with(handler) -> WahaClient:
    client = WahaClient("http://waha.test", "k")
    client._client = httpx.AsyncClient(base_url="http://waha.test", transport=httpx.MockTransport(handler))
    return client


def test_waha_routes_each_kind_to_its_endpoint():
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, json.loads(request.content)))
        return httpx.Response(201, json={"id": "true_x_1"})

    waha = _waha_with(handler)

    async def go():
        for kind, mimetype in (("image", "image/jpeg"), ("audio", "audio/ogg"), ("document", "application/pdf")):
            await waha.send_media("s", CHAT, kind=kind, mimetype=mimetype, filename="f", data=b"abc", caption="leg")

    asyncio.run(go())
    paths = [path for path, _ in calls]
    assert paths == ["/api/sendImage", "/api/sendVoice", "/api/sendFile"]
    image, audio, document = (body for _, body in calls)
    assert image["file"] == {"mimetype": "image/jpeg", "filename": "f", "data": base64.b64encode(b"abc").decode()}
    assert image["caption"] == "leg" and document["caption"] == "leg"
    assert "caption" not in audio and audio["convert"] is True


def test_waha_video_falls_back_to_document_without_chrome():
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, json.loads(request.content)))
        if request.url.path == "/api/sendVideo":
            return httpx.Response(422, json={"message": 'Use "devlikeapro/waha:chrome" docker image to send video in WEBJS'})
        return httpx.Response(201, json={"id": "true_x_2"})

    payload = asyncio.run(
        _waha_with(handler).send_media("s", CHAT, kind="video", mimetype="video/mp4", filename="v.mp4", data=b"v", caption="c")
    )
    assert [path for path, _ in calls] == ["/api/sendVideo", "/api/sendFile"]
    assert calls[1][1]["caption"] == "c" and "convert" not in calls[1][1]
    assert payload["id"] == "true_x_2"


def test_waha_other_video_errors_are_not_masked():
    from whatsapp_scheduler.waha import WahaError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "chatId inválido"})

    with pytest.raises(WahaError):
        asyncio.run(_waha_with(handler).send_media("s", CHAT, kind="video", mimetype="video/mp4", filename="v", data=b"v"))


def test_waha_500_keeps_only_the_reason_never_the_echoed_request():
    """O 500 do WAHA devolve o pedido inteiro (destinatário, legenda, arquivo em
    base64). O erro guarda só o motivo — que é o que permite diagnosticar."""
    from whatsapp_scheduler import failures
    from whatsapp_scheduler.waha import WahaError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={
            "statusCode": 500,
            "exception": {"message": "Data passed to getter must include an id property\ns (https://static.whatsapp.net/x.js:85)",
                          "name": "Error", "stack": "Error: ...\n at ..."},
            "request": {"body": json.loads(request.content)},
        })

    with pytest.raises(WahaError) as caught:
        asyncio.run(_waha_with(handler).send_media(
            "s", CHAT, kind="image", mimetype="image/jpeg", filename="f.jpg", data=JPEG, caption="legenda SEGREDO"))
    exc = caught.value
    assert exc.status_code == 500 and exc.reason == "Data passed to getter must include an id property"
    code, message = failures.classify_waha_error(exc)
    assert code == failures.WAHA_SERVER_ERROR
    assert message == "O WAHA respondeu com erro interno (HTTP 500). Motivo: Data passed to getter must include an id property"
    for leaked in ("SEGREDO", CHAT.split("@")[0], base64.b64encode(JPEG).decode()[:40]):
        assert leaked not in str(exc) and leaked not in message


def test_waha_reason_of_a_rejection_is_sanitized():
    from whatsapp_scheduler import failures
    from whatsapp_scheduler.waha import WahaError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": ["chatId 5514991110001@c.us inválido"], "error": "Bad Request"})

    with pytest.raises(WahaError) as caught:
        asyncio.run(_waha_with(handler).send_text("s", CHAT, "oi"))
    code, message = failures.classify_waha_error(caught.value)
    assert code == failures.WAHA_REJECTED and "inválido" in message and "5514991110001" not in message


def test_failed_media_send_records_the_reason(client, no_grace):
    from whatsapp_scheduler.waha import WahaError

    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto.jpg").json()["id"]
    schedule_form(client, messages=["oi"], media_ids=[media_id])
    client.waha.send_error = WahaError("WAHA respondeu 500", status_code=500, reason="Data passed to getter must include an id property")
    run_now_and_tick(client)
    from whatsapp_scheduler.models import Dispatch

    with Session(get_engine()) as db:
        dispatch = db.exec(select(Dispatch)).first()
    assert dispatch.failure_code == "waha_server_error"
    assert dispatch.last_error.endswith("Motivo: Data passed to getter must include an id property")


def test_dashboard_shows_the_attachment_type_of_a_media_only_message(client):
    give_plan(client.user.id, "pro")
    media_id = upload(client, PDF, "laudo-secreto.pdf").json()["id"]
    schedule_form(client, messages=[""], media_ids=[media_id], when=utcnow() - timedelta(hours=3) + timedelta(hours=2))
    page = client.get("/ui/dashboard/summary").text
    assert ">PDF</span>" in page and "laudo-secreto" not in page  # só o tipo, nunca o nome do arquivo


# --------------------------------------------------------------------------- #
# Rotação de chave (cli rotate-keys)
# --------------------------------------------------------------------------- #
@pytest.fixture
def add_key_version(monkeypatch):
    """Chama-se no meio do teste: a partir daí a chave ativa é a versão 2."""
    from whatsapp_scheduler import privacy

    def activate() -> None:
        monkeypatch.setattr(settings, "data_encryption_keys", f"{settings.data_encryption_keys},2:{privacy.generate_key()}")
        privacy.reset_key_cache()

    yield activate
    monkeypatch.undo()
    privacy.reset_key_cache()


def test_rotate_keys_reencrypts_attachments_without_overwriting_before_commit(client, add_key_version):
    from whatsapp_scheduler import cli, privacy

    give_plan(client.user.id, "pro")
    media_id = upload(client, JPEG, "foto-rotacao.jpg").json()["id"]
    old_key = media_row(media_id).storage_key
    add_key_version()
    assert media_row(media_id).encryption_key_version == 1 and privacy.active_key_version() == 2

    # rotate_file grava o arquivo novo em OUTRO nome e não toca no antigo (só se apaga depois do commit).
    with Session(get_engine()) as db:
        row = db.get(MediaAttachment, media_id)
        returned = media.rotate_file(row)
        assert returned == old_key and row.storage_key != old_key
        assert (media.media_root() / old_key).exists() and (media.media_root() / row.storage_key).exists()
        db.rollback()  # commit "falhou": a linha continua batendo com o arquivo antigo
    assert media.load_bytes(media_row(media_id)) == JPEG

    cli.cmd_rotate_keys(None)
    row = media_row(media_id)
    assert row.encryption_key_version == 2 and row.storage_key != old_key
    assert media.load_bytes(row) == JPEG and privacy.media_filename(row) == "foto-rotacao.jpg"
    assert not (media.media_root() / old_key).exists()


def test_sniff_signatures():
    assert media.sniff(JPEG[:16]) == (MediaKind.image, "image/jpeg")
    assert media.sniff(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) == (MediaKind.image, "image/png")
    assert media.sniff(b"ID3\x04" + b"\x00" * 12) == (MediaKind.audio, "audio/mpeg")
    assert media.sniff(b"\xff\xf1\x50\x80" + b"\x00" * 12) == (MediaKind.audio, "audio/aac")
    assert media.sniff(b"RIFF\x00\x00\x00\x00WAVEfmt ") == (MediaKind.audio, "audio/wav")
    assert media.sniff(b"\x00\x00\x00\x14ftypqt  \x00\x00") == (MediaKind.video, "video/quicktime")
    assert media.sniff(b"<svg xmlns=") is None and media.sniff(b"GIF89a") is None
