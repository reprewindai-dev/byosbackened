"""Autonomous optimization endpoints."""
import hashlib
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.autonomous.ml_models.cost_predictor import get_cost_predictor_ml
from core.autonomous.ml_models.routing_optimizer import get_routing_optimizer_ml
from core.autonomous.ml_models.quality_predictor import get_quality_predictor_ml
from core.autonomous.optimization.quality_optimizer import get_quality_optimizer
from core.autonomous.training.pipeline import get_training_pipeline
from db.models.security_audit import SecurityAuditLog
from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
import json

router = APIRouter(prefix="/autonomous", tags=["autonomous"])
cost_predictor_ml = get_cost_predictor_ml()
routing_optimizer_ml = get_routing_optimizer_ml()
quality_predictor_ml = get_quality_predictor_ml()
quality_optimizer = get_quality_optimizer()
training_pipeline = get_training_pipeline()
_HOT_AUTONOMOUS_CACHE: dict[str, tuple[float, dict]] = {}
_HOT_AUTONOMOUS_TTL_SECONDS = 30.0


def _cache_get(key: str) -> Optional[dict]:
    cached = _HOT_AUTONOMOUS_CACHE.get(key)
    if not cached:
        return None
    expiry, payload = cached
    if expiry <= time.time():
        _HOT_AUTONOMOUS_CACHE.pop(key, None)
        return None
    return payload


def _cache_set(key: str, payload: dict) -> None:
    now = time.time()
    _HOT_AUTONOMOUS_CACHE[key] = (now + _HOT_AUTONOMOUS_TTL_SECONDS, payload)
    if len(_HOT_AUTONOMOUS_CACHE) > 8000:
        expired = [k for k, (expiry, _) in _HOT_AUTONOMOUS_CACHE.items() if expiry <= now]
        for k in expired[:4000]:
            _HOT_AUTONOMOUS_CACHE.pop(k, None)


def _predict_key(*parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
    cache_key = _predict_key(
        "autonomous_cost_predict",
        workspace_id,
        request.operation_type,
        request.provider,
        request.input_tokens,
        request.estimated_output_tokens,
        request.model or "",
        datetime.utcnow().hour,
    )
    cached = _cache_get(cache_key)
    if cached:
        return cached
    
    prediction = cost_predictor_ml.predict_cost(
        workspace_id=workspace_id,
        operation_type=request.operation_type,
        provider=request.provider,
        input_tokens=request.input_tokens,
        estimated_output_tokens=request.estimated_output_tokens,
        model=request.model,
        time_of_day=datetime.utcnow().hour,
    )
    
    response = {
        "predicted_cost": str(prediction["predicted_cost"]),
        "confidence_lower": str(prediction["confidence_lower"]),
        "confidence_upper": str(prediction["confidence_upper"]),
        "is_ml_prediction": prediction.get("is_ml_prediction", False),
        "model_version": prediction.get("model_version"),
    }
    _cache_set(cache_key, response)
    return response


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
    db: Session = Depends(get_db),
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

    audit = SecurityAuditLog(
        workspace_id=workspace_id,
        event_type="routing_outcome_recorded",
        event_category="autonomous_ml",
        success=True,
        details=json.dumps({
            "operation_type": operation_type,
            "provider": provider,
            "actual_cost": str(actual_cost),
            "actual_quality": actual_quality,
            "actual_latency_ms": actual_latency_ms,
            "baseline_cost": str(baseline_cost),
        }),
    )
    db.add(audit)
    db.commit()

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
    cache_key = _predict_key(
        "autonomous_quality_predict",
        workspace_id,
        operation_type,
        provider,
        (input_text or "")[:1024],
    )
    cached = _cache_get(cache_key)
    if cached:
        return cached
    prediction = quality_predictor_ml.predict_quality(
        workspace_id=workspace_id,
        operation_type=operation_type,
        provider=provider,
        input_text=input_text,
        db=db,
    )
    
    response = {
        "predicted_quality": prediction["predicted_quality"],
        "confidence_lower": prediction["confidence_lower"],
        "confidence_upper": prediction["confidence_upper"],
        "is_ml_prediction": prediction.get("is_ml_prediction", False),
        "model_version": prediction.get("model_version"),
    }
    _cache_set(cache_key, response)
    return response


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
    cache_key = _predict_key(
        "autonomous_failure_risk",
        workspace_id,
        operation_type,
        provider,
        (input_text or "")[:1024],
    )
    cached = _cache_get(cache_key)
    if cached:
        return cached
    risk = quality_optimizer.predict_failure_risk(
        workspace_id=workspace_id,
        operation_type=operation_type,
        provider=provider,
        input_text=input_text,
        db=db,
    )
    
    _cache_set(cache_key, risk)
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

    audit = SecurityAuditLog(
        workspace_id=workspace_id,
        event_type="ml_model_training",
        event_category="autonomous_ml",
        success=True,
        details=json.dumps({
            "min_samples": request.min_samples,
            "models_trained": list(results.keys()) if isinstance(results, dict) else [],
            "results_summary": {
                k: v.get("trained", False) if isinstance(v, dict) else str(v)
                for k, v in (results.items() if isinstance(results, dict) else {}.items())
            },
        }),
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Training initiated",
        "results": results,
    }
