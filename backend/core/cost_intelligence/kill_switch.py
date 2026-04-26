"""Cost kill switch - emergency budget caps and shutdown."""
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import Budget
from core.config import get_settings
import os
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class CostKillSwitch:
    """
    Emergency cost kill switch.
    
    Provides hard budget caps and emergency shutdown capabilities.
    """
    
    # Global daily cap (emergency limit)
    GLOBAL_DAILY_CAP = Decimal(os.getenv("GLOBAL_DAILY_COST_CAP", "10000.00"))
    
    # Per-workspace daily cap (default)
    DEFAULT_WORKSPACE_DAILY_CAP = Decimal(os.getenv("DEFAULT_WORKSPACE_DAILY_CAP", "1000.00"))
    
    def __init__(self):
        self._enabled = os.getenv("COST_KILL_SWITCH_ENABLED", "true").lower() == "true"
        self._global_spend_today = Decimal("0")
        self._last_reset = datetime.utcnow().date()
    
    def check_global_cap(self, db: Session, operation_cost: Decimal) -> Dict[str, Any]:
        """
        Check global daily cost cap.
        
        Returns dict with allowed status and details.
        """
        if not self._enabled:
            return {
                "allowed": True,
                "reason": "kill_switch_disabled",
            }
        
        # Reset daily counter if new day
        today = datetime.utcnow().date()
        if today > self._last_reset:
            self._global_spend_today = Decimal("0")
            self._last_reset = today
        
        # Check global cap
        new_total = self._global_spend_today + operation_cost
        if new_total > self.GLOBAL_DAILY_CAP:
            logger.critical(
                f"GLOBAL COST CAP EXCEEDED: ${new_total} > ${self.GLOBAL_DAILY_CAP}. "
                f"Rejecting operation."
            )
            return {
                "allowed": False,
                "reason": "global_daily_cap_exceeded",
                "current_spend": self._global_spend_today,
                "cap": self.GLOBAL_DAILY_CAP,
                "operation_cost": operation_cost,
            }
        
        return {
            "allowed": True,
            "current_spend": self._global_spend_today,
            "cap": self.GLOBAL_DAILY_CAP,
            "remaining": self.GLOBAL_DAILY_CAP - self._global_spend_today,
        }
    
    def check_workspace_cap(
        self,
        db: Session,
        workspace_id: str,
        operation_cost: Decimal,
    ) -> Dict[str, Any]:
        """
        Check workspace daily cost cap.
        
        Returns dict with allowed status and details.
        """
        if not self._enabled:
            return {
                "allowed": True,
                "reason": "kill_switch_disabled",
            }
        
        # Get or create daily budget for workspace
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        daily_budget = db.query(Budget).filter(
            Budget.workspace_id == workspace_id,
            Budget.budget_type == "daily",
            Budget.period_start >= today_start,
            Budget.period_end <= today_end,
        ).first()
        
        # Use default cap if no budget set
        cap = self.DEFAULT_WORKSPACE_DAILY_CAP
        current_spend = Decimal("0")
        
        if daily_budget:
            cap = daily_budget.amount
            current_spend = daily_budget.current_spend
        
        # Check cap
        new_spend = current_spend + operation_cost
        if new_spend > cap:
            logger.critical(
                f"WORKSPACE COST CAP EXCEEDED: workspace={workspace_id}, "
                f"${new_spend} > ${cap}. Rejecting operation."
            )
            return {
                "allowed": False,
                "reason": "workspace_daily_cap_exceeded",
                "workspace_id": workspace_id,
                "current_spend": current_spend,
                "cap": cap,
                "operation_cost": operation_cost,
            }
        
        return {
            "allowed": True,
            "workspace_id": workspace_id,
            "current_spend": current_spend,
            "cap": cap,
            "remaining": cap - current_spend,
        }
    
    def record_cost(self, cost: Decimal):
        """Record cost for global tracking."""
        self._global_spend_today += cost
    
    def disable(self):
        """Disable kill switch (emergency override)."""
        self._enabled = False
        logger.critical("Cost kill switch DISABLED (emergency override)")
    
    def enable(self):
        """Enable kill switch."""
        self._enabled = True
        logger.info("Cost kill switch ENABLED")


# Global kill switch
_cost_kill_switch = CostKillSwitch()


def get_cost_kill_switch() -> CostKillSwitch:
    """Get global cost kill switch instance."""
    return _cost_kill_switch
