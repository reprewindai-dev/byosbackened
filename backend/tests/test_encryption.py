from __future__ import annotations

from cryptography.fernet import Fernet

from core.security import encryption


def test_get_encryption_key_accepts_hex_secret(monkeypatch):
    monkeypatch.setattr(
        encryption.settings,
        "encryption_key",
        "188E8E86F9F0C9A4E00C2F40595EF338",
    )

    key = encryption.get_encryption_key()

    assert key == b"MTg4RThFODZGOUYwQzlBNEUwMEMyRjQwNTk1RUYzMzg="


def test_encrypt_decrypt_field_with_hex_secret(monkeypatch):
    monkeypatch.setattr(
        encryption.settings,
        "encryption_key",
        "188E8E86F9F0C9A4E00C2F40595EF338",
    )

    encrypted = encryption.encrypt_field("hello world")
    decrypted = encryption.decrypt_field(encrypted)

    assert decrypted == "hello world"
    assert Fernet(encryption.get_encryption_key())
