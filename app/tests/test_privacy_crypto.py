"""privacy.py: AES-256-GCM com AAD por linha, chaves versionadas e HMAC por usuário."""

import base64
import os
from types import SimpleNamespace

import pytest

from whatsapp_scheduler import privacy
from whatsapp_scheduler.config import settings


def _key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


@pytest.fixture
def keyring(monkeypatch):
    """Troca as chaves durante o teste e restaura depois."""

    def use(keys: str, hash_key: str | None = None, active: int | None = None):
        monkeypatch.setattr(settings, "data_encryption_keys", keys)
        monkeypatch.setattr(settings, "data_encryption_active_version", active)
        if hash_key is not None:
            monkeypatch.setattr(settings, "data_hash_key", hash_key)
        privacy.reset_key_cache()

    yield use
    monkeypatch.undo()
    privacy.reset_key_cache()


def test_seal_roundtrip_and_ciphertext_is_not_plaintext():
    sealed = privacy.seal("Olá João, sua consulta é amanhã.", aad="attena:test:1")
    assert "João" not in sealed.ciphertext and "consulta" not in base64.b64decode(sealed.ciphertext).decode("latin1")
    assert privacy.unseal(sealed.ciphertext, sealed.nonce, sealed.key_version, aad="attena:test:1") == (
        "Olá João, sua consulta é amanhã."
    )


def test_every_seal_uses_a_fresh_nonce():
    a = privacy.seal("mesmo texto", aad="x")
    b = privacy.seal("mesmo texto", aad="x")
    assert a.nonce != b.nonce and a.ciphertext != b.ciphertext


def test_ciphertext_copied_to_another_row_does_not_decrypt():
    """AAD = identidade da linha: copiar o ciphertext do usuário A para a linha do B falha."""
    row_a = SimpleNamespace(id="row-a", user_id="user-a")
    row_b = SimpleNamespace(id="row-b", user_id="user-b")
    privacy.seal_schedule_message(row_a, "segredo de A")
    row_b.message_ciphertext, row_b.encryption_nonce, row_b.encryption_key_version = (
        row_a.message_ciphertext, row_a.encryption_nonce, row_a.encryption_key_version,
    )
    with pytest.raises(privacy.DecryptionError):
        privacy.schedule_message(row_b)
    assert privacy.schedule_message(row_b, safe=True) is None


def test_tampered_ciphertext_is_rejected():
    sealed = privacy.seal("texto", aad="a")
    raw = bytearray(base64.b64decode(sealed.ciphertext))
    raw[0] ^= 0x01
    with pytest.raises(privacy.DecryptionError):
        privacy.unseal(base64.b64encode(bytes(raw)).decode(), sealed.nonce, sealed.key_version, aad="a")


def test_key_rotation_old_versions_still_decrypt(keyring):
    old, new = _key(), _key()
    keyring(f"1:{old}")
    envelope_v1 = privacy.encrypt_field("antigo", aad="r")
    keyring(f"1:{old},2:{new}")
    assert privacy.envelope_version(envelope_v1) == 1
    assert privacy.decrypt_field(envelope_v1, aad="r") == "antigo"  # versão antiga continua legível
    envelope_v2 = privacy.encrypt_field("novo", aad="r")
    assert privacy.envelope_version(envelope_v2) == 2  # dado novo usa a maior versão
    keyring(f"2:{new}")  # a versão 1 foi removida
    with pytest.raises(privacy.DecryptionError):
        privacy.decrypt_field(envelope_v1, aad="r")


def test_wrong_key_cannot_decrypt(keyring):
    keyring(f"1:{_key()}")
    envelope = privacy.encrypt_field("x", aad="r")
    keyring(f"1:{_key()}")
    with pytest.raises(privacy.DecryptionError):
        privacy.decrypt_field(envelope, aad="r")


@pytest.mark.parametrize(
    "keys",
    ["", "abc", "1:naoebase64!!", "1:" + base64.b64encode(os.urandom(16)).decode(), "0:" + base64.b64encode(os.urandom(32)).decode()],
)
def test_invalid_or_missing_keys_refuse_to_start(keyring, keys):
    keyring(keys)
    with pytest.raises(privacy.KeyConfigurationError):
        privacy.check_configuration()


def test_missing_hash_key_refuses_to_start(keyring):
    keyring(f"1:{_key()}", hash_key="")
    with pytest.raises(privacy.KeyConfigurationError):
        privacy.check_configuration()


def test_keys_can_come_from_a_secret_file(tmp_path, monkeypatch):
    secret = tmp_path / "keys"
    secret.write_text(f"1:{_key()}\n")
    monkeypatch.setattr(settings, "data_encryption_keys", "")
    monkeypatch.setattr(settings, "data_encryption_keys_file", str(secret))
    privacy.reset_key_cache()
    try:
        assert privacy.decrypt_field(privacy.encrypt_field("ok", aad="f"), aad="f") == "ok"
    finally:
        monkeypatch.undo()
        privacy.reset_key_cache()


def test_recipient_hash_is_hmac_scoped_per_user_and_never_the_number():
    a = privacy.recipient_hash("user-a", "5514999999999@c.us")
    assert a == privacy.recipient_hash("user-a", "5514999999999@c.us")  # determinístico (buscas)
    assert a != privacy.recipient_hash("user-b", "5514999999999@c.us")  # não cruza clientes
    assert "5514999999999" not in a and len(a) == 64
    import hashlib

    assert a != hashlib.sha256(b"5514999999999@c.us").hexdigest()  # não é SHA-256 puro


def test_group_recipient_roundtrip():
    group = SimpleNamespace(id="g1", user_id="u1")
    privacy.seal_group_recipient(group, chat_id="5514999999999@c.us", recipient_input="+55 14 99999-9999", recipient_name="João")
    assert "João" not in group.recipient_encrypted and "5514999999999" not in group.recipient_encrypted
    info = privacy.group_recipient(group)
    assert (info.chat_id, info.input, info.name, info.phone, info.display) == (
        "5514999999999@c.us", "+55 14 99999-9999", "João", "+5514999999999", "João"
    )
