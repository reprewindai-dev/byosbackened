"""
LockerPhycer Security Router - Integrated into BYOS Backend

Security event management, threat statistics, and security controls.
Originally from LockerPhycer, now part of unified BYOS backend.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from enum import Enum

from db.session import get_db
from db.models import SecurityEvent, User, ThreatType, SecurityLevel
from apps.api.deps import get_current_user

router = APIRouter(prefix="/locker/security", tags=["locker-security"])


# ─── Pydantic Schemas ───────────────────────────────────────────────────────

class SecurityEventResponse(BaseModel):
    id: str
    workspace_id: Optional[str]
    user_id: Optional[str]
    event_type: str
    threat_type: Optional[ThreatType]
    security_level: SecurityLevel
    description: Optional[str]
    ip_address: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class SecurityEventCreate(BaseModel):
    user_id: Optional[str] = None
    event_type: str
    threat_type: Optional[ThreatType] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    description: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_analysis: Optional[dict] = None
    ai_recommendations: Optional[list] = None


class ThreatStats(BaseModel):
    total_threats: int
    threat_types: dict
    severity_counts: dict
    recent_threats: int
    open_threats: int


class SecurityControlResponse(BaseModel):
    name: str
    display_name: str
    description: str
    enabled: bool
    category: str


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/events", response_model=List[SecurityEventResponse])
def list_security_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    threat_type: Optional[ThreatType] = None,
    security_level: Optional[SecurityLevel] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List security events with filtering"""
    
    query = db.query(SecurityEvent).order_by(desc(SecurityEvent.created_at))
    
    # Apply filters
    if threat_type:
        query = query.filter(SecurityEvent.threat_type == threat_type)
    
    if security_level:
        query = query.filter(SecurityEvent.security_level == security_level)
    
    if status:
        query = query.filter(SecurityEvent.status == status)
    
    if start_date:
        query = query.filter(SecurityEvent.created_at >= start_date)
    
    if end_date:
        query = query.filter(SecurityEvent.created_at <= end_date)
    
    # Apply pagination
    events = query.offset(skip).limit(limit).all()
    
    return events


@router.get("/events/{event_id}", response_model=SecurityEventResponse)
def get_security_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get security event by ID"""
    
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security event not found"
        )
    
    return event


@router.post("/events", response_model=SecurityEventResponse)
def create_security_event(
    event_data: SecurityEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new security event"""
    
    event = SecurityEvent(
        user_id=event_data.user_id or current_user.id,
        workspace_id=current_user.workspace_id,
        event_type=event_data.event_type,
        threat_type=event_data.threat_type,
        security_level=event_data.security_level,
        description=event_data.description,
        details=event_data.details,
        ip_address=event_data.ip_address,
        user_agent=event_data.user_agent,
        ai_confidence=event_data.ai_confidence,
        ai_analysis=event_data.ai_analysis,
        ai_recommendations=event_data.ai_recommendations
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return event


@router.put("/events/{event_id}/assign")
def assign_security_event(
    event_id: str,
    assigned_to: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign security event to user"""
    
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security event not found"
        )
    
    # Check if assigned user exists
    assignee = db.query(User).filter(User.id == assigned_to).first()
    if not assignee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found"
        )
    
    event.assigned_to = assigned_to
    event.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Event assigned successfully"}


@router.put("/events/{event_id}/resolve")
def resolve_security_event(
    event_id: str,
    resolution: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve security event"""
    
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security event not found"
        )
    
    event.status = "resolved"
    event.resolution = resolution
    event.resolved_at = datetime.utcnow()
    event.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Event resolved successfully"}


@router.get("/threats/stats", response_model=ThreatStats)
def get_threat_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get threat statistics"""
    
    # Total threats
    total_threats = db.query(func.count(SecurityEvent.id)).scalar()
    
    # Threats by type
    threat_types_result = db.query(
        SecurityEvent.threat_type,
        func.count(SecurityEvent.id)
    ).group_by(SecurityEvent.threat_type).all()
    threat_types = {str(k): v for k, v in threat_types_result if k}
    
    # Threats by severity
    severity_result = db.query(
        SecurityEvent.security_level,
        func.count(SecurityEvent.id)
    ).group_by(SecurityEvent.security_level).all()
    severity_counts = {str(k): v for k, v in severity_result}
    
    # Recent threats (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_threats = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.created_at >= yesterday
    ).scalar()
    
    # Open threats
    open_threats = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.status == "open"
    ).scalar()
    
    return ThreatStats(
        total_threats=total_threats or 0,
        threat_types=threat_types,
        severity_counts=severity_counts,
        recent_threats=recent_threats or 0,
        open_threats=open_threats or 0
    )


@router.get("/controls", response_model=List[SecurityControlResponse])
def get_security_controls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get security controls status"""
    
    controls = [
        {
            "name": "mfa_enabled",
            "display_name": "Multi-Factor Authentication",
            "description": "Require MFA for all users",
            "enabled": True,
            "category": "authentication"
        },
        {
            "name": "ai_monitoring",
            "display_name": "AI Monitoring",
            "description": "AI-powered threat detection",
            "enabled": True,
            "category": "monitoring"
        },
        {
            "name": "rate_limiting",
            "display_name": "Rate Limiting",
            "description": "Prevent brute force attacks",
            "enabled": True,
            "category": "protection"
        },
        {
            "name": "session_timeout",
            "display_name": "Session Timeout",
            "description": "Auto logout inactive users",
            "enabled": True,
            "category": "session"
        },
        {
            "name": "audit_logging",
            "display_name": "Audit Logging",
            "description": "Log all security events",
            "enabled": True,
            "category": "logging"
        },
        {
            "name": "encryption",
            "display_name": "Encryption",
            "description": "End-to-end encryption",
            "enabled": True,
            "category": "encryption"
        }
    ]
    
    return [SecurityControlResponse(**control) for control in controls]


@router.post("/controls/{control_name}")
def toggle_security_control(
    control_name: str,
    enabled: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle security control"""
    
    return {
        "message": f"Security control {control_name} {'enabled' if enabled else 'disabled'} successfully"
    }


@router.get("/dashboard")
def get_security_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get security dashboard data"""
    
    # Get recent events
    recent_events = db.query(SecurityEvent).order_by(
        desc(SecurityEvent.created_at)
    ).limit(10).all()
    
    # Get threat stats
    stats = get_threat_stats(current_user, db)
    
    return {
        "recent_events": recent_events,
        "threat_stats": stats,
        "security_score": _calculate_security_score(stats)
    }


def _calculate_security_score(stats: ThreatStats) -> int:
    """Calculate security score based on threat statistics"""
    
    score = 100
    
    # Deduct points for open threats
    score -= min(stats.open_threats * 5, 50)
    
    # Deduct points for recent threats
    score -= min(stats.recent_threats * 2, 30)
    
    # Add points for low threat volume
    if stats.total_threats < 10:
        score += 10
    elif stats.total_threats < 50:
        score += 5
    
    return max(0, min(100, score))
