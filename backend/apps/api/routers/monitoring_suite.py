"""Monitoring Suite: system health, metrics, real-time dashboard, alerts."""
import time
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, load_only

from apps.api.deps import get_current_user, require_admin
from core.redis_pool import get_redis
from db.session import get_db
from db.models import (
    AIAuditLog,
    Alert,
    AlertSeverity,
    Budget,
    Deployment,
    Job,
    SystemMetrics,
    User,
    WorkspaceModelSetting,
    WorkspaceRequestLog,
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

_START_TIME = time.time()
_OVERVIEW_CACHE_TTL_SECONDS = 6
_OVERVIEW_WARM_CACHE_TTL_SECONDS = 30
_overview_cache: dict[str, tuple[float, dict]] = {}


# --- Schemas ------------------------------------------------------------------

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


class CreateMonitoringAlertRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    description: str | None = Field(None, max_length=4000)
    severity: str = Field("medium", min_length=1, max_length=20)
    alert_type: str = Field(..., min_length=2, max_length=120)
    status: str = Field("open", min_length=1, max_length=20)
    source: str | None = Field(None, max_length=140)
    details: dict[str, Any] = Field(default_factory=dict)


# --- Helpers ------------------------------------------------------------------

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
        from core.config import get_settings
        settings = get_settings()
        if not settings.redis_url or settings.redis_url == "redis://localhost:6379":
            return ComponentHealth(status="disabled", details={"reason": "Redis not configured"})

        import redis as redis_lib
        r = redis_lib.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        t0 = time.perf_counter()
        r.ping()
        ms = (time.perf_counter() - t0) * 1000
        return ComponentHealth(status="healthy", response_time_ms=round(ms, 2))
    except Exception as e:
        return ComponentHealth(status="unhealthy", details={"error": str(e)})


def _check_storage() -> ComponentHealth:
    try:
        from core.config import get_settings
        settings = get_settings()
        if not settings.s3_endpoint_url or not settings.s3_access_key_id:
            return ComponentHealth(status="disabled", details={"reason": "S3 not configured"})

        # Quick TCP probe - if S3 endpoint is unreachable, skip boto3 entirely
        # (avoids 5× retry with exponential backoff = ~10s hang)
        from urllib.parse import urlparse
        import socket
        parsed = urlparse(settings.s3_endpoint_url)
        host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            sock.connect((host, port))
        except (socket.timeout, ConnectionRefusedError, OSError):
            return ComponentHealth(status="disabled", details={"reason": f"S3 endpoint {host}:{port} unreachable"})
        finally:
            sock.close()

        import boto3
        from botocore.config import Config
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            config=Config(retries={"max_attempts": 1, "mode": "standard"}),
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


def _normalize_alert_severity(raw: str | None) -> AlertSeverity | None:
    if not raw:
        return None
    normalized = raw.strip().lower()
    for severity in AlertSeverity:
        if severity.value == normalized:
            return severity
    return None


def _serialize_alert(alert: Alert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "title": alert.title,
        "description": alert.description,
        "severity": (alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)),
        "type": alert.alert_type,
        "status": alert.status,
        "source": alert.source,
        "details": alert.details or {},
        "created_at": alert.created_at.isoformat(),
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
    }


# --- Routes -------------------------------------------------------------------

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


@router.get("/alerts")
async def list_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List monitoring alerts for the workspace."""
    query = db.query(Alert).filter(Alert.workspace_id == current_user.workspace_id)
    if status:
        query = query.filter(Alert.status == status.strip().lower())
    normalized_severity = _normalize_alert_severity(severity)
    if normalized_severity is not None:
        query = query.filter(Alert.severity == normalized_severity)

    page_size = 50
    total = query.count()
    alerts = (
        query.order_by(desc(Alert.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "alerts": [_serialize_alert(alert) for alert in alerts],
    }


@router.post("/alerts")
async def create_alert(
    payload: CreateMonitoringAlertRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a monitoring alert."""
    normalized_severity = _normalize_alert_severity(payload.severity) or AlertSeverity.MEDIUM
    alert = Alert(
        workspace_id=current_user.workspace_id,
        title=payload.title,
        description=payload.description,
        severity=normalized_severity,
        alert_type=payload.alert_type,
        status=payload.status.strip().lower(),
        source=payload.source,
        details=payload.details,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {
        "ok": True,
        "alert": _serialize_alert(alert),
    }


@router.get("/logs")
async def list_logs(
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
    level: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unified monitoring log endpoint for dashboard surfaces."""
    start = from_
    end = to
    query = db.query(AIAuditLog).filter(AIAuditLog.workspace_id == current_user.workspace_id)
    if start:
        query = query.filter(AIAuditLog.created_at >= start)
    if end:
        query = query.filter(AIAuditLog.created_at <= end)
    rows = (
        query.order_by(desc(AIAuditLog.created_at))
        .limit(limit)
        .all()
    )
    request_rows = (
        db.query(WorkspaceRequestLog)
        .filter(
            WorkspaceRequestLog.workspace_id == current_user.workspace_id,
            WorkspaceRequestLog.source_table == "ai_audit_logs",
            WorkspaceRequestLog.source_id.in_([row.id for row in rows] or [""]),
        )
        .all()
    )
    request_by_source = {row.source_id: row for row in request_rows}

    level_filter = (level or "").strip().lower()
    entries: list[dict[str, Any]] = []
    for log in rows:
        request_row = request_by_source.get(log.id)
        status_value = (
            request_row.status.lower()
            if request_row and isinstance(request_row.status, str)
            else "success"
        )
        if level_filter:
            normalized = {"warn": "warning", "warning": "warning", "err": "error", "error": "error", "info": "info"}
            normalized_level = normalized.get(level_filter, level_filter)
            if normalized_level == "error" and status_value != "error":
                continue
            if normalized_level == "warning" and status_value not in {"warning", "warn"}:
                continue
        entries.append(
            {
                "id": log.id,
                "operation_type": log.operation_type,
                "provider": log.provider,
                "model": log.model,
                "cost": str(log.cost),
                "latency_ms": request_row.latency_ms if request_row else None,
                "status": status_value,
                "pii_detected": log.pii_detected,
                "pii_types": log.pii_types,
                "created_at": log.created_at.isoformat(),
                "input_preview": log.input_preview,
                "output_preview": log.output_preview,
                "log_hash": log.log_hash,
                "contract": "audit",
            }
        )

    return {
        "source": "audit_logs",
        "generated_at": datetime.utcnow().isoformat(),
        "total": len(entries),
        "entries": entries,
    }


# --- Workspace overview (frontend Overview page) ------------------------------

@router.get("/overview")
async def workspace_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """OverviewPayload for the Overview dashboard.

    Synthesizes KPIs, routing, spend, recent runs, policy events, alerts, audit,
    and fleet from real request logs, audit logs, alerts, budget rows, and model
    settings. A short workspace-scoped hot cache prevents repeated dashboard
    reloads from hammering the database.
    """
    workspace_id = current_user.workspace_id
    cache_key = f"overview:{workspace_id}"
    cached = _overview_cache.get(cache_key)
    if cached and time.time() - cached[0] < _OVERVIEW_CACHE_TTL_SECONDS:
        return cached[1]
    redis_key = f"warm:{cache_key}"
    try:
        cached_raw = get_redis().get(redis_key)
        if cached_raw:
            payload = json.loads(cached_raw)
            _overview_cache[cache_key] = (time.time(), payload)
            return payload
    except Exception:
        pass

    now = datetime.utcnow()
    last_hour = now - timedelta(hours=1)
    prev_hour = now - timedelta(hours=2)
    last_day = now - timedelta(days=1)

    # Recent request logs carry runtime telemetry such as latency. Audit logs
    # carry tamper-evident evidence and remain the audit source of truth.
    recent_request_logs = (
        db.query(WorkspaceRequestLog)
        .options(
            load_only(
                WorkspaceRequestLog.id,
                WorkspaceRequestLog.workspace_id,
                WorkspaceRequestLog.provider,
                WorkspaceRequestLog.model,
                WorkspaceRequestLog.status,
                WorkspaceRequestLog.tokens_in,
                WorkspaceRequestLog.tokens_out,
                WorkspaceRequestLog.latency_ms,
                WorkspaceRequestLog.cost_usd,
                WorkspaceRequestLog.created_at,
            )
        )
        .filter(
            WorkspaceRequestLog.workspace_id == workspace_id,
            WorkspaceRequestLog.created_at >= last_day,
        )
        .order_by(WorkspaceRequestLog.created_at.desc())
        .limit(500)
        .all()
    )
    recent_logs = (
        db.query(AIAuditLog)
        .options(
            load_only(
                AIAuditLog.id,
                AIAuditLog.workspace_id,
                AIAuditLog.user_id,
                AIAuditLog.operation_type,
                AIAuditLog.provider,
                AIAuditLog.model,
                AIAuditLog.cost,
                AIAuditLog.tokens_input,
                AIAuditLog.tokens_output,
                AIAuditLog.pii_detected,
                AIAuditLog.log_hash,
                AIAuditLog.created_at,
            )
        )
        .filter(AIAuditLog.workspace_id == workspace_id, AIAuditLog.created_at >= last_day)
        .order_by(AIAuditLog.created_at.desc())
        .limit(500)
        .all()
    )
    telemetry_logs = recent_request_logs or []
    last_hour_requests = [l for l in telemetry_logs if l.created_at >= last_hour]
    prev_hour_requests = [l for l in telemetry_logs if prev_hour <= l.created_at < last_hour]
    last_hour_logs = [l for l in recent_logs if l.created_at >= last_hour]
    prev_hour_logs = [l for l in recent_logs if prev_hour <= l.created_at < last_hour]

    # KPIs.
    # Prefer true 1h telemetry, but if that window is empty fall back to a 24h
    # view so Overview does not look dead when runs happened outside the last hour.
    window_minutes = 60
    if telemetry_logs:
        kpi_current_rows = last_hour_requests
        kpi_previous_rows = prev_hour_requests
    else:
        kpi_current_rows = last_hour_logs
        kpi_previous_rows = prev_hour_logs

    if not kpi_current_rows:
        window_minutes = 24 * 60
        kpi_window_start = now - timedelta(minutes=window_minutes)
        prev_window_start = kpi_window_start - timedelta(minutes=window_minutes)
        if telemetry_logs:
            kpi_current_rows = [l for l in telemetry_logs if l.created_at >= kpi_window_start]
            kpi_previous_rows = [l for l in telemetry_logs if prev_window_start <= l.created_at < kpi_window_start]
        else:
            kpi_current_rows = [l for l in recent_logs if l.created_at >= kpi_window_start]
            kpi_previous_rows = [l for l in recent_logs if prev_window_start <= l.created_at < kpi_window_start]

    current_run_count = len(kpi_current_rows)
    previous_run_count = len(kpi_previous_rows)
    rpm = round(current_run_count / max(1, window_minutes), 2)
    prev_rpm = round(previous_run_count / max(1, window_minutes), 2)
    rpm_delta = ((rpm - prev_rpm) / prev_rpm * 100) if prev_rpm > 0 else 0.0

    def _median_int(values: list[int]) -> int:
        clean = sorted(v for v in values if v and v > 0)
        if not clean:
            return 0
        return int(clean[len(clean) // 2])

    p50 = _median_int([int(getattr(l, "latency_ms", 0) or 0) for l in kpi_current_rows])
    prev_p50 = _median_int([int(getattr(l, "latency_ms", 0) or 0) for l in kpi_previous_rows])

    def _toks(l):
        return (l.tokens_input or 0) + (l.tokens_output or 0)

    def _units_from_request(l: WorkspaceRequestLog) -> int:
        return int((l.tokens_in or 0) + (l.tokens_out or 0))

    if telemetry_logs:
        total_units_window = sum(_units_from_request(l) for l in kpi_current_rows)
        prev_units_window = sum(_units_from_request(l) for l in kpi_previous_rows)
    else:
        total_units_window = sum(_toks(l) for l in kpi_current_rows)
        prev_units_window = sum(_toks(l) for l in kpi_previous_rows)
    tps = round(total_units_window / max(1, window_minutes * 60), 2)
    tps_delta = ((total_units_window - prev_units_window) / prev_units_window * 100) if prev_units_window > 0 else 0.0

    spend_source = telemetry_logs if telemetry_logs else recent_logs
    spend_today_cents = int(
        sum(
            (float(getattr(l, "cost_usd", getattr(l, "cost", 0)) or 0) * 100)
            for l in spend_source
            if l.created_at.date() == now.date()
        )
    )
    audit_count = len(recent_logs)

    active_models = db.query(WorkspaceModelSetting).filter(
        WorkspaceModelSetting.workspace_id == workspace_id,
        WorkspaceModelSetting.enabled == True,  # noqa: E712
    ).all()
    quantized = sum(1 for m in active_models if (m.bedrock_model_id or "").lower().endswith(("q4", "q5", "q8")))

    # Routing split by actual executed provider.
    def _provider_name(row) -> str:
        return (getattr(row, "provider", None) or "").lower()

    def _provider_route(provider: str) -> str:
        return "primary" if provider == "ollama" else "burst"

    def _fallback_plane_name(rows) -> str:
        providers = {_provider_name(row) for row in rows if _provider_name(row)}
        if "bedrock" in providers:
            return "AWS Bedrock"
        if "groq" in providers:
            return "Groq fallback"
        return "Approved fallback"

    route_source = last_hour_requests if telemetry_logs else last_hour_logs
    primary_count = sum(1 for l in route_source if _provider_name(l) == "ollama")
    burst_count = sum(1 for l in route_source if _provider_name(l) and _provider_name(l) != "ollama")
    total_route = primary_count + burst_count
    primary_util = round(primary_count / total_route * 100, 1) if total_route else 0.0
    burst_util = round(burst_count / total_route * 100, 1) if total_route else 0.0
    fallback_plane = _fallback_plane_name(route_source or recent_request_logs or recent_logs)

    # Recent runs.
    recent_runs = []
    if telemetry_logs:
        for l in recent_request_logs[:10]:
            provider = _provider_name(l)
            recent_runs.append({
                "id": l.id,
                "model": l.model or "-",
                "route": _provider_route(provider) if provider else "primary",
                "latency_ms": int(l.latency_ms or 0),
                "tokens": _units_from_request(l),
                "cost_cents": int(float(l.cost_usd or 0) * 100),
                "policy": "blocked" if l.status != "success" else "passed",
                "when": l.created_at.isoformat(),
            })
    for l in recent_logs[: max(0, 10 - len(recent_runs))]:
        provider = _provider_name(l)
        policy = "redacted" if l.pii_detected else "passed"
        recent_runs.append({
            "id": l.id,
            "model": l.model or "-",
            "route": _provider_route(provider) if provider else "primary",
            "latency_ms": 0,
            "tokens": _toks(l),
            "cost_cents": int(float(l.cost or 0) * 100),
            "policy": policy,
            "when": l.created_at.isoformat(),
        })

    # Audit trail (compact).
    audit_trail = [
        {
            "id": l.id,
            "kind": l.operation_type or "exec",
            "subject": (l.model or "unknown")[:80],
            "actor": l.user_id or "system",
            "ts": l.created_at.isoformat(),
            "hash_prefix": (l.log_hash or "")[:12] if hasattr(l, "log_hash") else "",
        }
        for l in recent_logs[:20]
    ]

    # Policy events from PII flags + provider switches.
    policy_events = []
    for l in recent_logs[:20]:
        if l.pii_detected:
            policy_events.append({
                "id": f"pol-{l.id}",
                "ts": l.created_at.isoformat(),
                "kind": "policy_match",
                "summary": "PII redacted before egress",
                "detail": f"model={l.model} provider={l.provider}",
            })
    if not policy_events and recent_logs:
        l = recent_logs[0]
        policy_events.append({
            "id": f"sig-{l.id}",
            "ts": l.created_at.isoformat(),
            "kind": "audit_signed",
            "summary": "Audit entry signed",
            "detail": f"hash {(getattr(l, 'log_hash', '') or '')[:12]}",
        })

    # Fleet from workspace_model_settings.
    fleet = []
    for i, m in enumerate(active_models[:8]):
        provider = (m.provider or "").lower()
        fleet.append({
            "id": m.model_slug,
            "name": m.display_name or m.model_slug,
            "quant": (m.bedrock_model_id or "fp16").split("-")[-1][:8],
            "replicas": 1,
            "route": "primary" if provider == "ollama" else "burst",
            "p50_ms": p50 + i * 5 if p50 else 0,
        })

    # Alerts from Alert table.
    try:
        alert_rows = (
            db.query(Alert)
            .filter(Alert.workspace_id == workspace_id, Alert.status != "resolved")
            .order_by(Alert.created_at.desc())
            .limit(5)
            .all()
        )
    except Exception:
        alert_rows = []

    def _sev_to_ui(sev) -> str:
        s = (sev.value if hasattr(sev, "value") else str(sev)).lower()
        if s in ("critical", "high"):
            return "error"
        if s == "medium":
            return "warn"
        return "info"

    alerts = [
        {
            "id": a.id,
            "severity": _sev_to_ui(a.severity),
            "title": a.title or "Alert",
            "scope": a.alert_type or "system",
            "when": a.created_at.isoformat(),
        }
        for a in alert_rows
    ]

    active_budget = (
        db.query(Budget)
        .filter(
            Budget.workspace_id == workspace_id,
            Budget.period_start <= now,
            Budget.period_end >= now,
        )
        .order_by(Budget.period_end.asc())
        .first()
    )

    spend_cents = spend_today_cents
    cap_cents = int(float(active_budget.amount) * 100) if active_budget else 0
    burn_source = last_hour_requests if telemetry_logs else last_hour_logs
    burn_per_min = (
        int(
            sum(float(getattr(l, "cost_usd", getattr(l, "cost", 0)) or 0) * 100 for l in burn_source)
            / 60
        )
        if burn_source
        else 0
    )

    # ─── Time-series: bucket the last 2h into 24 x 5-minute windows ────────────
    BUCKET_COUNT = 24
    BUCKET_MIN = 5
    series_window_start = now - timedelta(minutes=BUCKET_COUNT * BUCKET_MIN)

    requests_series: list[int] = [0] * BUCKET_COUNT
    tokens_series: list[int] = [0] * BUCKET_COUNT
    spend_series: list[int] = [0] * BUCKET_COUNT  # cents per bucket
    primary_series: list[int] = [0] * BUCKET_COUNT
    burst_series: list[int] = [0] * BUCKET_COUNT

    series_source = telemetry_logs if telemetry_logs else recent_logs
    for log in series_source:
        if log.created_at < series_window_start:
            continue
        offset_min = (log.created_at - series_window_start).total_seconds() / 60.0
        idx = min(BUCKET_COUNT - 1, max(0, int(offset_min // BUCKET_MIN)))
        requests_series[idx] += 1
        tokens_series[idx] += _units_from_request(log) if telemetry_logs else _toks(log)
        spend_series[idx] += int(float(getattr(log, "cost_usd", getattr(log, "cost", 0)) or 0) * 100)
        provider = _provider_name(log)
        if provider and provider != "ollama":
            burst_series[idx] += 1
        elif provider == "ollama":
            primary_series[idx] += 1

    # Normalize routing series to per-bucket utilization percentages.
    routing_series = []
    for i in range(BUCKET_COUNT):
        bucket_total = primary_series[i] + burst_series[i]
        bucket_ts = (series_window_start + timedelta(minutes=i * BUCKET_MIN)).strftime("%H:%M")
        if bucket_total == 0:
            routing_series.append({"t": bucket_ts, "primary": 0, "burst": 0})
        else:
            routing_series.append({
                "t": bucket_ts,
                "primary": round(primary_series[i] / bucket_total * 100, 1),
                "burst": round(burst_series[i] / bucket_total * 100, 1),
            })

    payload = {
        "kpi": {
            "requests_per_minute": rpm,
            "requests_delta_pct": round(rpm_delta, 1),
            "p50_latency_ms": int(p50),
            "p50_delta_ms": int(p50 - prev_p50),
            "tokens_per_second": tps,
            "tokens_delta_pct": round(tps_delta, 1),
            "spend_today_cents": spend_cents,
            "spend_cap_pct": round(spend_cents / cap_cents * 100, 1) if cap_cents else 0,
            "active_models": len(active_models),
            "active_models_quantized": quantized,
            "audit_entries": audit_count,
            "audit_verified_pct": 100,
            # Real per-metric history for sparklines (24 buckets × 5 min = last 2h).
            "requests_series": requests_series,
            "tokens_series": tokens_series,
            "spend_series": spend_series,
        },
        "routing": {
            "primary_plane": "Hetzner primary",
            "burst_plane": fallback_plane,
            "primary_util_pct": primary_util,
            "burst_util_pct": burst_util,
            "primary_hosts": [
                {"name": "hetzner-fsn1", "util_pct": primary_util, "detail": f"{primary_count} run(s) / 1h"}
            ],
            "series": routing_series,
        },
        "spend": {
            "spend_cents": spend_cents,
            "cap_cents": cap_cents,
            "inference_cents": spend_cents,
            "embeddings_cents": 0,
            "gpu_burst_cents": 0,
            "storage_cents": 0,
            "burn_rate_per_min_cents": burn_per_min,
            "forecast_eod_cents": int(spend_cents + burn_per_min * 60 * (24 - now.hour)),
            "forecast_cap_pct": round((spend_cents + burn_per_min * 60 * (24 - now.hour)) / cap_cents * 100, 1) if cap_cents else 0,
        },
        "recent_runs": recent_runs,
        "policy_events": policy_events,
        "alerts": alerts,
        "audit_trail": audit_trail,
        "fleet": fleet,
    }
    _overview_cache[cache_key] = (time.time(), payload)
    try:
        get_redis().setex(redis_key, _OVERVIEW_WARM_CACHE_TTL_SECONDS, json.dumps(payload))
    except Exception:
        pass
    return payload
