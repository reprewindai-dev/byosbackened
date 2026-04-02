"""Insights endpoints - savings and optimization insights."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.autonomous.reporting.savings_calculator import get_savings_calculator
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

router = APIRouter(prefix="/insights", tags=["insights"])
savings_calculator = get_savings_calculator()


class SavingsResponse(BaseModel):
    """Savings response."""
    total_savings: str
    baseline_cost: str
    actual_cost: str
    savings_percent: float
    operations_count: int
    latency_reduction_ms: Optional[int] = None
    cache_hit_rate_improvement: Optional[float] = None
    period_start: str
    period_end: str


class ProjectedSavingsResponse(BaseModel):
    """Projected savings response."""
    projected_savings: str
    monthly_avg_savings: str
    months_ahead: int
    projected_savings_percent: float


@router.get("/savings", response_model=SavingsResponse)
async def get_savings(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """
    Get savings vs baseline for workspace.
    
    Shows exactly how much the system saved you.
    """
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    savings = savings_calculator.calculate_savings(
        workspace_id=workspace_id,
        start_date=start,
        end_date=end,
        db=db,
    )
    
    return SavingsResponse(
        total_savings=str(savings["total_savings"]),
        baseline_cost=str(savings["baseline_cost"]),
        actual_cost=str(savings["actual_cost"]),
        savings_percent=savings["savings_percent"],
        operations_count=savings["operations_count"],
        latency_reduction_ms=savings.get("latency_reduction_ms"),
        cache_hit_rate_improvement=savings.get("cache_hit_rate_improvement"),
        period_start=savings["period_start"],
        period_end=savings["period_end"],
    )


@router.get("/savings/projected", response_model=ProjectedSavingsResponse)
async def get_projected_savings(
    months_ahead: int = Query(1, ge=1, le=12, description="Months ahead to project"),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """
    Get projected savings for next N months.
    
    Uses historical trends to project future savings.
    """
    projected = savings_calculator.calculate_projected_savings(
        workspace_id=workspace_id,
        months_ahead=months_ahead,
        db=db,
    )
    
    return ProjectedSavingsResponse(
        projected_savings=str(projected["projected_savings"]),
        monthly_avg_savings=str(projected["monthly_avg_savings"]),
        months_ahead=projected["months_ahead"],
        projected_savings_percent=projected["projected_savings_percent"],
    )


@router.get("/summary")
async def get_insights_summary(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """
    Get insights summary for workspace.
    
    Returns key metrics and highlights.
    """
    # Get savings
    savings = savings_calculator.calculate_savings(
        workspace_id=workspace_id,
        db=db,
    )
    
    # Get projected savings
    projected = savings_calculator.calculate_projected_savings(
        workspace_id=workspace_id,
        months_ahead=1,
        db=db,
    )
    
    return {
        "savings": {
            "total": str(savings["total_savings"]),
            "percent": savings["savings_percent"],
            "projected_next_month": str(projected["projected_savings"]),
        },
        "performance": {
            "latency_reduction_ms": savings.get("latency_reduction_ms", 0),
            "cache_hit_rate_improvement": savings.get("cache_hit_rate_improvement", 0.0),
        },
        "operations": {
            "count": savings["operations_count"],
        },
    }
