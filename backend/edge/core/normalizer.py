"""Normalization primitives for legacy protocol connectors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _coerce_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize(
    protocol: str,
    source: str,
    metric: str,
    value,
    *,
    units: str | None = None,
    raw: dict | None = None,
    tags: dict | None = None,
    timestamp: str | None = None,
) -> dict:
    """Normalize protocol payloads into a standard edge event shape."""
    return {
        "protocol": str(protocol),
        "source": str(source),
        "metric": str(metric),
        "value": _coerce_value(value),
        "units": units,
        "timestamp": timestamp or _utc_now_iso(),
        "raw": dict(raw or {}),
        "tags": dict(tags or {}),
    }
