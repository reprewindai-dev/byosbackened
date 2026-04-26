"""
LockerPhycer Monitoring Router - Integrated into BYOS Backend

System monitoring, health checks, and performance metrics.
Originally from LockerPhycer, now part of unified BYOS backend.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from db.session import get_db
from db.models import User, SystemMetrics, Alert
from apps.api.deps import get_current_user

router = APIRouter(prefix="/locker/monitoring", tags=["locker-monitoring"])


# ─── Pydantic Schemas ───────────────────────────────────────────────────────

class SystemStatusResponse(BaseModel):
    status: str
    timestamp: datetime
    components: Dict[str, Any]
    uptime_seconds: int


class PerformanceMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    timestamp: datetime


class AlertSummary(BaseModel):
    total_alerts: int
    critical: int
    warning: int
    info: int
    recent_alerts: list


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overall system status"""
    
    # Get latest metrics
    latest_metrics = db.query(SystemMetrics).order_by(
        SystemMetrics.timestamp.desc()
    ).first()
    
    # Count active alerts
    active_alerts = db.query(Alert).filter(
        Alert.resolved_at.is_(None)
    ).count()
    
    components = {
        "database": "healthy" if latest_metrics else "unknown",
        "alerts": f"{active_alerts} active" if active_alerts > 0 else "none",
        "metrics_collected": latest_metrics is not None
    }
    
    return SystemStatusResponse(
        status="healthy" if active_alerts == 0 else "degraded",
        timestamp=datetime.utcnow(),
        components=components,
        uptime_seconds=0  # Would track actual uptime in production
    )


@router.get("/metrics/performance")
def get_performance_metrics(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance metrics for the specified time period"""
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(SystemMetrics).filter(
        SystemMetrics.timestamp >= since
    ).order_by(SystemMetrics.timestamp.desc()).all()
    
    return {
        "period_hours": hours,
        "data_points": len(metrics),
        "latest": metrics[0] if metrics else None,
        "trends": {
            "cpu_avg": sum(m.cpu_percent for m in metrics) / len(metrics) if metrics else 0,
            "memory_avg": sum(m.memory_percent for m in metrics) / len(metrics) if metrics else 0,
        }
    }


@router.get("/alerts/summary", response_model=AlertSummary)
def get_alerts_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get alert summary"""
    
    # Count by severity
    from db.models import AlertSeverity
    
    total = db.query(Alert).count()
    critical = db.query(Alert).filter(Alert.severity == AlertSeverity.CRITICAL).count()
    warning = db.query(Alert).filter(Alert.severity == AlertSeverity.WARNING).count()
    info = db.query(Alert).filter(Alert.severity == AlertSeverity.INFO).count()
    
    # Recent alerts
    recent = db.query(Alert).order_by(
        Alert.created_at.desc()
    ).limit(5).all()
    
    return AlertSummary(
        total_alerts=total,
        critical=critical,
        warning=warning,
        info=info,
        recent_alerts=recent
    )


@router.get("/alerts")
def list_alerts(
    resolved: Optional[bool] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List alerts with optional filtering"""
    
    query = db.query(Alert)
    
    if resolved is not None:
        if resolved:
            query = query.filter(Alert.resolved_at.isnot(None))
        else:
            query = query.filter(Alert.resolved_at.is_(None))
    
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    
    return alerts


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    resolution: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve an alert"""
    
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.resolved_at = datetime.utcnow()
    alert.resolution = resolution
    alert.resolved_by = current_user.id
    db.commit()
    
    return {"message": "Alert resolved successfully"}


@router.get("/health/detailed")
def get_detailed_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed health check for all components"""
    
    health_checks = {
        "database": _check_database(db),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Overall status
    all_healthy = all(check["status"] == "healthy" for check in health_checks.values() 
                      if isinstance(check, dict) and "status" in check)
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": health_checks
    }


def _check_database(db: Session) -> Dict[str, Any]:
    """Check database connectivity"""
    try:
        # Simple query to verify connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "response_time_ms": 0,  # Would measure actual time
            "message": "Database connection successful"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed"
        }
