"""Anomaly management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from apps.api.deps import get_current_workspace_id
from db.session import get_db
from db.models import Anomaly
from db.models.anomaly import AnomalyStatus
from core.cost_intelligence.anomaly_detector import get_anomaly_detector

router = APIRouter(prefix="/anomalies", tags=["anomalies"])
detector = get_anomaly_detector()


class DetectRequest(BaseModel):
    lookback_minutes: int = 60
    spike_multiplier: float = 3.0
    min_events: int = 5


class UpdateStatusRequest(BaseModel):
    status: AnomalyStatus
    resolution_notes: str | None = None


@router.post("/detect")
async def detect_anomalies(
    request: DetectRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Run anomaly detection for the current workspace."""
    cost_spike = detector.detect_cost_spike(
        db=db,
        workspace_id=workspace_id,
        lookback_minutes=request.lookback_minutes,
        spike_multiplier=request.spike_multiplier,
        min_events=request.min_events,
    )
    return {
        "workspace_id": workspace_id,
        "cost_spike": (
            {
                "id": cost_spike.id,
                "severity": cost_spike.severity,
                "status": cost_spike.status,
                "description": cost_spike.description,
                "remediated_at": (
                    cost_spike.remediated_at.isoformat() if cost_spike.remediated_at else None
                ),
                "remediation_action": cost_spike.remediation_action,
                "remediation_result": cost_spike.remediation_result,
            }
            if cost_spike
            else None
        ),
    }


@router.get("")
async def list_anomalies(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """List anomalies for the current workspace."""
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.workspace_id == workspace_id)
        .order_by(Anomaly.detected_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": a.id,
            "type": a.anomaly_type,
            "severity": a.severity,
            "status": a.status,
            "description": a.description,
            "detected_at": a.detected_at.isoformat(),
            "baseline_value": a.baseline_value,
            "actual_value": a.actual_value,
            "deviation_percent": a.deviation_percent,
            "remediated_at": a.remediated_at.isoformat() if a.remediated_at else None,
            "remediation_action": a.remediation_action,
            "remediation_result": a.remediation_result,
            "resolution_notes": a.resolution_notes,
        }
        for a in anomalies
    ]


@router.post("/{anomaly_id}/status")
async def update_anomaly_status(
    anomaly_id: str,
    request: UpdateStatusRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Update anomaly status."""
    anomaly = (
        db.query(Anomaly)
        .filter(Anomaly.id == anomaly_id, Anomaly.workspace_id == workspace_id)
        .first()
    )
    if not anomaly:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found")

    anomaly.status = request.status
    if request.resolution_notes is not None:
        anomaly.resolution_notes = request.resolution_notes

    db.commit()
    db.refresh(anomaly)

    return {
        "id": anomaly.id,
        "status": anomaly.status,
        "resolution_notes": anomaly.resolution_notes,
    }
