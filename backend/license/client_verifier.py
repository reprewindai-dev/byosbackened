"""Buyer-side signed license verification.

The buyer backend must not trust raw JSON from a license endpoint. The server
returns an Ed25519-signed envelope, and the buyer package contains only the
public verification key.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ACTIVE_STATUSES = {"active", "trial", "grace", "payment_failed"}
BLOCKED_STATUSES = {"revoked", "deactivated", "disabled", "expired", "invalid"}


@dataclass(slots=True)
class VerifiedLicense:
    valid: bool
    status: str
    reason: str
    payload: dict[str, Any]
    checked_at: datetime
    tier: str = ""
    workspace_id: str = ""
    license_id: str = ""
    features: dict[str, Any] | None = None
    expires_at: datetime | None = None
    grace_until: datetime | None = None
    offline_until: datetime | None = None


class LicenseVerificationError(RuntimeError):
    """Raised when a signed license cannot be trusted."""


def canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def load_public_key(public_key_text: str) -> Ed25519PublicKey:
    text = (public_key_text or "").strip()
    if not text:
        raise LicenseVerificationError("license public key is missing")
    try:
        if "BEGIN PUBLIC KEY" in text:
            key = serialization.load_pem_public_key(text.encode("utf-8"))
        else:
            key = Ed25519PublicKey.from_public_bytes(base64.b64decode(text))
    except Exception as exc:
        raise LicenseVerificationError("license public key is invalid") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise LicenseVerificationError("license public key must be Ed25519")
    return key


def verify_signed_payload(envelope: dict[str, Any], public_key_text: str) -> dict[str, Any]:
    payload = envelope.get("payload")
    signature = str(envelope.get("signature") or "")
    if not isinstance(payload, dict):
        raise LicenseVerificationError("signed license payload is missing")
    if not signature:
        raise LicenseVerificationError("signed license signature is missing")

    public_key = load_public_key(public_key_text)
    try:
        public_key.verify(base64.b64decode(signature), canonical_json(payload))
    except (InvalidSignature, ValueError) as exc:
        raise LicenseVerificationError("signed license signature is invalid") from exc
    return payload


def verify_signed_license_response(
    envelope: dict[str, Any],
    *,
    public_key_text: str,
    machine_fingerprint: str,
    package_name: str,
    package_version: str,
    now: datetime | None = None,
) -> VerifiedLicense:
    """Verify a signed license envelope and apply local enforcement rules."""
    now = now or datetime.now(timezone.utc)
    payload = verify_signed_payload(envelope, public_key_text)
    status = str(payload.get("status") or "invalid").lower()
    expires_at = parse_dt(payload.get("expires_at"))
    grace_until = parse_dt(payload.get("grace_until"))
    offline_until = parse_dt(payload.get("offline_until"))

    if str(payload.get("machine_fingerprint") or "") != machine_fingerprint:
        raise LicenseVerificationError("license machine fingerprint mismatch")
    if str(payload.get("package_name") or "") != package_name:
        raise LicenseVerificationError("license package mismatch")
    if str(payload.get("package_version") or "") != package_version:
        raise LicenseVerificationError("license package version mismatch")
    if status in BLOCKED_STATUSES:
        raise LicenseVerificationError(f"license status is blocked: {status}")
    if status not in ACTIVE_STATUSES:
        raise LicenseVerificationError(f"license status is not allowed: {status}")

    if expires_at and now > expires_at:
        if grace_until and now <= grace_until:
            status = "grace"
        else:
            raise LicenseVerificationError("license expired outside grace window")

    if status == "payment_failed":
        if not grace_until or now > grace_until:
            raise LicenseVerificationError("payment failed outside grace window")

    return VerifiedLicense(
        valid=True,
        status=status,
        reason="signed_license_valid",
        payload=payload,
        checked_at=now,
        tier=str(payload.get("tier") or ""),
        workspace_id=str(payload.get("workspace_id") or ""),
        license_id=str(payload.get("license_id") or ""),
        features=payload.get("features") if isinstance(payload.get("features"), dict) else {},
        expires_at=expires_at,
        grace_until=grace_until,
        offline_until=offline_until,
    )
