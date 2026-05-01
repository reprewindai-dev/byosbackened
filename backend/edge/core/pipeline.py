"""Edge execution pipeline used by protocol connectors."""

from __future__ import annotations

from edge.schemas.edge_message import EdgeMessage
from edge.services.edge_router import route_message
from edge.services.edge_rules import apply_rules


def _build_message(data: dict) -> EdgeMessage:
    """Map a normalized connector payload into a full EdgeMessage."""
    metadata = {}
    if isinstance(data.get("metadata"), dict):
        metadata = dict(data["metadata"])

    # Keep both legacy and current rule shapes available for downstream compatibility.
    payload = {
        **data,
    }
    if data.get("metric") == "temperature":
        payload.setdefault("temperature", data.get("value"))

    return EdgeMessage(
        source=data.get("source", "unknown"),
        payload=payload,
        protocol=data.get("protocol", "unknown"),
        metadata=metadata,
    )


async def process_pipeline(data: dict, user):
    """
    Normalize a connector payload, apply rules, route for AI/API handling, and return output.

    The user context is passed for future entitlement/ledger hooks and to match upstream auth patterns.
    """
    _ = user
    msg = _build_message(data)
    msg = apply_rules(msg)
    return await route_message(msg)
