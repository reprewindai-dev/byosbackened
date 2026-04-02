"""Budget tracking and enforcement."""

from decimal import Decimal
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.models import Budget
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class BudgetCheck(BaseModel):
    """Budget check result."""

    allowed: bool
    current_spend: Decimal
    budget_limit: Decimal
    remaining: Decimal
    forecast_exhaustion_date: Optional[datetime]
    alert_level: str  # "ok", "warning", "critical", "exceeded"


class BudgetTracker:
    """Track and enforce budgets."""

    def check_budget(
        self,
        db: Session,
        workspace_id: str,
        operation_cost: Decimal,
        budget_type: str = "monthly",
    ) -> BudgetCheck:
        """
        Check if operation is allowed within budget.

        Returns budget status and forecast.
        """
        # Get budget
        budget = (
            db.query(Budget)
            .filter(
                Budget.workspace_id == workspace_id,
                Budget.budget_type == budget_type,
            )
            .first()
        )

        if not budget:
            # No budget set - allow
            return BudgetCheck(
                allowed=True,
                current_spend=Decimal("0"),
                budget_limit=Decimal("0"),
                remaining=Decimal("0"),
                forecast_exhaustion_date=None,
                alert_level="ok",
            )

        # Check if operation would exceed budget
        new_spend = budget.current_spend + operation_cost
        allowed = new_spend <= budget.amount

        # Calculate forecast
        forecast_date = self._forecast_exhaustion(
            budget.current_spend,
            budget.amount,
            budget.period_start,
            budget.period_end,
        )

        # Determine alert level
        percent_used = (budget.current_spend / budget.amount * 100) if budget.amount > 0 else 0
        if percent_used >= 100:
            alert_level = "exceeded"
        elif percent_used >= 95:
            alert_level = "critical"
        elif percent_used >= 80:
            alert_level = "warning"
        else:
            alert_level = "ok"

        return BudgetCheck(
            allowed=allowed,
            current_spend=budget.current_spend,
            budget_limit=budget.amount,
            remaining=budget.amount - budget.current_spend,
            forecast_exhaustion_date=forecast_date,
            alert_level=alert_level,
        )

    def update_budget_spend(
        self,
        db: Session,
        workspace_id: str,
        cost: Decimal,
        budget_type: str = "monthly",
    ):
        """Update budget spend (atomic)."""
        budget = (
            db.query(Budget)
            .filter(
                Budget.workspace_id == workspace_id,
                Budget.budget_type == budget_type,
            )
            .first()
        )

        if budget:
            budget.current_spend += cost
            budget.last_updated = datetime.utcnow()
            db.commit()

    def _forecast_exhaustion(
        self,
        current_spend: Decimal,
        budget_limit: Decimal,
        period_start: datetime,
        period_end: datetime,
    ) -> Optional[datetime]:
        """Forecast when budget will be exhausted."""
        if current_spend <= 0:
            return None

        # Calculate average daily spend
        days_elapsed = (datetime.utcnow() - period_start).days
        if days_elapsed <= 0:
            return None

        avg_daily_spend = current_spend / days_elapsed

        # Calculate days until exhaustion
        remaining_budget = budget_limit - current_spend
        if remaining_budget <= 0:
            return datetime.utcnow()  # Already exhausted

        if avg_daily_spend <= 0:
            return None

        days_remaining = remaining_budget / avg_daily_spend
        forecast_date = datetime.utcnow() + timedelta(days=int(days_remaining))

        # Don't forecast beyond period end
        if forecast_date > period_end:
            return period_end

        return forecast_date
