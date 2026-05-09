"""Internal UACP bridge over backend product truth.

The backend owns product reality. UACP consumes this read-only bridge to map
real product events into pillars, committees, workers, and archive records.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from apps.api.routers.internal_operators import (
    COMMITTEE_REGISTRY,
    WORKER_REGISTRY,
    OperatorPrincipal,
    require_internal_operator,
)
from db.models import (
    AIAuditLog,
    Alert,
    Deployment,
    PipelineRun,
    SecurityAuditLog,
    Subscription,
    SubscriptionStatus,
    TokenTransaction,
    TokenWallet,
    User,
    Workspace,
    WorkspaceRequestLog,
)
from db.session import get_db


router = APIRouter(prefix="/internal/uacp", tags=["internal-uacp"])
RESERVE_UNITS_PER_USD = Decimal("1000")


EVENT_OWNERS: dict[str, dict[str, Any]] = {
    "ai.complete": {
        "pillar_ids": ["execution", "governance", "archives"],
        "committee_ids": ["governance-evidence", "experience-assurance"],
        "worker_ids": ["ledger", "pulse", "mirror"],
    },
    "request.failed": {
        "pillar_ids": ["product", "engineering", "operations"],
        "committee_ids": ["experience-assurance"],
        "worker_ids": ["sentinel", "sheriff", "pulse"],
    },
    "pipeline.run": {
        "pillar_ids": ["execution", "governance", "archives"],
        "committee_ids": ["governance-evidence", "experience-assurance"],
        "worker_ids": ["ledger", "sentinel", "mirror"],
    },
    "deployment.state": {
        "pillar_ids": ["engineering", "operations"],
        "committee_ids": ["experience-assurance"],
        "worker_ids": ["sentinel", "sheriff", "glide"],
    },
    "billing.reserve": {
        "pillar_ids": ["finance", "governance"],
        "committee_ids": ["growth-intelligence", "marketplace-operations"],
        "worker_ids": ["mint", "gauge", "ledger"],
    },
    "security.audit": {
        "pillar_ids": ["security", "governance", "archives"],
        "committee_ids": ["governance-evidence"],
        "worker_ids": ["bouncer", "ledger", "oracle"],
    },
    "workspace.created": {
        "pillar_ids": ["growth", "product"],
        "committee_ids": ["growth-intelligence", "experience-assurance"],
        "worker_ids": ["welcome", "signal", "mirror"],
    },
    "subscription.state": {
        "pillar_ids": ["finance", "growth"],
        "committee_ids": ["growth-intelligence"],
        "worker_ids": ["mint", "gauge"],
    },
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + "Z" if value else None


def _enum_value(value: Any) -> str:
    return getattr(value, "value", value) or ""


def _safe_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {"raw": raw[:500]}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _severity_for_status(status_value: str, default: str = "info") -> str:
    normalized = (status_value or "").lower()
    if normalized in {"failed", "failure", "error", "blocked", "blocked_policy"}:
        return "error"
    if normalized in {"warning", "past_due", "degraded"}:
        return "warning"
    return default


def _owner_mapping(event_type: str) -> dict[str, list[str]]:
    owner = EVENT_OWNERS.get(event_type, EVENT_OWNERS.get(event_type.split(":")[0], {}))
    return {
        "pillar_ids": list(owner.get("pillar_ids", ["operations"])),
        "committee_ids": list(owner.get("committee_ids", ["experience-assurance"])),
        "worker_ids": list(owner.get("worker_ids", ["sentinel"])),
    }


def _event(
    *,
    event_id: str,
    event_type: str,
    workspace_id: str | None,
    user_id: str | None,
    entity_type: str,
    entity_id: str,
    severity: str,
    status: str,
    timestamp: datetime | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "source": "veklom_backend",
        "workspace_id": workspace_id,
        "tenant_id": workspace_id,
        "user_id": user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "severity": severity,
        "status": status,
        "timestamp": _iso(timestamp),
        "payload": payload,
        "uacp": _owner_mapping(event_type),
    }


def _cash_reserve_usd(units: int | None) -> str:
    return f"{(Decimal(int(units or 0)) / RESERVE_UNITS_PER_USD):.2f}"


def _count(db: Session, model: Any, *criteria: Any) -> int:
    query = db.query(func.count(model.id))
    if criteria:
        query = query.filter(*criteria)
    return int(query.scalar() or 0)


def _recent_events(db: Session, limit: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for row in (
        db.query(AIAuditLog)
        .order_by(desc(AIAuditLog.created_at))
        .limit(limit)
        .all()
    ):
        events.append(
            _event(
                event_id=f"ai_audit:{row.id}",
                event_type="ai.complete",
                workspace_id=row.workspace_id,
                user_id=row.user_id,
                entity_type="ai_audit",
                entity_id=row.id,
                severity="info",
                status="succeeded",
                timestamp=row.created_at,
                payload={
                    "audit_id": row.id,
                    "provider": row.provider,
                    "model": row.model,
                    "latency_ms": None,
                    "cost_usd": str(row.cost),
                    "tokens_in": row.tokens_input,
                    "tokens_out": row.tokens_output,
                    "pii_detected": row.pii_detected,
                    "log_hash": row.log_hash,
                    "previous_log_hash": row.previous_log_hash,
                },
            )
        )

    for row in (
        db.query(WorkspaceRequestLog)
        .order_by(desc(WorkspaceRequestLog.created_at))
        .limit(limit)
        .all()
    ):
        status_value = str(row.status or "unknown")
        event_type = "request.failed" if _severity_for_status(status_value) == "error" else row.request_kind
        events.append(
            _event(
                event_id=f"request:{row.id}",
                event_type=event_type,
                workspace_id=row.workspace_id,
                user_id=row.user_id,
                entity_type="workspace_request",
                entity_id=row.id,
                severity=_severity_for_status(status_value),
                status=status_value,
                timestamp=row.created_at,
                payload={
                    "request_kind": row.request_kind,
                    "request_path": row.request_path,
                    "provider": row.provider,
                    "model": row.model,
                    "latency_ms": row.latency_ms,
                    "cost_usd": str(row.cost_usd),
                    "tokens_in": row.tokens_in,
                    "tokens_out": row.tokens_out,
                    "error_message": row.error_message,
                    "source_table": row.source_table,
                    "source_id": row.source_id,
                },
            )
        )

    for row in (
        db.query(PipelineRun)
        .order_by(desc(PipelineRun.created_at))
        .limit(limit)
        .all()
    ):
        status_value = _enum_value(row.status)
        events.append(
            _event(
                event_id=f"pipeline_run:{row.id}",
                event_type="pipeline.run",
                workspace_id=row.workspace_id,
                user_id=row.triggered_by,
                entity_type="pipeline",
                entity_id=row.pipeline_id,
                severity=_severity_for_status(status_value),
                status=status_value,
                timestamp=row.created_at,
                payload={
                    "run_id": row.id,
                    "pipeline_id": row.pipeline_id,
                    "version": row.version,
                    "latency_ms": row.total_latency_ms,
                    "cost_usd": row.total_cost_usd,
                    "error_message": row.error_message,
                    "step_count": len(row.step_trace or []),
                },
            )
        )

    for row in (
        db.query(Deployment)
        .order_by(desc(Deployment.updated_at), desc(Deployment.deployed_at))
        .limit(limit)
        .all()
    ):
        status_value = _enum_value(row.status)
        events.append(
            _event(
                event_id=f"deployment:{row.id}",
                event_type="deployment.state",
                workspace_id=row.workspace_id,
                user_id=row.created_by,
                entity_type="deployment",
                entity_id=row.id,
                severity=_severity_for_status(status_value),
                status=status_value,
                timestamp=row.updated_at or row.deployed_at,
                payload={
                    "name": row.name,
                    "slug": row.slug,
                    "model_slug": row.model_slug,
                    "provider": row.provider,
                    "region": row.region,
                    "strategy": _enum_value(row.strategy),
                    "traffic_percent": row.traffic_percent,
                    "last_health_check": _iso(row.last_health_check),
                    "health_metrics": row.health_metrics or {},
                },
            )
        )

    for row in (
        db.query(TokenTransaction)
        .order_by(desc(TokenTransaction.created_at))
        .limit(limit)
        .all()
    ):
        tx_type = row.transaction_type
        events.append(
            _event(
                event_id=f"wallet_tx:{row.id}",
                event_type="billing.reserve",
                workspace_id=row.workspace_id,
                user_id=None,
                entity_type="wallet_transaction",
                entity_id=row.id,
                severity="info",
                status=tx_type,
                timestamp=row.created_at,
                payload={
                    "transaction_type": tx_type,
                    "amount_units": row.amount,
                    "amount_usd": _cash_reserve_usd(abs(row.amount)),
                    "balance_before_units": row.balance_before,
                    "balance_after_units": row.balance_after,
                    "endpoint_path": row.endpoint_path,
                    "request_id": row.request_id,
                    "description": row.description,
                    "metadata": _safe_json(row.metadata_json),
                },
            )
        )

    for row in (
        db.query(SecurityAuditLog)
        .order_by(desc(SecurityAuditLog.created_at))
        .limit(limit)
        .all()
    ):
        events.append(
            _event(
                event_id=f"security_audit:{row.id}",
                event_type="security.audit",
                workspace_id=row.workspace_id,
                user_id=row.user_id,
                entity_type="security_audit",
                entity_id=row.id,
                severity="info" if row.success else "error",
                status="succeeded" if row.success else "failed",
                timestamp=row.created_at,
                payload={
                    "event_type": row.event_type,
                    "event_category": row.event_category,
                    "failure_reason": row.failure_reason,
                    "details": _safe_json(row.details),
                },
            )
        )

    events.sort(key=lambda event: event.get("timestamp") or "", reverse=True)
    return events[:limit]


@router.get("/summary")
async def uacp_summary(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    since_24h = now - timedelta(days=1)
    wallet_units = int(db.query(func.coalesce(func.sum(TokenWallet.balance), 0)).scalar() or 0)
    run_count_24h = _count(db, WorkspaceRequestLog, WorkspaceRequestLog.created_at >= since_24h)
    failed_count_24h = _count(
        db,
        WorkspaceRequestLog,
        WorkspaceRequestLog.created_at >= since_24h,
        WorkspaceRequestLog.status.notin_(["success", "ok", "200", "completed"]),
    )
    return {
        "source": "veklom_backend",
        "contract_version": "uacp_backend_information_contract_v1",
        "generated_at": _iso(now),
        "product_truth": {
            "workspaces": _count(db, Workspace),
            "active_workspaces": _count(db, Workspace, Workspace.is_active.is_(True)),
            "users": _count(db, User),
            "active_users": _count(db, User, User.is_active.is_(True)),
            "subscriptions": _count(db, Subscription),
            "active_subscriptions": _count(db, Subscription, Subscription.status == SubscriptionStatus.ACTIVE),
            "reserve_balance_units": wallet_units,
            "reserve_balance_usd": _cash_reserve_usd(wallet_units),
            "requests_24h": run_count_24h,
            "failed_requests_24h": failed_count_24h,
            "ai_audits_24h": _count(db, AIAuditLog, AIAuditLog.created_at >= since_24h),
            "pipeline_runs_24h": _count(db, PipelineRun, PipelineRun.created_at >= since_24h),
            "deployments": _count(db, Deployment),
            "open_alerts": _count(db, Alert, Alert.status == "open"),
        },
        "uacp_truth": {
            "worker_count": len(WORKER_REGISTRY),
            "committee_count": len(COMMITTEE_REGISTRY),
            "event_owner_mappings": len(EVENT_OWNERS),
            "write_surface": "/api/v1/internal/operators/runs",
            "read_surface": "/api/v1/internal/uacp/events",
        },
        "permission_boundary": {
            "backend_writes": ["product_events", "runs", "billing", "evidence", "workspace_state", "deployment_state", "security_events"],
            "uacp_writes": ["worker_runs", "decisions", "escalations", "archive_records", "recommendations"],
            "blocked_without_approval": ["change_pricing", "delete_user_data", "rotate_production_secrets", "ship_code", "change_compliance_claims"],
        },
    }


@router.get("/events")
async def uacp_events(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    return {
        "source": "veklom_backend",
        "contract_version": "uacp_backend_information_contract_v1",
        "events": _recent_events(db, limit),
    }


@router.get("/event-stream")
async def uacp_event_stream(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    return {
        "stream": "snapshot",
        "source": "veklom_backend",
        "contract_version": "uacp_backend_information_contract_v1",
        "events": _recent_events(db, limit),
    }


@router.get("/workspaces")
async def uacp_workspaces(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(Workspace).order_by(desc(Workspace.created_at)).limit(limit).all()
    return {
        "workspaces": [
            {
                "workspace_id": row.id,
                "tenant_id": row.id,
                "name": row.name,
                "slug": row.slug,
                "is_active": row.is_active,
                "license_tier": row.license_tier,
                "created_at": _iso(row.created_at),
                "updated_at": _iso(row.updated_at),
            }
            for row in rows
        ]
    }


@router.get("/runs")
async def uacp_runs(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(WorkspaceRequestLog).order_by(desc(WorkspaceRequestLog.created_at)).limit(limit).all()
    return {
        "runs": [
            {
                "run_id": row.id,
                "workspace_id": row.workspace_id,
                "user_id": row.user_id,
                "request_kind": row.request_kind,
                "request_path": row.request_path,
                "status": row.status,
                "provider": row.provider,
                "model": row.model,
                "latency_ms": row.latency_ms,
                "cost_usd": str(row.cost_usd),
                "tokens_in": row.tokens_in,
                "tokens_out": row.tokens_out,
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ]
    }


@router.get("/deployments")
async def uacp_deployments(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(Deployment).order_by(desc(Deployment.updated_at), desc(Deployment.deployed_at)).limit(limit).all()
    return {
        "deployments": [
            {
                "deployment_id": row.id,
                "workspace_id": row.workspace_id,
                "name": row.name,
                "slug": row.slug,
                "status": _enum_value(row.status),
                "provider": row.provider,
                "model_slug": row.model_slug,
                "region": row.region,
                "strategy": _enum_value(row.strategy),
                "traffic_percent": row.traffic_percent,
                "last_health_check": _iso(row.last_health_check),
                "updated_at": _iso(row.updated_at),
            }
            for row in rows
        ]
    }


@router.get("/billing")
async def uacp_billing(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    txs = db.query(TokenTransaction).order_by(desc(TokenTransaction.created_at)).limit(limit).all()
    return {
        "reserve_units_total": int(db.query(func.coalesce(func.sum(TokenWallet.balance), 0)).scalar() or 0),
        "transactions": [
            {
                "transaction_id": row.id,
                "workspace_id": row.workspace_id,
                "transaction_type": row.transaction_type,
                "amount_units": row.amount,
                "amount_usd": _cash_reserve_usd(abs(row.amount)),
                "balance_after_units": row.balance_after,
                "description": row.description,
                "metadata": _safe_json(row.metadata_json),
                "created_at": _iso(row.created_at),
            }
            for row in txs
        ],
    }


@router.get("/evidence")
async def uacp_evidence(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(AIAuditLog).order_by(desc(AIAuditLog.created_at)).limit(limit).all()
    return {
        "evidence": [
            {
                "audit_id": row.id,
                "workspace_id": row.workspace_id,
                "user_id": row.user_id,
                "operation_type": row.operation_type,
                "provider": row.provider,
                "model": row.model,
                "cost_usd": str(row.cost),
                "log_hash": row.log_hash,
                "previous_log_hash": row.previous_log_hash,
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ]
    }


@router.get("/monitoring")
async def uacp_monitoring(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    return await uacp_summary(_, db)


@router.get("/security")
async def uacp_security(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(SecurityAuditLog).order_by(desc(SecurityAuditLog.created_at)).limit(limit).all()
    return {
        "security_events": [
            {
                "event_id": row.id,
                "workspace_id": row.workspace_id,
                "user_id": row.user_id,
                "event_type": row.event_type,
                "event_category": row.event_category,
                "success": row.success,
                "failure_reason": row.failure_reason,
                "details": _safe_json(row.details),
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ]
    }
