"""Monitoring Suite: system health, metrics, real-time dashboard, alerts."""
import time
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, require_admin
from db.session import get_db
from db.models import SystemMetrics, Alert, AlertSeverity, User, Job, AIAuditLog

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

_START_TIME = time.time()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ComponentHealth(BaseModel):
    status: str
    response_time_ms: Optional[float] = None
    details: Optional[dict] = None


class SystemHealth(BaseModel):
    status: str
    score: int
    uptime_seconds: float
    components: Dict[str, Any]
    timestamp: str


class MetricPoint(BaseModel):
    name: str
    value: float
    unit: Optional[str]
    timestamp: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _check_db(db: Session) -> ComponentHealth:
    try:
        t0 = time.perf_counter()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        ms = (time.perf_counter() - t0) * 1000
        return ComponentHealth(status="healthy", response_time_ms=round(ms, 2))
    except Exception as e:
        return ComponentHealth(status="unhealthy", details={"error": str(e)})


def _check_redis() -> ComponentHealth:
    try:
        import redis as redis_lib
        from core.config import get_settings
        settings = get_settings()
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        t0 = time.perf_counter()
        r.ping()
        ms = (time.perf_counter() - t0) * 1000
        return ComponentHealth(status="healthy", response_time_ms=round(ms, 2))
    except Exception as e:
        return ComponentHealth(status="unhealthy", details={"error": str(e)})


def _check_storage() -> ComponentHealth:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
        from core.config import get_settings
        settings = get_settings()
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )
        t0 = time.perf_counter()
        s3.list_buckets()
        ms = (time.perf_counter() - t0) * 1000
        return ComponentHealth(status="healthy", response_time_ms=round(ms, 2))
    except Exception as e:
        return ComponentHealth(status="degraded", details={"error": str(e)})


def _health_score(components: dict) -> int:
    score = 100
    weights = {"database": 40, "redis": 30, "storage": 20, "api": 10}
    for name, comp in components.items():
        w = weights.get(name, 10)
        if comp["status"] == "unhealthy":
            score -= w
        elif comp["status"] == "degraded":
            score -= w // 2
        rt = comp.get("response_time_ms")
        if rt and rt > 500:
            score -= 5
    return max(0, score)


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/health", response_model=SystemHealth)
async def system_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full system health check with component status."""
    db_health = _check_db(db)
    redis_health = _check_redis()
    storage_health = _check_storage()

    components = {
        "database": db_health.model_dump(),
        "redis": redis_health.model_dump(),
        "storage": storage_health.model_dump(),
        "api": {"status": "healthy", "response_time_ms": 0.1},
    }
    score = _health_score(components)
    overall = "healthy" if score >= 80 else ("degraded" if score >= 50 else "unhealthy")

    return SystemHealth(
        status=overall,
        score=score,
        uptime_seconds=round(time.time() - _START_TIME, 1),
        components=components,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/metrics")
async def get_metrics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Workspace-scoped operational metrics."""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(hours=24)
    if not end_date:
        end_date = datetime.utcnow()

    ws_id = current_user.workspace_id

    total_jobs = db.query(func.count(Job.id)).filter(
        Job.workspace_id == ws_id,
        Job.created_at >= start_date,
    ).scalar() or 0

    completed_jobs = db.query(func.count(Job.id)).filter(
        Job.workspace_id == ws_id,
        Job.created_at >= start_date,
        Job.status == "completed",
    ).scalar() or 0

    failed_jobs = db.query(func.count(Job.id)).filter(
        Job.workspace_id == ws_id,
        Job.created_at >= start_date,
        Job.status == "failed",
    ).scalar() or 0

    total_ai_ops = db.query(func.count(AIAuditLog.id)).filter(
        AIAuditLog.workspace_id == ws_id,
        AIAuditLog.created_at >= start_date,
    ).scalar() or 0

    ai_cost_result = db.query(func.sum(AIAuditLog.cost)).filter(
        AIAuditLog.workspace_id == ws_id,
        AIAuditLog.created_at >= start_date,
    ).scalar()
    total_ai_cost = float(ai_cost_result or 0)

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "jobs": {
            "total": total_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs,
            "success_rate": round((completed_jobs / total_jobs * 100) if total_jobs > 0 else 0, 2),
        },
        "ai_operations": {
            "total": total_ai_ops,
            "total_cost_usd": round(total_ai_cost, 4),
            "avg_cost_per_op": round(total_ai_cost / total_ai_ops, 6) if total_ai_ops > 0 else 0,
        },
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/dashboard")
async def monitoring_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full monitoring dashboard: health + metrics + recent alerts."""
    health = await system_health(current_user, db)
    metrics = await get_metrics(start_date=None, end_date=None, current_user=current_user, db=db)

    open_alerts = db.query(Alert).filter(
        Alert.workspace_id == current_user.workspace_id,
        Alert.status == "open",
    ).order_by(desc(Alert.created_at)).limit(10).all()

    recent_jobs = db.query(Job).filter(
        Job.workspace_id == current_user.workspace_id,
    ).order_by(desc(Job.created_at)).limit(5).all()

    return {
        "health": health,
        "metrics": metrics,
        "open_alerts": [
            {
                "id": a.id,
                "title": a.title,
                "severity": a.severity.value,
                "type": a.alert_type,
                "created_at": a.created_at.isoformat(),
            }
            for a in open_alerts
        ],
        "recent_jobs": [
            {
                "id": j.id,
                "type": j.job_type if hasattr(j, "job_type") else "unknown",
                "status": j.status,
                "created_at": j.created_at.isoformat(),
            }
            for j in recent_jobs
        ],
    }


@router.post("/metrics/record")
async def record_metric(
    metric_name: str,
    metric_value: float,
    metric_unit: Optional[str] = None,
    service: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Record a custom system metric (admin only)."""
    metric = SystemMetrics(
        metric_name=metric_name,
        metric_value=metric_value,
        metric_unit=metric_unit,
        service=service or "api",
    )
    db.add(metric)
    db.commit()
    return {"message": "Metric recorded", "id": metric.id}


@router.get("/metrics/history")
async def metric_history(
    metric_name: str,
    hours: int = Query(24, ge=1, le=720),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Historical metric data for charting."""
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = db.query(SystemMetrics).filter(
        SystemMetrics.metric_name == metric_name,
        SystemMetrics.timestamp >= since,
    ).order_by(SystemMetrics.timestamp).all()
    return [
        {
            "value": r.metric_value,
            "unit": r.metric_unit,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in rows
    ]
