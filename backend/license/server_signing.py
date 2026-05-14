"""License-server Ed25519 signing helpers.

Private signing keys are server-only and excluded from buyer packages.
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def load_private_key() -> Ed25519PrivateKey:
    material = os.getenv("VEKLOM_LICENSE_SIGNING_PRIVATE_KEY", "").strip()
    if not material:
        raise RuntimeError("VEKLOM_LICENSE_SIGNING_PRIVATE_KEY is required on license server")
    if "BEGIN PRIVATE KEY" in material:
        key = serialization.load_pem_private_key(material.encode("utf-8"), password=None)
    else:
        key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(material))
    if not isinstance(key, Ed25519PrivateKey):
        raise RuntimeError("License signing key must be Ed25519")
    return key


def sign_license_payload(payload: dict[str, Any], private_key: Ed25519PrivateKey | None = None) -> dict[str, Any]:
    key = private_key or load_private_key()
    signature = base64.b64encode(key.sign(_canonical_json(payload))).decode("ascii")
    return {
        "alg": "Ed25519",
        "payload": payload,
        "signature": signature,
    }


def build_license_payload(
    *,
    license_id: str,
    workspace_id: str,
    tier: str,
    features: dict[str, Any],
    machine_fingerprint: str,
    package_name: str,
    package_version: str,
    status: str,
    expires_at: datetime | None,
    grace_until: datetime | None = None,
    offline_until: datetime | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    offline_until = offline_until or (now + timedelta(days=7))
    return {
        "license_id": license_id,
        "workspace_id": workspace_id,
        "tier": tier,
        "features": features,
        "machine_fingerprint": machine_fingerprint,
        "package_name": package_name,
        "package_version": package_version,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "grace_until": grace_until.isoformat() if grace_until else None,
        "offline_until": offline_until.isoformat(),
        "status": status,
    }
