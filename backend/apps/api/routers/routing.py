"""Intelligent routing endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.cost_intelligence import ProviderRouter, RoutingConstraints
from db.models import RoutingDecision
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

router = APIRouter(prefix="/routing", tags=["routing"])
provider_router = ProviderRouter()


class RoutingPolicyRequest(BaseModel):
    """Routing policy request."""

    strategy: str = "cost_optimized"  # cost_optimized, quality_optimized, speed_optimized, hybrid
    max_cost: Optional[Decimal] = None
    min_quality: Optional[float] = None
    max_latency_ms: Optional[int] = None


class RoutingTestRequest(BaseModel):
    """Routing test request."""

    operation_type: str
    input_text: Optional[str] = None
    constraints: RoutingPolicyRequest


@router.post("/policy")
async def create_routing_policy(
    request: RoutingPolicyRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create or update routing policy."""
    from db.models import RoutingPolicy
    import json
    
    # Check if policy exists for workspace
    existing_policy = db.query(RoutingPolicy).filter(
        RoutingPolicy.workspace_id == workspace_id
    ).first()
    
    if existing_policy:
        # Update existing policy
        existing_policy.strategy = request.strategy
        existing_policy.constraints_json = json.dumps({
            "max_cost": str(request.max_cost) if request.max_cost else None,
            "min_quality": request.min_quality,
            "max_latency_ms": request.max_latency_ms,
        })
        db.commit()
        db.refresh(existing_policy)
        policy_id = existing_policy.id
        message = "Routing policy updated"
    else:
        # Create new policy
        new_policy = RoutingPolicy(
            workspace_id=workspace_id,
            strategy=request.strategy,
            constraints_json=json.dumps({
                "max_cost": str(request.max_cost) if request.max_cost else None,
                "min_quality": request.min_quality,
                "max_latency_ms": request.max_latency_ms,
            }),
        )
        db.add(new_policy)
        db.commit()
        db.refresh(new_policy)
        policy_id = new_policy.id
        message = "Routing policy created"
    
    return {
        "message": message,
        "policy_id": policy_id,
        "workspace_id": workspace_id,
        "strategy": request.strategy,
        "constraints": {
            "max_cost": str(request.max_cost) if request.max_cost else None,
            "min_quality": request.min_quality,
            "max_latency_ms": request.max_latency_ms,
        },
    }


@router.get("/policy")
async def get_routing_policy(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get routing policy."""
    from db.models import RoutingPolicy
    import json
    
    policy = db.query(RoutingPolicy).filter(
        RoutingPolicy.workspace_id == workspace_id
    ).first()
    
    if not policy:
        # Return default policy
        return {
            "workspace_id": workspace_id,
            "strategy": "cost_optimized",
            "constraints": {},
            "exists": False,
        }
    
    # Parse constraints from JSON
    try:
        constraints = json.loads(policy.constraints_json) if policy.constraints_json else {}
    except json.JSONDecodeError:
        constraints = {}
    
    return {
        "workspace_id": workspace_id,
        "policy_id": policy.id,
        "strategy": policy.strategy,
        "constraints": constraints,
        "exists": True,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


@router.post("/test")
async def test_routing(
    request: RoutingTestRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Test routing decision."""
    constraints = RoutingConstraints(
        max_cost=request.constraints.max_cost,
        min_quality=request.constraints.min_quality,
        max_latency_ms=request.constraints.max_latency_ms,
        strategy=request.constraints.strategy,
    )
    
    decision = provider_router.select_provider(
        operation_type=request.operation_type,
        constraints=constraints,
        input_text=request.input_text,
    )
    
    # Store routing decision
    routing_decision = RoutingDecision(
        workspace_id=workspace_id,
        operation_type=request.operation_type,
        constraints_json=str(constraints.dict()),
        selected_provider=decision.selected_provider,
        reasoning=decision.reasoning,
        expected_cost=decision.expected_cost,
        expected_quality_score=decision.expected_quality_score,
        expected_latency_ms=decision.expected_latency_ms,
        alternatives_json=str([alt.dict() for alt in decision.alternatives_considered]),
    )
    db.add(routing_decision)
    db.commit()
    db.refresh(routing_decision)
    
    return {
        "selected_provider": decision.selected_provider,
        "reasoning": decision.reasoning,
        "expected_cost": str(decision.expected_cost),
        "expected_quality": decision.expected_quality_score,
        "expected_latency_ms": decision.expected_latency_ms,
        "alternatives": [
            {
                "provider": alt.provider,
                "cost": str(alt.cost),
                "quality": alt.quality_score,
                "latency_ms": alt.latency_ms,
            }
            for alt in decision.alternatives_considered
        ],
        "decision_id": routing_decision.id,
    }
