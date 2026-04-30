"""Data encryption utilities."""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import binascii
import os
from typing import Optional
from core.config import get_settings

settings = get_settings()


def generate_key(password: Optional[bytes] = None, salt: Optional[bytes] = None) -> bytes:
    """Generate encryption key from password or random."""
    if password is None:
        return Fernet.generate_key()

    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def get_encryption_key() -> bytes:
    """Get encryption key from settings or generate."""
    encryption_key = getattr(settings, "encryption_key", None)
    if encryption_key:
        key_text = encryption_key.decode() if isinstance(encryption_key, bytes) else str(encryption_key)
        key_text = key_text.strip()
        try:
            decoded = base64.urlsafe_b64decode(key_text.encode())
            if len(decoded) == 32 and base64.urlsafe_b64encode(decoded).decode().rstrip("=") == key_text.rstrip("="):
                return key_text.encode()
        except Exception:
            pass

        try:
            raw = binascii.unhexlify(key_text)
            if len(raw) == 32:
                return base64.urlsafe_b64encode(raw)
        except (binascii.Error, ValueError):
            pass

        if len(key_text.encode()) == 32:
            return base64.urlsafe_b64encode(key_text.encode())
        return generate_key(key_text.encode())
    # Fallback: use secret_key (not ideal, but works)
    return generate_key(settings.secret_key.encode())


def encrypt_field(value: str) -> str:
    """Encrypt a field value."""
    if not value:
        return value

    key = get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_field(encrypted_value: str) -> str:
    """Decrypt a field value."""
    if not encrypted_value:
        return encrypted_value

    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        decoded = base64.urlsafe_b64decode(encrypted_value.encode())
        decrypted = fernet.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt field: {str(e)}")


def encrypt_data(data: bytes) -> bytes:
    """Encrypt binary data."""
    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.encrypt(data)


def decrypt_data(encrypted_data: bytes) -> bytes:
    """Decrypt binary data."""
    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data)
