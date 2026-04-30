"""Edge ingest endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from edge.connectors.http import normalize_http_payload
from edge.schemas.edge_message import EdgeMessage
from edge.services.edge_processor import process_edge_payload, process_edge_data

router = APIRouter(prefix="/edge", tags=["Edge"])


@router.post("/input/webhook")
async def webhook_ingest(data: dict):
    """Webhook input adapter for edge payloads."""
    return await process_edge_data(data)


@router.post("/ingest")
async def ingest_edge(data: dict):
    """Generic edge ingest endpoint."""
    return await process_edge_data(data)


@router.post("/input/http")
async def ingest_http(data: dict):
    """HTTP input adapter that normalizes via connector before processing."""
    msg = normalize_http_payload(data)
    return await process_edge_payload(msg)


@router.post("/demo")
async def demo_ingest():
    """Simple demo payload for rapid integration testing."""
    sample_payload: dict = {
        "device": "sensor-1",
        "temperature": 92,
        "status": "critical",
    }
    sample_msg = EdgeMessage.normalize(sample_payload, source="sensor-1", protocol="http")
    return await process_edge_payload(sample_msg)
