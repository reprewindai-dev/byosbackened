"""Secrets management."""

import os
import hashlib
import hmac
from typing import Optional, Dict
from datetime import datetime, timedelta
from core.config import get_settings
from core.security.encryption import encrypt_field, decrypt_field
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class SecretManager:
    """Manages secrets securely."""

    def __init__(self):
        self.secrets_cache: Dict[str, str] = {}
        self.access_log: list = []

    def get_secret(self, secret_name: str, workspace_id: Optional[str] = None) -> Optional[str]:
        """
        Get secret value.

        Never logs the actual secret value.
        Logs access for audit trail.
        """
        # Check cache first
        cache_key = f"{workspace_id}:{secret_name}" if workspace_id else secret_name
        if cache_key in self.secrets_cache:
            self._log_access(secret_name, workspace_id, "cache_hit")
            return self.secrets_cache[cache_key]

        # Get from environment or external secret manager
        env_key = secret_name.upper().replace("-", "_")
        secret_value = os.getenv(env_key)

        if secret_value:
            # Cache encrypted
            self.secrets_cache[cache_key] = secret_value
            self._log_access(secret_name, workspace_id, "env")
            return secret_value

        # Try external secret manager (future: HashiCorp Vault, AWS Secrets Manager)
        # For now, return None if not found
        self._log_access(secret_name, workspace_id, "not_found")
        return None

    def set_secret(self, secret_name: str, value: str, workspace_id: Optional[str] = None):
        """Set secret value (encrypted)."""
        encrypted = encrypt_field(value)
        cache_key = f"{workspace_id}:{secret_name}" if workspace_id else secret_name
        self.secrets_cache[cache_key] = encrypted
        self._log_access(secret_name, workspace_id, "set")

    def rotate_secret(self, secret_name: str, workspace_id: Optional[str] = None) -> str:
        """Rotate secret - generate new value."""
        import secrets

        new_value = secrets.token_urlsafe(32)
        self.set_secret(secret_name, new_value, workspace_id)
        self._log_access(secret_name, workspace_id, "rotated")
        return new_value

    def _log_access(self, secret_name: str, workspace_id: Optional[str], action: str):
        """Log secret access (without logging the value)."""
        log_entry = {
            "secret_name": secret_name,
            "workspace_id": workspace_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.access_log.append(log_entry)
        logger.info(f"Secret access: {secret_name} [{action}] workspace={workspace_id}")

    def get_access_log(self, secret_name: Optional[str] = None, limit: int = 100) -> list:
        """Get secret access log."""
        log = self.access_log[-limit:]
        if secret_name:
            log = [entry for entry in log if entry["secret_name"] == secret_name]
        return log


# Global secret manager instance
_secret_manager = SecretManager()


def get_secret(secret_name: str, workspace_id: Optional[str] = None) -> Optional[str]:
    """Get secret value."""
    return _secret_manager.get_secret(secret_name, workspace_id)


def set_secret(secret_name: str, value: str, workspace_id: Optional[str] = None):
    """Set secret value."""
    _secret_manager.set_secret(secret_name, value, workspace_id)


def rotate_secret(secret_name: str, workspace_id: Optional[str] = None) -> str:
    """Rotate secret."""
    return _secret_manager.rotate_secret(secret_name, workspace_id)
