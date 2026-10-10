"""Anexos de mensagens programadas: foto, vídeo, áudio e PDF (recurso de plano).

Fluxo:
  1. o navegador manda o arquivo sozinho (`POST /ui/media`) assim que o usuário
     o escolhe; `store_upload` confere o plano, valida o tipo pelos BYTES (não
     pela extensão nem pelo content-type do navegador) e o tamanho, cifra e
     grava no disco — vira um RASCUNHO;
  2. o formulário de agendamento manda só o id (`media_ids`, alinhado com as
     mensagens) e `service.create_sequence` liga o anexo às mensagens;
  3. na hora do envio o scheduler lê o arquivo, decifra EM MEMÓRIA e entrega ao
     WAHA (`WahaClient.send_media`);
  4. quando nenhuma mensagem que usa o anexo ainda vai sair, ele é apagado
     (`retention.finalize_schedules`); rascunho abandonado expira em
     `media_draft_ttl_minutes` (`retention.run_cleanup`).

Privacidade: o mesmo modelo do texto (privacy.py) — arquivo e nome cifrados com
AES-256-GCM e AAD amarrado ao id da linha. O pacote admin/ nunca chama as
funções daqui que decifram (`load_bytes`, `infos`).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import exists, func
from sqlmodel import Session, col, select

from . import plans, privacy
from .config import settings
from .errors import ValidationError
from .models import MediaAttachment, MediaKind, Schedule, User

logger = logging.getLogger("whatsapp_scheduler.media")

KIND_LABELS = {
    MediaKind.image: "Foto",
    MediaKind.video: "Vídeo",
    MediaKind.audio: "Áudio",
    MediaKind.document: "PDF",
}
_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/3gpp": ".3gp",
    "video/webm": ".webm",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "application/pdf": ".pdf",
}
# Atributo `accept` do <input type=file> — só ajuda o seletor do sistema; quem
# decide de verdade é `sniff`.
ACCEPT = (
    "image/jpeg,image/png,video/mp4,video/quicktime,video/3gpp,video/webm,"
    "audio/*,.mp3,.m4a,.aac,.ogg,.opus,.wav,application/pdf,.pdf"
)
UNSUPPORTED_MESSAGE = (
    "Formato não suportado. Envie foto (JPG ou PNG), vídeo (MP4, MOV, 3GP ou WEBM), "
    "áudio (MP3, M4A, AAC, OGG ou WAV) ou PDF."
)
# Uploads ainda não agendados por usuário (dentro do prazo de rascunho) — evita
# encher o disco com arquivos que nunca vão sair.
MAX_DRAFTS_PER_USER = 30
_SNIFF_BYTES = 16


class MediaUnavailable(RuntimeError):
    """O arquivo do anexo não existe mais (expurgado ou apagado do disco)."""


# --------------------------------------------------------------------------- #
# Tipo do arquivo pelos primeiros bytes
# --------------------------------------------------------------------------- #
def sniff(head: bytes, declared: str = "") -> tuple[MediaKind, str] | None:
    """(tipo, mimetype) a partir da assinatura do arquivo; None = não aceito.
    `declared` (o que o navegador disse) só desempata contêineres que servem
    tanto pra áudio quanto pra vídeo (MP4/WebM)."""
    declared = (declared or "").lower()
    if head.startswith(b"\xff\xd8\xff"):
        return MediaKind.image, "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return MediaKind.image, "image/png"
    if head.startswith(b"%PDF-"):
        return MediaKind.document, "application/pdf"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"M4A ", b"M4B "):
            return MediaKind.audio, "audio/mp4"
        if brand == b"qt  ":
            return MediaKind.video, "video/quicktime"
        if brand.startswith(b"3g"):
            return MediaKind.video, "video/3gpp"
        if declared.startswith("audio/"):  # .m4a gravado pelo celular costuma vir com marca "isom"/"mp42"
            return MediaKind.audio, "audio/mp4"
        return MediaKind.video, "video/mp4"
    if head.startswith(b"OggS"):
        return MediaKind.audio, "audio/ogg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return MediaKind.audio, "audio/wav"
    if head.startswith(b"\x1a\x45\xdf\xa3"):  # Matroska/WebM
        return (MediaKind.audio, "audio/webm") if declared.startswith("audio/") else (MediaKind.video, "video/webm")
    if len(head) > 1 and head[0] == 0xFF and head[1] in (0xF1, 0xF9):  # AAC (ADTS)
        return MediaKind.audio, "audio/aac"
    if head.startswith(b"ID3") or (len(head) > 1 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return MediaKind.audio, "audio/mpeg"
    return None


def clean_filename(name: str, mimetype: str) -> str:
    """Só o nome (sem pasta), sem caracteres de controle, com a extensão do tipo REAL."""
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    base = "".join(ch for ch in base if ch.isprintable() and ch not in '<>:"/\\|?*')[:120].strip(" .")
    ext = _EXTENSIONS.get(mimetype, "")
    stem = base[: -len(Path(base).suffix)] if Path(base).suffix else base
    return f"{stem or 'arquivo'}{ext}"


def size_label(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB".replace(".", ",")
    return f"{max(1, round(size / 1024))} KB"


def max_size_label() -> str:
    return size_label(settings.media_max_bytes)


# --------------------------------------------------------------------------- #
# Disco
# --------------------------------------------------------------------------- #
def media_root() -> Path:
    root = Path(settings.media_dir) if settings.media_dir else Path(settings.db_path).parent / "media"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def _path(storage_key: str) -> Path:
    path = (media_root() / storage_key).resolve()
    if path.parent != media_root().resolve():  # nunca sai da pasta de anexos
        raise MediaUnavailable("caminho de anexo inválido")
    return path


def _write(storage_key: str, data: bytes) -> None:
    final = _path(storage_key)
    tmp = final.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, final)


def delete_file(storage_key: str | None) -> None:
    if not storage_key:
        return
    try:
        _path(storage_key).unlink(missing_ok=True)
    except (OSError, MediaUnavailable):
        logger.warning("não consegui apagar o arquivo de um anexo (o privacy_cleanup tenta de novo)")


def load_bytes(media: MediaAttachment) -> bytes:
    """Conteúdo DECIFRADO do anexo — só para enviar ao WAHA ou mostrar ao dono."""
    if not media.storage_key:
        raise MediaUnavailable("anexo já expurgado")
    try:
        ciphertext = _path(media.storage_key).read_bytes()
    except FileNotFoundError as exc:
        raise MediaUnavailable("arquivo do anexo não encontrado") from exc
    return privacy.open_media_file(media, ciphertext)


def rotate_file(media: MediaAttachment) -> str | None:
    """Recifra arquivo + nome com a chave ativa (`cli rotate-keys`). O arquivo
    novo vai para OUTRO nome e a linha passa a apontar para ele; devolve o nome
    antigo, que quem chamou só apaga DEPOIS do commit. Assim, se o commit
    falhar, a linha continua batendo com o arquivo antigo (o novo vira órfão e
    o privacy_cleanup o remove) — nunca fica um nonce que não abre o arquivo."""
    if not media.storage_key or media.encryption_key_version == privacy.active_key_version():
        return None
    data = load_bytes(media)
    name = privacy.media_filename(media)
    old_key = media.storage_key
    new_key = f"{media.id}.{uuid4().hex[:8]}.bin"
    _write(new_key, privacy.seal_media_file(media, data))
    media.storage_key = new_key
    if name is not None:
        privacy.seal_media_filename(media, name)
    return old_key


# --------------------------------------------------------------------------- #
# Upload (rascunho)
# --------------------------------------------------------------------------- #
def _draft_count(db: Session, user_id: str) -> int:
    used = exists().where(col(Schedule.media_id) == col(MediaAttachment.id))
    return int(
        db.exec(
            select(func.count())
            .select_from(MediaAttachment)
            .where(col(MediaAttachment.user_id) == user_id)
            .where(col(MediaAttachment.storage_key).is_not(None))
            .where(~used)
        ).one()
    )


def store_upload(db: Session, user: User, *, data: bytes, filename: str, declared_type: str = "") -> MediaAttachment:
    """Valida, cifra e grava um anexo novo (ainda sem mensagem). Levanta
    `ValidationError` com o texto que vai pra tela."""
    plans.require_capability(db, user, plans.MEDIA_MESSAGES)
    if not data:
        raise ValidationError("O arquivo está vazio.")
    if len(data) > settings.media_max_bytes:
        raise ValidationError(f"O arquivo passa do limite de {max_size_label()}.")
    detected = sniff(data[:_SNIFF_BYTES], declared_type)
    if detected is None:
        raise ValidationError(UNSUPPORTED_MESSAGE)
    if _draft_count(db, user.id) >= MAX_DRAFTS_PER_USER:
        raise ValidationError("Há muitos anexos enviados e ainda não agendados. Agende ou aguarde alguns minutos.")
    kind, mimetype = detected
    media = MediaAttachment(user_id=user.id, kind=kind, mimetype=mimetype, size_bytes=len(data))
    media.storage_key = f"{media.id}.bin"
    privacy.seal_media_filename(media, clean_filename(filename, mimetype))
    _write(media.storage_key, privacy.seal_media_file(media, data))
    db.add(media)
    try:
        db.commit()
    except Exception:
        delete_file(media.storage_key)
        raise
    db.refresh(media)
    logger.info("anexo recebido: tipo=%s tamanho=%d", kind.value, len(data))
    return media


def resolve_for_user(db: Session, user_id: str, media_ids: list[str]) -> dict[str, MediaAttachment]:
    """Os anexos pedidos, conferindo dono e se ainda existem. Id de outro
    usuário responde igual a id inexistente."""
    wanted = list(dict.fromkeys(m for m in media_ids if m))
    if not wanted:
        return {}
    rows = {m.id: m for m in db.exec(select(MediaAttachment).where(col(MediaAttachment.id).in_(wanted))).all()}
    for media_id in wanted:
        media = rows.get(media_id)
        if media is None or media.user_id != user_id:
            raise ValidationError("Anexo não encontrado. Anexe o arquivo de novo.")
        if not media.storage_key:
            raise ValidationError("Um anexo expirou antes de ser agendado. Anexe o arquivo de novo.")
    return rows


# --------------------------------------------------------------------------- #
# Exibição (só para o DONO — decifra o nome)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MediaInfo:
    id: str
    kind: str
    kind_label: str
    name: str | None  # None = expurgado (a mensagem terminou)
    size_label: str
    mimetype: str

    @property
    def available(self) -> bool:
        return self.name is not None

    @property
    def is_image(self) -> bool:
        return self.kind == MediaKind.image.value


def info(media: MediaAttachment) -> MediaInfo:
    kind = MediaKind(media.kind)
    return MediaInfo(
        id=media.id,
        kind=kind.value,
        kind_label=KIND_LABELS[kind],
        name=privacy.media_filename(media, safe=True) if media.storage_key else None,
        size_label=size_label(media.size_bytes),
        mimetype=media.mimetype,
    )


def infos(db: Session, user_id: str, media_ids: list[str | None]) -> dict[str, MediaInfo]:
    wanted = list(dict.fromkeys(m for m in media_ids if m))
    if not wanted:
        return {}
    rows = db.exec(
        select(MediaAttachment).where(col(MediaAttachment.id).in_(wanted)).where(col(MediaAttachment.user_id) == user_id)
    ).all()
    return {m.id: info(m) for m in rows}


def attach_config(db: Session, user: User) -> dict:
    """O que o formulário precisa pra mostrar o botão de anexo (ou o convite pro plano)."""
    enabled = plans.has_capability(db, user, plans.MEDIA_MESSAGES)
    target = None if enabled else plans.upgrade_plan_for(db, plans.MEDIA_MESSAGES)
    return {
        "enabled": enabled,
        "plan_name": target.name if target else None,
        "accept": ACCEPT,
        "max_label": max_size_label(),
    }

