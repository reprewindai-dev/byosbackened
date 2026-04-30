"""API output adapter for non-alert edge messages."""

from __future__ import annotations

from datetime import datetime

from edge.schemas.edge_message import EdgeMessage


async def store(msg: EdgeMessage) -> dict:
    """Persist/store message shape hook.

    This is intentionally lightweight in phase 1 and returns a normalized result
    that downstream services can consume.
    """
    return {
        "status": "processed",
        "route": "edge_api",
        "workspace": msg.source,
        "protocol": msg.protocol,
        "metadata": msg.metadata,
        "timestamp": datetime.utcnow().isoformat(),
        "data": msg.payload,
    }
