"""Autonomous optimization endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.autonomous.ml_models.cost_predictor import get_cost_predictor_ml
from core.autonomous.ml_models.routing_optimizer import get_routing_optimizer_ml
from core.autonomous.ml_models.quality_predictor import get_quality_predictor_ml
from core.autonomous.optimization.quality_optimizer import get_quality_optimizer
from core.autonomous.training.pipeline import get_training_pipeline
from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal

router = APIRouter(prefix="/autonomous", tags=["autonomous"])
cost_predictor_ml = get_cost_predictor_ml()
routing_optimizer_ml = get_routing_optimizer_ml()
quality_predictor_ml = get_quality_predictor_ml()
quality_optimizer = get_quality_optimizer()
training_pipeline = get_training_pipeline()


class MLPredictionRequest(BaseModel):
    """ML cost prediction request."""
    operation_type: str
    provider: str
    input_tokens: int
    estimated_output_tokens: int
    model: Optional[str] = None


class TrainModelRequest(BaseModel):
    """Train model request."""
    min_samples: int = 100


@router.post("/cost/predict")
async def predict_cost_ml(
    request: MLPredictionRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Predict cost using ML model (workspace-specific)."""
    from datetime import datetime
    
    prediction = cost_predictor_ml.predict_cost(
        workspace_id=workspace_id,
        operation_type=request.operation_type,
        provider=request.provider,
        input_tokens=request.input_tokens,
        estimated_output_tokens=request.estimated_output_tokens,
        model=request.model,
        time_of_day=datetime.utcnow().hour,
    )
    
    return {
        "predicted_cost": str(prediction["predicted_cost"]),
        "confidence_lower": str(prediction["confidence_lower"]),
        "confidence_upper": str(prediction["confidence_upper"]),
        "is_ml_prediction": prediction.get("is_ml_prediction", False),
        "model_version": prediction.get("model_version"),
    }


@router.post("/routing/select")
async def select_provider_ml(
    operation_type: str,
    available_providers: List[str],
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Select provider using ML routing optimizer (workspace-specific)."""
    selected = routing_optimizer_ml.select_provider(
        workspace_id=workspace_id,
        operation_type=operation_type,
        available_providers=available_providers,
        constraints={},
    )
    
    # Get stats
    stats = routing_optimizer_ml.get_routing_stats(workspace_id, operation_type)
    
    return {
        "selected_provider": selected,
        "routing_stats": stats,
    }


@router.post("/routing/update")
async def update_routing_outcome(
    operation_type: str,
    provider: str,
    actual_cost: Decimal,
    actual_quality: float,
    actual_latency_ms: int,
    baseline_cost: Decimal,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Update routing model with actual outcome (learning loop)."""
    routing_optimizer_ml.update_routing_outcome(
        workspace_id=workspace_id,
        operation_type=operation_type,
        provider=provider,
        actual_cost=actual_cost,
        actual_quality=actual_quality,
        actual_latency_ms=actual_latency_ms,
        baseline_cost=baseline_cost,
    )
    
    return {
        "message": "Routing outcome recorded",
        "workspace_id": workspace_id,
    }


@router.get("/routing/stats")
async def get_routing_stats(
    operation_type: str,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Get routing statistics (shows learning progress)."""
    stats = routing_optimizer_ml.get_routing_stats(workspace_id, operation_type)
    
    return stats


@router.post("/quality/predict")
async def predict_quality_ml(
    operation_type: str,
    provider: str,
    input_text: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Predict quality score before running operation."""
    prediction = quality_predictor_ml.predict_quality(
        workspace_id=workspace_id,
        operation_type=operation_type,
        provider=provider,
        input_text=input_text,
        db=db,
    )
    
    return {
        "predicted_quality": prediction["predicted_quality"],
        "confidence_lower": prediction["confidence_lower"],
        "confidence_upper": prediction["confidence_upper"],
        "is_ml_prediction": prediction.get("is_ml_prediction", False),
        "model_version": prediction.get("model_version"),
    }


@router.post("/quality/optimize")
async def optimize_for_quality(
    operation_type: str,
    available_providers: List[str],
    min_quality: float = 0.85,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Optimize provider selection for quality."""
    optimization = quality_optimizer.optimize_for_quality(
        workspace_id=workspace_id,
        operation_type=operation_type,
        available_providers=available_providers,
        min_quality=min_quality,
        db=db,
    )
    
    return optimization


@router.post("/quality/failure-risk")
async def predict_failure_risk(
    operation_type: str,
    provider: str,
    input_text: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Predict if operation is likely to fail before running."""
    risk = quality_optimizer.predict_failure_risk(
        workspace_id=workspace_id,
        operation_type=operation_type,
        provider=provider,
        input_text=input_text,
        db=db,
    )
    
    return risk


@router.post("/train")
async def train_models(
    request: TrainModelRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Train ML models for workspace (accelerates learning)."""
    results = training_pipeline.train_workspace(
        workspace_id=workspace_id,
        min_samples=request.min_samples,
    )
    
    return {
        "message": "Training initiated",
        "results": results,
    }
