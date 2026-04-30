"""Edge control endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/edge", tags=["Edge"])


@router.get("/control/status")
async def edge_status():
    """Health-style edge control status endpoint."""
    return {"status": "running", "capabilities": ["webhook", "rules_engine"]}
