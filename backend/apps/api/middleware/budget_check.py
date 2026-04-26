"""Budget check middleware."""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from core.cost_intelligence import BudgetTracker
from core.cost_intelligence.kill_switch import get_cost_kill_switch
from core.redis import get_redis
from sqlalchemy.orm import Session
from db.session import SessionLocal
from core.config import get_settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
budget_tracker = BudgetTracker()
cost_kill_switch = get_cost_kill_switch()


def is_kill_switch_active(redis, workspace_id: str) -> tuple[bool, str | None]:
    """Check if manual kill switch is active for workspace."""
    key = f"kill_switch:{workspace_id}"
    data = redis.hgetall(key)
    if not data:
        return False, None
    
    killed = data.get(b"killed", b"false").decode() == "true"
    reason = data.get(b"reason", b"").decode() or None
    
    # Check auto-restore
    if killed:
        auto_restore = data.get(b"auto_restore_at", b"").decode()
        if auto_restore:
            from datetime import datetime
            try:
                restore_time = datetime.fromisoformat(auto_restore)
                if datetime.utcnow() >= restore_time:
                    # Auto-expire
                    redis.delete(key)
                    return False, None
            except (ValueError, TypeError):
                pass
    
    return killed, reason


class BudgetCheckMiddleware(BaseHTTPMiddleware):
    """Check budget before expensive operations."""

    async def dispatch(self, request: Request, call_next):
        """Check budget before processing."""
        # Only check for operations that cost money
        path = request.url.path
        is_cost_operation = (
            path.startswith(f"{settings.api_prefix}/transcribe") or
            path.startswith(f"{settings.api_prefix}/extract") or
            path == "/v1/exec" or
            path.startswith(f"{settings.api_prefix}/exec") or
            path.startswith(f"{settings.api_prefix}/ai/") or
            path.startswith(f"{settings.api_prefix}/cost/predict")
        )
        if not is_cost_operation:
            return await call_next(request)

        # Get workspace_id from request state (set by zero-trust middleware)
        workspace_id = getattr(request.state, "workspace_id", None)
        if not workspace_id:
            return await call_next(request)

        # Check manual kill switch first (fastest path)
        try:
            redis = get_redis()
            killed, reason = is_kill_switch_active(redis, workspace_id)
            if killed:
                logger.critical(f"Kill switch ACTIVE for workspace {workspace_id}: {reason}")
                return JSONResponse(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    content={"detail": f"AI operations suspended: {reason or 'Emergency kill switch active'}"},
                    headers={"X-Kill-Switch": "active"},
                )
        except Exception as e:
            # If Redis is down, log but don't block - fail open for availability
            logger.warning(f"Could not check kill switch state: {e}")

        db = SessionLocal()
        try:
            # Estimate operation cost (conservative estimate)
            # Actual cost will be checked in endpoint, but we do a quick check here
            estimated_cost = Decimal("0.01")  # Conservative estimate

            # Check cost kill switch (hard caps)
            global_check = cost_kill_switch.check_global_cap(db, estimated_cost)
            if not global_check.get("allowed"):
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": f"Global daily cost cap exceeded: ${global_check.get('current_spend')} / ${global_check.get('cap')}"},
                )
            
            workspace_check = cost_kill_switch.check_workspace_cap(
                db, workspace_id, estimated_cost
            )
            if not workspace_check.get("allowed"):
                return JSONResponse(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    content={"detail": f"Workspace daily cost cap exceeded: ${workspace_check.get('current_spend')} / ${workspace_check.get('cap')}"},
                    headers={"X-Budget-Remaining": str(workspace_check.get('remaining', 0))},
                )
            
            # Check monthly budget (existing check)
            check = budget_tracker.check_budget(db, workspace_id, Decimal("0"), "monthly")
            
            if check.alert_level == "exceeded":
                return JSONResponse(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    content={"detail": f"Budget exceeded: ${check.current_spend} / ${check.budget_limit}"},
                    headers={"X-Budget-Remaining": str(check.remaining)},
                )
        finally:
            db.close()
        
        return await call_next(request)
