"""Security module."""

from core.security.encryption import encrypt_field, decrypt_field, generate_key
from core.security.secrets import get_secret, rotate_secret, SecretManager

# Import from parent module file directly to avoid circular import
import importlib.util
from pathlib import Path

_parent_security = Path(__file__).parent.parent / "security.py"
if _parent_security.exists():
    spec = importlib.util.spec_from_file_location("core_security_parent", _parent_security)
    security_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(security_module)
    decode_access_token = security_module.decode_access_token
    get_password_hash = security_module.get_password_hash
    verify_password = security_module.verify_password
    create_access_token = security_module.create_access_token
else:
    # Fallback: try direct import
    from core import security as security_module

    decode_access_token = security_module.decode_access_token
    get_password_hash = security_module.get_password_hash
    verify_password = security_module.verify_password
    create_access_token = security_module.create_access_token

# Import zero_trust after other imports to avoid circular dependency
from core.security.zero_trust import ZeroTrustMiddleware

__all__ = [
    "ZeroTrustMiddleware",
    "encrypt_field",
    "decrypt_field",
    "generate_key",
    "get_secret",
    "rotate_secret",
    "SecretManager",
    "decode_access_token",
    "get_password_hash",
    "verify_password",
    "create_access_token",
]
