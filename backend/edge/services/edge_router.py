"""Edge routing engine."""

from __future__ import annotations

from edge.outputs.ai import send_to_ai
from edge.outputs.api import store


async def route_message(msg):
    """Route processed edge messages to AI or system API outputs."""
    if msg.metadata.get("alert"):
        return await send_to_ai(msg)

    return await store(msg)
