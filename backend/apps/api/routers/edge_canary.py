"""Public protocol canary summary endpoints."""
from __future__ import annotations

from fastapi import APIRouter


router = APIRouter(tags=["edge-canary"])


@router.get("/edge/canary/public")
async def public_edge_canary() -> dict:
    """Return the latest public protocol validation summary.

    The live canary runner is not active in this production path yet, so this
    endpoint reports that the proof job has not been run instead of returning a
    404 or implying successful validation.
    """
    return {
        "status": "not_run",
        "last_checked_at": None,
        "checks": {
            "snmp": "not_run",
            "modbus_tcp": "not_run",
            "mqtt": "not_run",
            "webhook": "not_run",
        },
        "proof": {
            "normalized": False,
            "decision": False,
            "audit": False,
            "cost_control": False,
        },
    }
