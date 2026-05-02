"""Budget management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.cost_intelligence import BudgetTracker
from db.models import Budget
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/budget", tags=["budget"])
budget_tracker = BudgetTracker()


class BudgetRequest(BaseModel):
    """Budget creation/update request."""

    budget_type: str  # "daily", "monthly", "project", "client"
    amount: Decimal
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    alert_thresholds: Optional[list[int]] = [50, 80, 95]


@router.post("")
async def create_budget(
    request: BudgetRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create or update budget."""
    # Set default period if not provided
    period_start = request.period_start or datetime.utcnow()
    if request.budget_type == "daily":
        period_end = period_start + timedelta(days=1)
    elif request.budget_type == "monthly":
        period_end = period_start + timedelta(days=30)
    else:
        period_end = request.period_end or period_start + timedelta(days=30)
    
    # Check if budget exists
    existing = db.query(Budget).filter(
        Budget.workspace_id == workspace_id,
        Budget.budget_type == request.budget_type,
    ).first()
    
    if existing:
        # Update existing
        existing.amount = request.amount
        existing.period_start = period_start
        existing.period_end = period_end
        existing.alerts_sent = request.alert_thresholds
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "message": "Budget updated",
            "budget_type": existing.budget_type,
            "amount": str(existing.amount),
            "current_spend": str(existing.current_spend),
            "remaining": str(existing.amount - existing.current_spend),
        }
    else:
        # Create new
        budget = Budget(
            workspace_id=workspace_id,
            budget_type=request.budget_type,
            amount=request.amount,
            period_start=period_start,
            period_end=period_end,
            alerts_sent=request.alert_thresholds,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        return {
            "id": budget.id,
            "message": "Budget created",
            "budget_type": budget.budget_type,
            "amount": str(budget.amount),
            "current_spend": "0.00",
            "remaining": str(budget.amount),
        }


@router.get("")
async def get_budget_status(
    workspace_id: str = Depends(get_current_workspace_id),
    budget_type: Optional[str] = None,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Max budgets to return"),
):
    """Get budget status."""
    query = db.query(Budget).filter(Budget.workspace_id == workspace_id)
    if budget_type:
        query = query.filter(Budget.budget_type == budget_type)
    
    budgets = query.limit(limit).all()
    
    return [
        {
            "id": b.id,
            "budget_type": b.budget_type,
            "amount": str(b.amount),
            "current_spend": str(b.current_spend or Decimal("0")),
            "remaining": str(b.amount - (b.current_spend or Decimal("0"))),
            "percent_used": float((((b.current_spend or Decimal("0")) / b.amount) * 100) if b.amount > 0 else 0),
            "forecast_exhaustion_date": b.forecast_exhaustion_date.isoformat() if b.forecast_exhaustion_date else None,
            "period_start": b.period_start.isoformat(),
            "period_end": b.period_end.isoformat(),
        }
        for b in budgets
    ]


@router.get("/forecast")
async def get_budget_forecast(
    workspace_id: str = Depends(get_current_workspace_id),
    budget_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """Get budget forecast."""
    budget = db.query(Budget).filter(
        Budget.workspace_id == workspace_id,
        Budget.budget_type == budget_type,
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    
    # Check budget
    check = budget_tracker.check_budget(db, workspace_id, Decimal("0"), budget_type)
    
    return {
        "budget_type": budget_type,
        "current_spend": str(check.current_spend),
        "budget_limit": str(check.budget_limit),
        "remaining": str(check.remaining),
        "forecast_exhaustion_date": check.forecast_exhaustion_date.isoformat() if check.forecast_exhaustion_date else None,
        "alert_level": check.alert_level,
    }
