"""Cost prediction endpoints."""
import hashlib
import json
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.cost_intelligence import CostCalculator
from db.models import CostPrediction
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

router = APIRouter(prefix="/cost", tags=["cost"])
cost_calculator = CostCalculator()
_HOT_COST_CACHE: dict[str, tuple[float, dict]] = {}
_HOT_COST_CACHE_TTL_SECONDS = 30.0


def _cache_key(workspace_id: str, request: "CostPredictionRequest") -> str:
    payload = {
        "workspace_id": workspace_id,
        "operation_type": request.operation_type,
        "provider": request.provider,
        "input_text": request.input_text,
        "input_tokens": request.input_tokens,
        "estimated_output_tokens": request.estimated_output_tokens,
        "model": request.model,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CostPredictionRequest(BaseModel):
    """Cost prediction request."""

    operation_type: str
    provider: str
    input_text: Optional[str] = None
    input_tokens: Optional[int] = None
    estimated_output_tokens: Optional[int] = None
    model: Optional[str] = None


class CostPredictionResponse(BaseModel):
    """Cost prediction response."""

    predicted_cost: str
    confidence_lower: str
    confidence_upper: str
    accuracy_score: float
    alternative_providers: list
    input_tokens: int
    estimated_output_tokens: int
    prediction_id: str


@router.post("/predict", response_model=CostPredictionResponse)
async def predict_cost(
    request: CostPredictionRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Predict cost for operation."""
    key = _cache_key(workspace_id, request)
    now = time.time()
    cached = _HOT_COST_CACHE.get(key)
    if cached and cached[0] > now:
        return CostPredictionResponse(**cached[1])

    # Calculate prediction
    prediction = cost_calculator.predict_cost(
        operation_type=request.operation_type,
        provider=request.provider,
        input_text=request.input_text,
        input_tokens=request.input_tokens,
        estimated_output_tokens=request.estimated_output_tokens,
        model=request.model,
    )
    
    # Store prediction in database
    cost_pred = CostPrediction(
        workspace_id=workspace_id,
        operation_type=request.operation_type,
        provider=request.provider,
        model=request.model,
        input_tokens=prediction.input_tokens,
        estimated_output_tokens=prediction.estimated_output_tokens,
        predicted_cost=prediction.predicted_cost,
        confidence_lower=prediction.confidence_lower,
        confidence_upper=prediction.confidence_upper,
    )
    db.add(cost_pred)
    db.commit()
    db.refresh(cost_pred)
    
    response = CostPredictionResponse(
        predicted_cost=str(prediction.predicted_cost),
        confidence_lower=str(prediction.confidence_lower),
        confidence_upper=str(prediction.confidence_upper),
        accuracy_score=prediction.accuracy_score,
        alternative_providers=prediction.alternative_providers,
        input_tokens=prediction.input_tokens,
        estimated_output_tokens=prediction.estimated_output_tokens,
        prediction_id=cost_pred.id,
    )
    _HOT_COST_CACHE[key] = (now + _HOT_COST_CACHE_TTL_SECONDS, response.model_dump())
    if len(_HOT_COST_CACHE) > 5000:
        expired = [k for k, (expiry, _) in _HOT_COST_CACHE.items() if expiry <= now]
        for k in expired[:2500]:
            _HOT_COST_CACHE.pop(k, None)
    return response


@router.get("/history")
async def get_cost_history(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """Get cost prediction history."""
    predictions = db.query(CostPrediction).filter(
        CostPrediction.workspace_id == workspace_id
    ).order_by(CostPrediction.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "operation_type": p.operation_type,
            "provider": p.provider,
            "predicted_cost": str(p.predicted_cost),
            "actual_cost": str(p.actual_cost) if p.actual_cost else None,
            "prediction_error_percent": float(p.prediction_error_percent) if p.prediction_error_percent else None,
            "was_within_confidence": p.was_within_confidence,
            "created_at": p.created_at.isoformat(),
        }
        for p in predictions
    ]
