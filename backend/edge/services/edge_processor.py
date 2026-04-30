"""Main edge execution pipeline."""

from __future__ import annotations

from edge.connectors.http import normalize_http_payload
from edge.schemas.edge_message import EdgeMessage
from edge.services.edge_router import route_message
from edge.services.edge_rules import apply_rules


async def process_edge_data(raw_data: dict):
    """Normalize, rule, and route a webhook payload."""
    msg = normalize_http_payload(raw_data)
    msg = apply_rules(msg)
    return await route_message(msg)


async def process_edge_payload(message: EdgeMessage):
    """Accept a pre-normalized edge message and run the same pipeline."""
    normalized = apply_rules(message)
    return await route_message(normalized)
