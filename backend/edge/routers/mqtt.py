"""MQTT endpoints (stubbed until broker integration is enabled)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/edge", tags=["Edge"])


@router.post("/control/mqtt")
async def mqtt_control():
    """Placeholder for future MQTT control endpoints."""
    raise HTTPException(status_code=501, detail="MQTT connector pending")
