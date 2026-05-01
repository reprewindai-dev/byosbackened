"""Signed offline license cache for buyer deployments."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from license.client_verifier import LicenseVerificationError, VerifiedLicense, verify_signed_license_response


def write_signed_cache(path: Path, envelope: dict[str, Any], verified: VerifiedLicense) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cache = {
        "cached_at": verified.checked_at.isoformat(),
        "license_id": verified.license_id,
        "workspace_id": verified.workspace_id,
        "status": verified.status,
        "signed_license": envelope,
    }
    path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def read_signed_cache(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    envelope = payload.get("signed_license")
    return envelope if isinstance(envelope, dict) else None


def verify_signed_cache(
    path: Path,
    *,
    public_key_text: str,
    machine_fingerprint: str,
    package_name: str,
    package_version: str,
    now: datetime | None = None,
) -> VerifiedLicense:
    now = now or datetime.now(timezone.utc)
    envelope = read_signed_cache(path)
    if not envelope:
        raise LicenseVerificationError("signed offline cache is missing")
    verified = verify_signed_license_response(
        envelope,
        public_key_text=public_key_text,
        machine_fingerprint=machine_fingerprint,
        package_name=package_name,
        package_version=package_version,
        now=now,
    )
    if not verified.offline_until or now > verified.offline_until:
        raise LicenseVerificationError("offline license cache expired")
    return verified
