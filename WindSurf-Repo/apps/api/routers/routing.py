"""Intelligent routing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.cost_intelligence import ProviderRouter, RoutingConstraints
from db.models import RoutingDecision, RoutingPolicy
from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal
import json

router = APIRouter(prefix="/routing", tags=["routing"])
provider_router = ProviderRouter()


class RoutingPolicyRequest(BaseModel):
    """Routing policy request."""

    strategy: str = "cost_optimized"  # cost_optimized, quality_optimized, speed_optimized, hybrid
    max_cost: Optional[Decimal] = None
    min_quality: Optional[float] = None
    max_latency_ms: Optional[int] = None
    allowed_providers: Optional[list[str]] = None
    enforcement_mode: Optional[str] = "strict"  # strict|fallback

    @field_validator("enforcement_mode")
    @classmethod
    def validate_enforcement_mode(cls, v: Optional[str]):
        if v is None:
            return "strict"
        if v not in {"strict", "fallback"}:
            raise ValueError("enforcement_mode must be 'strict' or 'fallback'")
        return v

    @field_validator("allowed_providers")
    @classmethod
    def validate_allowed_providers(cls, v: Optional[list[str]]):
        if v is None:
            return v
        cleaned = [p for p in v if isinstance(p, str) and p.strip()]
        return cleaned


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
    policy = db.query(RoutingPolicy).filter(RoutingPolicy.workspace_id == workspace_id).first()
    constraints = {
        "max_cost": str(request.max_cost) if request.max_cost is not None else None,
        "min_quality": request.min_quality,
        "max_latency_ms": request.max_latency_ms,
        "allowed_providers": request.allowed_providers,
        "enforcement_mode": request.enforcement_mode or "strict",
    }

    if not policy:
        policy = RoutingPolicy(
            workspace_id=workspace_id,
            strategy=request.strategy,
            constraints_json=json.dumps(constraints),
            enabled=True,
            version=1,
        )
        db.add(policy)
    else:
        policy.strategy = request.strategy
        policy.constraints_json = json.dumps(constraints)
        policy.enabled = True
        policy.version = (policy.version or 0) + 1

    db.commit()
    db.refresh(policy)
    return {
        "message": "Routing policy created",
        "workspace_id": workspace_id,
        "strategy": policy.strategy,
        "constraints": constraints,
    }


@router.get("/policy")
async def get_routing_policy(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get routing policy."""
    policy = db.query(RoutingPolicy).filter(RoutingPolicy.workspace_id == workspace_id).first()
    if not policy:
        return {
            "workspace_id": workspace_id,
            "strategy": "cost_optimized",
            "constraints": {},
            "enabled": False,
        }

    constraints = {}
    if policy.constraints_json:
        try:
            constraints = json.loads(policy.constraints_json)
        except Exception:
            constraints = {}
    return {
        "workspace_id": workspace_id,
        "strategy": policy.strategy,
        "constraints": constraints,
        "enabled": policy.enabled,
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
        constraints_json=json.dumps(
            constraints.model_dump() if hasattr(constraints, "model_dump") else constraints.dict()
        ),
        selected_provider=decision.selected_provider,
        reasoning=decision.reasoning,
        expected_cost=decision.expected_cost,
        expected_quality=decision.expected_quality_score,
        expected_latency_ms=decision.expected_latency_ms,
        alternatives_json=json.dumps(
            [
                alt.model_dump() if hasattr(alt, "model_dump") else alt.dict()
                for alt in decision.alternatives_considered
            ]
        ),
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
