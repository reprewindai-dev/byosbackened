"""Buyer-side license heartbeat payloads."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_heartbeat_payload(
    *,
    license_id: str,
    workspace_id: str,
    package_version: str,
    machine_fingerprint: str,
    started_at: datetime,
    status: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    return {
        "license_id": license_id,
        "workspace_id": workspace_id,
        "package_version": package_version,
        "machine_fingerprint": machine_fingerprint,
        "started_at": started_at.isoformat(),
        "last_seen": now.isoformat(),
        "status": status,
    }
