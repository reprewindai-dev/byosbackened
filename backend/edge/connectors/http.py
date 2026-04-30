"""HTTP/Webhook input connector."""

from __future__ import annotations

from typing import Any

from edge.schemas.edge_message import EdgeMessage


def normalize_http_payload(payload: dict[str, Any]) -> EdgeMessage:
    """Normalize an incoming webhook payload."""
    return EdgeMessage.normalize(payload, protocol="http")
