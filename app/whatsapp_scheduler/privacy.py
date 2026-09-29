"""Criptografia de dados de usuário em repouso ("Plano A").

O que isto é: o servidor guarda uma chave FORA do banco (variável de ambiente
ou arquivo de secret; nunca no Git, nunca no navegador) e só decifra um dado
quando precisa operar com ele — entregar uma mensagem programada no WhatsApp ou
mostrá-la ao próprio dono autenticado. O texto decifrado existe só em memória,
durante essa operação.

O que isto NÃO é: zero-knowledge nem E2EE. Quem controla o servidor de produção
E tem a chave consegue decifrar. O ganho é que o banco sozinho (e cada backup
dele) não revela conteúdo de mensagens, telefones de destinatários nem CPF, e
que nenhuma tela/API administrativa passa por aqui (ver admin/).

Primitivas (biblioteca `cryptography`, nada implementado à mão):
- AES-256-GCM (cifra autenticada), nonce aleatório de 96 bits por cifra.
- AAD = identidade da linha (ex. "attena:schedules.message:<id>"): um
  ciphertext copiado para outra linha — de outro usuário, por exemplo — não
  decifra, em vez de ser enviado pelo WhatsApp errado.
- Chaves versionadas (`DATA_ENCRYPTION_KEYS="1:<b64>,2:<b64>"`): dado novo usa a
  versão ativa; versões antigas continuam decifrando até `cli rotate-keys`.
- HMAC-SHA256 com chave própria (`DATA_HASH_KEY`) para "índices cegos": achar
  as mensagens de uma conversa pelo hash do telefone sem guardar o telefone.
  O hash leva o id do usuário junto — o mesmo número em duas contas gera hashes
  diferentes (não dá pra cruzar clientes pelo banco).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import settings

logger = logging.getLogger("whatsapp_scheduler.privacy")

_KEY_BYTES = 32
_NONCE_BYTES = 12

GENERATE_KEY_COMMAND = (
    "python -c \"import os,base64;print(base64.b64encode(os.urandom(32)).decode())\""
)
_HOW_TO = (
    "Gere as chaves com `python -m whatsapp_scheduler.cli generate-keys` (ou "
    f"{GENERATE_KEY_COMMAND}) e defina DATA_ENCRYPTION_KEYS=1:<chave> e DATA_HASH_KEY=<outra chave> "
    "no .env do servidor. Use chaves DIFERENTES em desenvolvimento e em produção."
)


class KeyConfigurationError(RuntimeError):
    """Chave ausente ou inválida — o app se recusa a subir sem ela."""


class DecryptionError(RuntimeError):
    """Não foi possível decifrar (chave errada/ausente, dado adulterado ou copiado de outra linha)."""


def generate_key() -> str:
    """Uma chave nova de 256 bits em base64 (serve para cifra e para HMAC)."""
    return base64.b64encode(os.urandom(_KEY_BYTES)).decode("ascii")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"), validate=True)


def _read_secret(value: str, file_path: str) -> str:
    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise KeyConfigurationError(f"Não consegui ler o arquivo de chave {file_path!r}: {exc}") from exc
    return (value or "").strip()


def _decode_key(raw: str, what: str) -> bytes:
    try:
        key = _unb64(raw.strip())
    except (binascii.Error, ValueError) as exc:
        raise KeyConfigurationError(f"{what}: não é base64 válido. {_HOW_TO}") from exc
    if len(key) != _KEY_BYTES:
        raise KeyConfigurationError(f"{what}: precisa ter {_KEY_BYTES} bytes (tem {len(key)}). {_HOW_TO}")
    return key


@dataclass(frozen=True)
class _Keyring:
    active_version: int
    ciphers: dict[int, AESGCM]


@lru_cache
def _keyring() -> _Keyring:
    raw = _read_secret(settings.data_encryption_keys, settings.data_encryption_keys_file)
    if not raw:
        raise KeyConfigurationError(f"DATA_ENCRYPTION_KEYS não configurada. {_HOW_TO}")
    ciphers: dict[int, AESGCM] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        version_text, sep, material = part.partition(":")
        try:
            version = int(version_text)
        except ValueError:
            version = 0
        if not sep or version < 1:
            raise KeyConfigurationError("DATA_ENCRYPTION_KEYS: use o formato 1:<chave>[,2:<chave>] (versões >= 1).")
        if version in ciphers:
            raise KeyConfigurationError(f"DATA_ENCRYPTION_KEYS: versão {version} repetida.")
        ciphers[version] = AESGCM(_decode_key(material, f"DATA_ENCRYPTION_KEYS versão {version}"))
    if not ciphers:
        raise KeyConfigurationError(f"DATA_ENCRYPTION_KEYS vazia. {_HOW_TO}")
    active = settings.data_encryption_active_version or max(ciphers)
    if active not in ciphers:
        raise KeyConfigurationError(f"DATA_ENCRYPTION_ACTIVE_VERSION={active} não existe em DATA_ENCRYPTION_KEYS.")
    return _Keyring(active_version=active, ciphers=ciphers)


@lru_cache
def _hash_key() -> bytes:
    raw = _read_secret(settings.data_hash_key, settings.data_hash_key_file)
    if not raw:
        raise KeyConfigurationError(f"DATA_HASH_KEY não configurada. {_HOW_TO}")
    return _decode_key(raw, "DATA_HASH_KEY")


def check_configuration() -> None:
    """Valida as duas chaves (levanta `KeyConfigurationError`). Chamada no boot."""
    _keyring()
    _hash_key()


def reset_key_cache() -> None:
    """Relê as chaves na próxima operação (testes e rotação)."""
    _keyring.cache_clear()
    _hash_key.cache_clear()


def active_key_version() -> int:
    return _keyring().active_version


# --------------------------------------------------------------------------- #
# Cifra autenticada
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Sealed:
    ciphertext: str  # base64(ciphertext || tag GCM)
    nonce: str  # base64, 12 bytes
    key_version: int


def seal(plaintext: str, *, aad: str) -> Sealed:
    ring = _keyring()
    nonce = os.urandom(_NONCE_BYTES)
    ct = ring.ciphers[ring.active_version].encrypt(nonce, plaintext.encode("utf-8"), aad.encode("utf-8"))
    return Sealed(ciphertext=_b64(ct), nonce=_b64(nonce), key_version=ring.active_version)


def unseal(ciphertext: str, nonce: str, key_version: int, *, aad: str) -> str:
    cipher = _keyring().ciphers.get(int(key_version))
    if cipher is None:
        raise DecryptionError(f"a chave versão {key_version} não está configurada")
    try:
        return cipher.decrypt(_unb64(nonce), _unb64(ciphertext), aad.encode("utf-8")).decode("utf-8")
    except (InvalidTag, ValueError, binascii.Error) as exc:
        raise DecryptionError("falha ao decifrar (chave errada, dado adulterado ou de outra linha)") from exc


def encrypt_field(plaintext: str | None, *, aad: str) -> str | None:
    """Envelope de uma coluna só: "v<versão>:<nonce b64>:<ciphertext b64>"."""
    if plaintext is None:
        return None
    sealed = seal(plaintext, aad=aad)
    return f"v{sealed.key_version}:{sealed.nonce}:{sealed.ciphertext}"


def _parse_envelope(envelope: str) -> tuple[int, str, str]:
    try:
        version, nonce, ciphertext = envelope.split(":", 2)
        if not version.startswith("v"):
            raise ValueError
        return int(version[1:]), nonce, ciphertext
    except ValueError as exc:
        raise DecryptionError("envelope cifrado em formato inválido") from exc


def decrypt_field(envelope: str | None, *, aad: str) -> str | None:
    if not envelope:
        return None
    version, nonce, ciphertext = _parse_envelope(envelope)
    return unseal(ciphertext, nonce, version, aad=aad)


def envelope_version(envelope: str | None) -> int | None:
    if not envelope:
        return None
    return _parse_envelope(envelope)[0]


# --------------------------------------------------------------------------- #
# Índice cego (HMAC)
# --------------------------------------------------------------------------- #
def blind_index(*parts: str) -> str:
    message = "\x1f".join(parts).encode("utf-8")
    return hmac.new(_hash_key(), message, hashlib.sha256).hexdigest()


def recipient_hash(user_id: str | None, chat_id: str) -> str:
    """Hash do destinatário no escopo de UM usuário (nunca o número em si)."""
    return blind_index("recipient", user_id or "", chat_id)


def waha_message_hash(user_id: str | None, message_id: str) -> str:
    """O id de mensagem do WAHA embute o telefone ("true_5511...@c.us_ABC") — guardamos só o hash."""
    return blind_index("waha-message", user_id or "", message_id)


# --------------------------------------------------------------------------- #
# Acesso aos campos cifrados de cada entidade. É o ÚNICO caminho de leitura do
# conteúdo privado — o pacote admin/ nunca importa estas funções (há teste).
# --------------------------------------------------------------------------- #
def _aad(kind: str, row_id: str) -> str:
    return f"attena:{kind}:{row_id}"


def _safe(fn, kind: str, row_id: str, safe: bool):
    try:
        return fn()
    except DecryptionError:
        if not safe:
            raise
        logger.warning("conteúdo cifrado ilegível (%s id=%s) — chave errada ou dado adulterado", kind, row_id)
        return None


# ---- Mensagem programada (`Schedule`) ---------------------------------------- #
def seal_schedule_message(schedule, text: str) -> None:
    sealed = seal(text, aad=_aad("schedules.message", schedule.id))
    schedule.message_ciphertext = sealed.ciphertext
    schedule.encryption_nonce = sealed.nonce
    schedule.encryption_key_version = sealed.key_version
    schedule.content_purged_at = None


def schedule_message(schedule, *, safe: bool = False) -> str | None:
    if not schedule.message_ciphertext or not schedule.encryption_nonce:
        return None
    return _safe(
        lambda: unseal(
            schedule.message_ciphertext, schedule.encryption_nonce, schedule.encryption_key_version or 0,
            aad=_aad("schedules.message", schedule.id),
        ),
        "schedules.message", schedule.id, safe,
    )


def seal_schedule_recipient(schedule, chat_id: str) -> None:
    schedule.recipient_phone_encrypted = encrypt_field(chat_id, aad=_aad("schedules.recipient", schedule.id))
    schedule.recipient_phone_hash = recipient_hash(schedule.user_id, chat_id)


def schedule_recipient(schedule, *, safe: bool = False) -> str | None:
    return _safe(
        lambda: decrypt_field(schedule.recipient_phone_encrypted, aad=_aad("schedules.recipient", schedule.id)),
        "schedules.recipient", schedule.id, safe,
    )


# ---- Destinatário de um agendamento (`ScheduleGroup`) ------------------------ #
@dataclass(frozen=True)
class Recipient:
    chat_id: str
    input: str
    name: str | None = None

    @property
    def is_group(self) -> bool:
        return self.chat_id.endswith("@g.us")

    @property
    def phone(self) -> str | None:
        """"+5511999998888" para contato individual; None para grupo/outros ids."""
        head = self.chat_id.split("@", 1)[0]
        return f"+{head}" if self.chat_id.endswith("@c.us") and head.isdigit() else None

    @property
    def display(self) -> str:
        return self.name or self.phone or self.input or self.chat_id


def seal_group_recipient(group, *, chat_id: str, recipient_input: str, recipient_name: str | None) -> None:
    payload = json.dumps({"chat_id": chat_id, "input": recipient_input, "name": recipient_name}, ensure_ascii=False)
    group.recipient_encrypted = encrypt_field(payload, aad=_aad("schedule_groups.recipient", group.id))
    group.recipient_phone_hash = recipient_hash(group.user_id, chat_id)
    group.content_purged_at = None


def group_recipient(group, *, safe: bool = False) -> Recipient | None:
    raw = _safe(
        lambda: decrypt_field(group.recipient_encrypted, aad=_aad("schedule_groups.recipient", group.id)),
        "schedule_groups.recipient", group.id, safe,
    )
    if not raw:
        return None
    data = json.loads(raw)
    return Recipient(chat_id=data["chat_id"], input=data.get("input") or data["chat_id"], name=data.get("name"))


# ---- Mensagem de uma automação (`AutomationMessage`) ------------------------- #
def seal_automation_message(message, text: str) -> None:
    sealed = seal(text, aad=_aad("automation_messages.message", message.id))
    message.message_ciphertext = sealed.ciphertext
    message.encryption_nonce = sealed.nonce
    message.encryption_key_version = sealed.key_version
    message.content_purged_at = None


def automation_message(message, *, safe: bool = False) -> str | None:
    if not message.message_ciphertext or not message.encryption_nonce:
        return None
    return _safe(
        lambda: unseal(
            message.message_ciphertext, message.encryption_nonce, message.encryption_key_version or 0,
            aad=_aad("automation_messages.message", message.id),
        ),
        "automation_messages.message", message.id, safe,
    )


# ---- Campos genéricos (faturamento, notas do CRM) --------------------------- #
def seal_field(table: str, column: str, row_id: str, value: str | None) -> str | None:
    return encrypt_field(value, aad=_aad(f"{table}.{column}", row_id))


def open_field(table: str, column: str, row_id: str, envelope: str | None, *, safe: bool = False) -> str | None:
    return _safe(
        lambda: decrypt_field(envelope, aad=_aad(f"{table}.{column}", row_id)), f"{table}.{column}", row_id, safe
    )


# ---- Notas do CRM administrativo (escritas PELO admin sobre a relação comercial) #
def seal_crm_note(note, body: str) -> None:
    note.body_encrypted = encrypt_field(body, aad=_aad("crm_notes.body", note.id))


def crm_note_body(note) -> str:
    return _safe(
        lambda: decrypt_field(note.body_encrypted, aad=_aad("crm_notes.body", note.id)), "crm_notes.body", note.id, True
    ) or ""
