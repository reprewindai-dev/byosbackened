"""Billing and cost allocation endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from db.models import CostAllocation, AIAuditLog
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/billing", tags=["billing"])


class CostAllocationRequest(BaseModel):
    """Cost allocation request."""

    operation_id: str
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    allocation_method: str = "percentage"  # "percentage", "fixed", "usage"
    allocation_rules: dict  # e.g., {"project_a": 50, "project_b": 50} for percentage


@router.post("/allocate")
async def allocate_cost(
    request: CostAllocationRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Manually allocate cost."""
    # Get operation cost from audit log
    audit_log = db.query(AIAuditLog).filter(
        AIAuditLog.id == request.operation_id,
        AIAuditLog.workspace_id == workspace_id,
    ).first()
    
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found",
        )
    
    base_cost = audit_log.cost
    
    # Allocate based on method
    allocations = []
    if request.allocation_method == "percentage":
        total_percent = sum(request.allocation_rules.values())
        if abs(total_percent - 100) > 0.01:  # Allow small rounding errors
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Percentages must sum to 100, got {total_percent}",
            )
        
        for target, percent in request.allocation_rules.items():
            allocated = base_cost * Decimal(percent) / Decimal(100)
            # Round to 6 decimal places
            allocated = allocated.quantize(Decimal("0.000001"))
            
            allocation = CostAllocation(
                workspace_id=workspace_id,
                operation_id=request.operation_id,
                project_id=target if not request.client_id else None,
                client_id=request.client_id,
                allocated_cost=allocated,
                base_cost=base_cost,
                markup_percent=Decimal("0"),
                final_cost=allocated,
                allocation_method=request.allocation_method,
            )
            db.add(allocation)
            allocations.append(allocation)
    
    db.commit()
    
    return {
        "message": "Cost allocated",
        "operation_id": request.operation_id,
        "base_cost": str(base_cost),
        "allocations": [
            {
                "id": a.id,
                "project_id": a.project_id,
                "client_id": a.client_id,
                "allocated_cost": str(a.allocated_cost),
            }
            for a in allocations
        ],
    }


@router.get("/report")
async def generate_billing_report(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    project_id: Optional[str] = None,
    client_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Generate billing report."""
    query = db.query(CostAllocation).filter(CostAllocation.workspace_id == workspace_id)
    
    if project_id:
        query = query.filter(CostAllocation.project_id == project_id)
    if client_id:
        query = query.filter(CostAllocation.client_id == client_id)
    if start_date:
        query = query.filter(CostAllocation.created_at >= start_date)
    if end_date:
        query = query.filter(CostAllocation.created_at <= end_date)
    
    allocations = query.all()
    
    # Calculate totals
    total_base_cost = sum(a.base_cost for a in allocations)
    total_final_cost = sum(a.final_cost for a in allocations)
    total_markup = total_final_cost - total_base_cost
    
    # Group by project/client
    by_project = {}
    by_client = {}
    for a in allocations:
        if a.project_id:
            by_project[a.project_id] = by_project.get(a.project_id, Decimal("0")) + a.final_cost
        if a.client_id:
            by_client[a.client_id] = by_client.get(a.client_id, Decimal("0")) + a.final_cost
    
    return {
        "workspace_id": workspace_id,
        "period": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        },
        "summary": {
            "total_operations": len(allocations),
            "total_base_cost": str(total_base_cost),
            "total_markup": str(total_markup),
            "total_final_cost": str(total_final_cost),
        },
        "by_project": {k: str(v) for k, v in by_project.items()},
        "by_client": {k: str(v) for k, v in by_client.items()},
        "line_items": [
            {
                "id": a.id,
                "operation_id": a.operation_id,
                "project_id": a.project_id,
                "client_id": a.client_id,
                "base_cost": str(a.base_cost),
                "markup_percent": str(a.markup_percent),
                "final_cost": str(a.final_cost),
                "created_at": a.created_at.isoformat(),
            }
            for a in allocations
        ],
    }


@router.get("/breakdown")
async def get_cost_breakdown(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    group_by: str = "project",  # "project", "client", "operation_type", "provider"
):
    """Get cost breakdown."""
    allocations = db.query(CostAllocation).filter(
        CostAllocation.workspace_id == workspace_id
    ).all()
    
    breakdown = {}
    for a in allocations:
        if group_by == "project":
            key = a.project_id or "unallocated"
        elif group_by == "client":
            key = a.client_id or "unallocated"
        elif group_by == "operation_type":
            # Need to join with audit log
            audit_log = db.query(AIAuditLog).filter(
                AIAuditLog.id == a.operation_id
            ).first()
            key = audit_log.operation_type if audit_log else "unknown"
        else:  # provider
            audit_log = db.query(AIAuditLog).filter(
                AIAuditLog.id == a.operation_id
            ).first()
            key = audit_log.provider if audit_log else "unknown"
        
        breakdown[key] = breakdown.get(key, Decimal("0")) + a.final_cost
    
    return {
        "group_by": group_by,
        "breakdown": {k: str(v) for k, v in breakdown.items()},
    }
