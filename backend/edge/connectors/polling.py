"""Polling connector stubs for future implementation."""

from __future__ import annotations

from typing import Any

from edge.schemas.edge_message import EdgeMessage


def normalize_polling_payload(payload: dict[str, Any]) -> EdgeMessage:
    """Normalize polling payload shape into the shared edge message model."""
    return EdgeMessage.normalize(payload, source=payload.get("source") or "polling", protocol="polling")
