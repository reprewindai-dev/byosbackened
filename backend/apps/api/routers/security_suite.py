"""Security Suite: threat events, security score, controls, real-time dashboard."""
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, require_admin
from db.session import get_db
from db.models import (
    SecurityEvent, ThreatType, SecurityLevel,
    Alert, AlertSeverity, User,
)

router = APIRouter(prefix="/security", tags=["security-suite"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SecurityEventCreate(BaseModel):
    event_type: str
    threat_type: Optional[ThreatType] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    description: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_analysis: Optional[dict] = None
    ai_recommendations: Optional[dict] = None


class SecurityEventResponse(BaseModel):
    id: str
    workspace_id: Optional[str]
    event_type: str
    threat_type: Optional[str]
    security_level: str
    description: Optional[str]
    status: str
    ip_address: Optional[str]
    ai_confidence: Optional[float]
    created_at: str
    resolved_at: Optional[str]

    class Config:
        from_attributes = True


class ThreatStats(BaseModel):
    total: int
    open: int
    resolved: int
    critical: int
    last_24h: int
    by_type: dict
    by_severity: dict
    security_score: int


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/events", response_model=List[SecurityEventResponse])
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    threat_type: Optional[ThreatType] = None,
    security_level: Optional[SecurityLevel] = None,
    event_status: Optional[str] = Query(None, alias="status"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List security events for the current workspace."""
    q = db.query(SecurityEvent).filter(
        SecurityEvent.workspace_id == current_user.workspace_id
    ).order_by(desc(SecurityEvent.created_at))

    if threat_type:
        q = q.filter(SecurityEvent.threat_type == threat_type)
    if security_level:
        q = q.filter(SecurityEvent.security_level == security_level)
    if event_status:
        q = q.filter(SecurityEvent.status == event_status)
    if start_date:
        q = q.filter(SecurityEvent.created_at >= start_date)
    if end_date:
        q = q.filter(SecurityEvent.created_at <= end_date)

    events = q.offset(skip).limit(limit).all()
    return [
        SecurityEventResponse(
            id=e.id,
            workspace_id=e.workspace_id,
            event_type=e.event_type,
            threat_type=e.threat_type.value if e.threat_type else None,
            security_level=e.security_level.value,
            description=e.description,
            status=e.status,
            ip_address=e.ip_address,
            ai_confidence=e.ai_confidence,
            created_at=e.created_at.isoformat(),
            resolved_at=e.resolved_at.isoformat() if e.resolved_at else None,
        )
        for e in events
    ]


@router.get("/events/{event_id}", response_model=SecurityEventResponse)
async def get_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = db.query(SecurityEvent).filter(
        SecurityEvent.id == event_id,
        SecurityEvent.workspace_id == current_user.workspace_id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return SecurityEventResponse(
        id=event.id,
        workspace_id=event.workspace_id,
        event_type=event.event_type,
        threat_type=event.threat_type.value if event.threat_type else None,
        security_level=event.security_level.value,
        description=event.description,
        status=event.status,
        ip_address=event.ip_address,
        ai_confidence=event.ai_confidence,
        created_at=event.created_at.isoformat(),
        resolved_at=event.resolved_at.isoformat() if event.resolved_at else None,
    )


@router.post("/events", response_model=SecurityEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: SecurityEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually log a security event."""
    event = SecurityEvent(
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return SecurityEventResponse(
        id=event.id,
        workspace_id=event.workspace_id,
        event_type=event.event_type,
        threat_type=event.threat_type.value if event.threat_type else None,
        security_level=event.security_level.value,
        description=event.description,
        status=event.status,
        ip_address=event.ip_address,
        ai_confidence=event.ai_confidence,
        created_at=event.created_at.isoformat(),
        resolved_at=None,
    )


@router.put("/events/{event_id}/resolve")
async def resolve_event(
    event_id: str,
    resolution: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.query(SecurityEvent).filter(
        SecurityEvent.id == event_id,
        SecurityEvent.workspace_id == current_user.workspace_id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = "resolved"
    event.resolution = resolution
    event.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Event resolved"}


@router.put("/events/{event_id}/assign")
async def assign_event(
    event_id: str,
    assignee_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.query(SecurityEvent).filter(
        SecurityEvent.id == event_id,
        SecurityEvent.workspace_id == current_user.workspace_id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.assigned_to = assignee_id
    db.commit()
    return {"message": "Event assigned"}


@router.get("/stats", response_model=ThreatStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Security stats and score for the workspace."""
    ws_id = current_user.workspace_id
    yesterday = datetime.utcnow() - timedelta(days=1)

    total = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.workspace_id == ws_id
    ).scalar() or 0

    open_count = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.workspace_id == ws_id,
        SecurityEvent.status == "open",
    ).scalar() or 0

    resolved_count = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.workspace_id == ws_id,
        SecurityEvent.status == "resolved",
    ).scalar() or 0

    critical_count = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.workspace_id == ws_id,
        SecurityEvent.security_level == SecurityLevel.CRITICAL,
        SecurityEvent.status == "open",
    ).scalar() or 0

    last_24h = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.workspace_id == ws_id,
        SecurityEvent.created_at >= yesterday,
    ).scalar() or 0

    by_type_rows = db.query(SecurityEvent.threat_type, func.count()).filter(
        SecurityEvent.workspace_id == ws_id,
        SecurityEvent.threat_type.isnot(None),
    ).group_by(SecurityEvent.threat_type).all()
    by_type = {r[0].value if r[0] else "unknown": r[1] for r in by_type_rows}

    by_sev_rows = db.query(SecurityEvent.security_level, func.count()).filter(
        SecurityEvent.workspace_id == ws_id,
    ).group_by(SecurityEvent.security_level).all()
    by_severity = {r[0].value: r[1] for r in by_sev_rows}

    score = max(0, 100 - (critical_count * 15) - (open_count * 3) - (last_24h * 2))
    score = min(100, score)

    return ThreatStats(
        total=total,
        open=open_count,
        resolved=resolved_count,
        critical=critical_count,
        last_24h=last_24h,
        by_type=by_type,
        by_severity=by_severity,
        security_score=score,
    )


@router.get("/dashboard")
async def security_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregated security dashboard for the workspace."""
    stats = await get_stats(current_user, db)
    recent_events = await list_events(
        skip=0, limit=10, threat_type=None, security_level=None,
        event_status=None, start_date=None, end_date=None,
        current_user=current_user, db=db,
    )
    alerts = db.query(Alert).filter(
        Alert.workspace_id == current_user.workspace_id,
        Alert.status == "open",
    ).order_by(desc(Alert.created_at)).limit(5).all()

    return {
        "stats": stats,
        "recent_events": recent_events,
        "open_alerts": [
            {
                "id": a.id,
                "title": a.title,
                "severity": a.severity.value,
                "type": a.alert_type,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "controls": [
            {"name": "zero_trust_auth", "enabled": True, "category": "authentication"},
            {"name": "mfa_available", "enabled": True, "category": "authentication"},
            {"name": "api_key_scoping", "enabled": True, "category": "access_control"},
            {"name": "cryptographic_audit_logs", "enabled": True, "category": "compliance"},
            {"name": "pii_detection", "enabled": True, "category": "privacy"},
            {"name": "content_filtering", "enabled": True, "category": "content_safety"},
            {"name": "rate_limiting", "enabled": True, "category": "protection"},
            {"name": "budget_enforcement", "enabled": True, "category": "cost_control"},
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/alerts")
async def list_alerts(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerts = db.query(Alert).filter(
        Alert.workspace_id == current_user.workspace_id,
    ).order_by(desc(Alert.created_at)).offset(skip).limit(limit).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "severity": a.severity.value,
            "type": a.alert_type,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.workspace_id == current_user.workspace_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"message": "Alert acknowledged"}
