"""Edge engine executor."""

from __future__ import annotations

from edge.services.edge_processor import process_edge_payload
from edge.schemas.edge_message import EdgeMessage


async def execute(msg: EdgeMessage):
    """Execute an already normalized EdgeMessage."""
    return await process_edge_payload(msg)
