"""Edge engine pipeline utilities."""

from __future__ import annotations

from edge.services.edge_processor import process_edge_data


async def run_pipeline(payload: dict):
    """Process a payload through edge rules and routing."""
    return await process_edge_data(payload)
