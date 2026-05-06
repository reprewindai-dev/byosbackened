"""Kill switch API endpoints for emergency cost control."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id, require_admin
from core.cost_intelligence.kill_switch import get_cost_kill_switch
from core.redis_pool import get_redis
from db.models import User
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/cost", tags=["cost-intelligence"])

# Redis key for kill switch state (per-workspace)
KILL_SWITCH_KEY = "kill_switch:{workspace_id}"


class KillSwitchRequest(BaseModel):
    """Kill switch activation request."""
    reason: str = Field(..., min_length=5, max_length=500, description="Reason for activation (min 5 chars)")
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Auto-restore after N minutes (1-1440)")


class KillSwitchResponse(BaseModel):
    """Kill switch status response."""
    killed: bool  # True = AI calls are blocked
    reason: Optional[str] = None
    activated_at: Optional[str] = None
    activated_by: Optional[str] = None
    auto_restore_at: Optional[str] = None


def _get_redis_state(redis, workspace_id: str) -> dict:
    """Get kill switch state from Redis."""
    key = KILL_SWITCH_KEY.format(workspace_id=workspace_id)
    data = redis.hgetall(key)
    if not data:
        return {"killed": False, "reason": None, "activated_at": None, "activated_by": None, "auto_restore_at": None}
    return {
        "killed": data.get(b"killed", b"false").decode() == "true",
        "reason": data.get(b"reason", b"").decode() or None,
        "activated_at": data.get(b"activated_at", b"").decode() or None,
        "activated_by": data.get(b"activated_by", b"").decode() or None,
        "auto_restore_at": data.get(b"auto_restore_at", b"").decode() or None,
    }


def _set_redis_state(redis, workspace_id: str, state: dict):
    """Set kill switch state in Redis."""
    key = KILL_SWITCH_KEY.format(workspace_id=workspace_id)
    if state.get("killed"):
        redis.hset(key, mapping={
            "killed": "true",
            "reason": state.get("reason", ""),
            "activated_at": state.get("activated_at", ""),
            "activated_by": state.get("activated_by", ""),
            "auto_restore_at": state.get("auto_restore_at", ""),
        })
    else:
        redis.delete(key)


@router.post("/kill-switch", response_model=KillSwitchResponse)
async def activate_kill_switch(
    request: KillSwitchRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    current_user: User = Depends(require_admin),
    redis = Depends(get_redis),
):
    """
    Emergency kill switch - blocks all AI calls for workspace.

    Immediately returns HTTP 402 on all future AI requests until deactivated.
    Use this for runaway usage, suspected abuse, or emergency cost control.
    """
    # Check if already killed
    current = _get_redis_state(redis, workspace_id)
    if current["killed"]:
        return KillSwitchResponse(**current)

    now = datetime.utcnow().isoformat()
    auto_restore = None
    if request.duration_minutes:
        auto_restore = (datetime.utcnow() + timedelta(minutes=request.duration_minutes)).isoformat()

    state = {
        "killed": True,
        "reason": request.reason,
        "activated_at": now,
        "activated_by": current_user.id,
        "auto_restore_at": auto_restore,
    }
    _set_redis_state(redis, workspace_id, state)

    return KillSwitchResponse(**state)


@router.delete("/kill-switch", response_model=KillSwitchResponse)
async def deactivate_kill_switch(
    workspace_id: str = Depends(get_current_workspace_id),
    current_user: User = Depends(require_admin),
    redis = Depends(get_redis),
):
    """
    Deactivate kill switch - re-enable normal AI operations.
    """
    # Clear the killed state
    _set_redis_state(redis, workspace_id, {"killed": False})

    return KillSwitchResponse(
        killed=False,
        reason=None,
        activated_at=None,
        activated_by=None,
        auto_restore_at=None,
    )


@router.get("/kill-switch/status", response_model=KillSwitchResponse)
async def get_kill_switch_status(
    workspace_id: str = Depends(get_current_workspace_id),
    current_user: User = Depends(require_admin),
):
    """
    Get current kill switch status.
    """
    try:
        redis = get_redis()
        state = _get_redis_state(redis, workspace_id)

        # Auto-restore check
        if state["killed"] and state.get("auto_restore_at"):
            try:
                restore_time = datetime.fromisoformat(state["auto_restore_at"])
                if datetime.utcnow() >= restore_time:
                    # Auto-restore triggered
                    _set_redis_state(redis, workspace_id, {"killed": False})
                    return KillSwitchResponse(killed=False)
            except (ValueError, TypeError):
                pass  # Invalid timestamp, ignore

        return KillSwitchResponse(**state)
    except Exception:
        # Redis unavailable — report not killed (fail-open)
        return KillSwitchResponse(killed=False)
