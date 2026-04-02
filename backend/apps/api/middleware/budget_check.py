"""Budget check middleware."""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from core.cost_intelligence import BudgetTracker
from core.cost_intelligence.kill_switch import get_cost_kill_switch
from sqlalchemy.orm import Session
from db.session import SessionLocal
from core.config import get_settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
budget_tracker = BudgetTracker()
cost_kill_switch = get_cost_kill_switch()


class BudgetCheckMiddleware(BaseHTTPMiddleware):
    """Check budget before expensive operations."""

    async def dispatch(self, request: Request, call_next):
        """Check budget before processing."""
        # Only check for operations that cost money
        if not request.url.path.startswith(f"{settings.api_prefix}/transcribe") and \
           not request.url.path.startswith(f"{settings.api_prefix}/extract"):
            return await call_next(request)
        
        # Get workspace_id from request state (set by zero-trust middleware)
        workspace_id = getattr(request.state, "workspace_id", None)
        if not workspace_id:
            return await call_next(request)
        
        db = SessionLocal()
        try:
            # Estimate operation cost (conservative estimate)
            # Actual cost will be checked in endpoint, but we do a quick check here
            estimated_cost = Decimal("0.01")  # Conservative estimate
            
            # Check cost kill switch (hard caps)
            global_check = cost_kill_switch.check_global_cap(db, estimated_cost)
            if not global_check.get("allowed"):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Global daily cost cap exceeded: ${global_check.get('current_spend')} / ${global_check.get('cap')}",
                )
            
            workspace_check = cost_kill_switch.check_workspace_cap(
                db, workspace_id, estimated_cost
            )
            if not workspace_check.get("allowed"):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Workspace daily cost cap exceeded: ${workspace_check.get('current_spend')} / ${workspace_check.get('cap')}",
                    headers={"X-Budget-Remaining": str(workspace_check.get('remaining', 0))},
                )
            
            # Check monthly budget (existing check)
            check = budget_tracker.check_budget(db, workspace_id, Decimal("0"), "monthly")
            
            if check.alert_level == "exceeded":
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Budget exceeded: ${check.current_spend} / ${check.budget_limit}",
                    headers={"X-Budget-Remaining": str(check.remaining)},
                )
        finally:
            db.close()
        
        return await call_next(request)
