"""AI explainability endpoints."""

from fastapi import APIRouter, Depends
from apps.api.deps import get_current_workspace_id
from core.ai_quality.explainability import get_explainability_engine
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter(prefix="/explain", tags=["explainability"])
explainability_engine = get_explainability_engine()


class ExplainRoutingRequest(BaseModel):
    """Explain routing request."""

    selected_provider: str
    alternatives: List[Dict]
    constraints: Dict


class ExplainCostRequest(BaseModel):
    """Explain cost prediction request."""

    predicted_cost: float
    input_tokens: int
    provider: str


@router.post("/routing")
async def explain_routing(
    request: ExplainRoutingRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Explain routing decision."""
    explanation = explainability_engine.explain_routing_decision(
        selected_provider=request.selected_provider,
        alternatives=request.alternatives,
        constraints=request.constraints,
    )

    return {
        "decision": explanation.decision,
        "reasoning": explanation.reasoning,
        "confidence": explanation.confidence,
        "important_inputs": explanation.important_inputs,
        "important_outputs": explanation.important_outputs,
        "alternatives_considered": explanation.alternatives_considered,
    }


@router.post("/cost")
async def explain_cost(
    request: ExplainCostRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Explain cost prediction."""
    explanation = explainability_engine.explain_cost_prediction(
        predicted_cost=request.predicted_cost,
        input_tokens=request.input_tokens,
        provider=request.provider,
    )

    return {
        "decision": explanation.decision,
        "reasoning": explanation.reasoning,
        "confidence": explanation.confidence,
        "important_inputs": explanation.important_inputs,
        "important_outputs": explanation.important_outputs,
    }
