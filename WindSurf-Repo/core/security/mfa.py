"""Multi-Factor Authentication (MFA/2FA) support."""

import pyotp
import qrcode
import io
import base64
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models.user import User
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class MFAService:
    """Multi-Factor Authentication service."""

    def __init__(self):
        self.issuer_name = settings.app_name or "BYOS AI Backend"

    def generate_secret(self, user_email: str) -> str:
        """Generate TOTP secret for user."""
        return pyotp.random_base32()

    def generate_qr_code(self, user_email: str, secret: str) -> str:
        """Generate QR code for MFA setup."""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name,
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Convert to base64
        img_base64 = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_base64}"

    def verify_totp(self, secret: str, token: str) -> bool:
        """Verify TOTP token."""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)  # Allow 1 time step tolerance
        except Exception as e:
            logger.error(f"MFA verification error: {e}")
            return False

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for MFA."""
        import secrets

        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8-character hex code
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes

    def verify_backup_code(self, code: str, backup_codes: List[str]) -> tuple[bool, List[str]]:
        """Verify backup code and remove it from list."""
        # Normalize code (remove dashes, uppercase)
        normalized_code = code.replace("-", "").upper()

        for backup_code in backup_codes:
            normalized_backup = backup_code.replace("-", "").upper()
            if normalized_code == normalized_backup:
                # Remove used code
                backup_codes.remove(backup_code)
                return True, backup_codes

        return False, backup_codes


# Add MFA fields to User model (via migration)
# mfa_enabled: bool = False
# mfa_secret: Optional[str] = None
# mfa_backup_codes: Optional[List[str]] = None
