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
    Listing,
    MarketplaceOrder,
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
UACP_SOURCE_TAG = "veklom_backend"
UACP_CONTRACT_VERSION = "uacp_backend_information_contract_v1"
UACP_REDIS_EVENT_STREAM_KEY = "uacp:v5:event-stream"

try:
    from db.models.veklom_run import VeklomRun
except ImportError:
    VeklomRun = None


def _uacp_response(payload: dict[str, Any], source: str | None = None) -> dict[str, Any]:
    return {
        "source": source or UACP_SOURCE_TAG,
        "contract_version": UACP_CONTRACT_VERSION,
        **payload,
    }


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


def _bounded_score(value: int) -> int:
    return max(0, min(100, int(value)))


def _workspace_top_action(
    *,
    tier: str,
    runs_used: int,
    endpoint_created: bool,
    endpoint_tested: bool,
    evidence_count: int,
    reserve_units: int,
    error_count: int,
) -> str:
    if error_count:
        return "Inspect failed route and assign sentinel/sheriff before buyer follow-up."
    if tier == "free" and runs_used >= 15:
        return "Explain activation, reserve funding, and regulated access path."
    if endpoint_created and not endpoint_tested:
        return "Guide buyer to test the endpoint on-page and create proof."
    if endpoint_tested and evidence_count == 0:
        return "Open evidence trail and show the audit artifact generated by the test."
    if endpoint_tested and reserve_units <= 0:
        return "Explain operating reserve before production routing."
    if runs_used > 0:
        return "Send focused onboarding note tied to their last governed run."
    return "Wait for first governed action; no intervention without product evidence."


def _evaluation_score(
    *,
    tier: str,
    runs_used: int,
    endpoint_created: bool,
    endpoint_tested: bool,
    evidence_count: int,
    billing_events: int,
    reserve_units: int,
    error_count: int,
) -> tuple[int, int]:
    activation = 0
    activation += min(runs_used, 15) * 3
    activation += 12 if endpoint_created else 0
    activation += 18 if endpoint_tested else 0
    activation += 12 if evidence_count else 0
    activation += 10 if billing_events else 0
    activation += 15 if reserve_units > 0 else 0
    activation += 20 if tier != "free" else 0
    activation -= min(error_count * 8, 24)

    risk = 0
    risk += min(error_count * 20, 60)
    risk += 25 if tier == "free" and runs_used >= 15 else 0
    risk += 18 if endpoint_created and not endpoint_tested else 0
    risk += 15 if endpoint_tested and reserve_units <= 0 else 0
    risk += 10 if runs_used == 0 else 0
    return _bounded_score(activation), _bounded_score(risk)


def _assigned_workers_for_evaluation(
    *,
    error_count: int,
    endpoint_created: bool,
    endpoint_tested: bool,
    evidence_count: int,
    reserve_units: int,
) -> list[str]:
    workers = ["gauge", "welcome"]
    if error_count:
        workers.extend(["sentinel", "sheriff"])
    if endpoint_created or endpoint_tested:
        workers.append("mirror")
    if evidence_count or endpoint_tested:
        workers.append("ledger")
    if reserve_units <= 0 and (endpoint_created or endpoint_tested):
        workers.append("mint")
    return list(dict.fromkeys(workers))


def _growth_action(kind: str, *, failures: int = 0, orders: int = 0, installs: int = 0) -> str:
    if kind == "failed_route":
        return "Convert repeated integration failure into a governed connector or repair task."
    if kind == "listing_signal" and orders:
        return "Promote demand-backed listing and assign harvest/signal for distribution."
    if kind == "listing_signal" and installs == 0:
        return "Review listing packaging and create a clearer test/install path."
    if kind == "marketplace_order":
        return "Check fulfillment proof, buyer fit, and follow-on tool opportunity."
    return "Hold until more backend evidence lands."


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


def _recent_redis_uacp_events(limit: int) -> list[dict[str, Any]]:
    try:
        from core.redis_pool import get_redis

        redis_client = get_redis()
        if redis_client is None:
            return []
        raw_events = redis_client.lrange(UACP_REDIS_EVENT_STREAM_KEY, 0, max(0, limit - 1))
    except Exception:
        return []

    events: list[dict[str, Any]] = []
    for raw_event in raw_events or []:
        try:
            if isinstance(raw_event, bytes):
                raw_event = raw_event.decode("utf-8")
            parsed = json.loads(raw_event)
        except (TypeError, ValueError, UnicodeDecodeError):
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events[:limit]


def _merge_events(primary: list[dict[str, Any]], secondary: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for event in [*primary, *secondary]:
        event_id = str(event.get("event_id") or "")
        if event_id and event_id in seen:
            continue
        if event_id:
            seen.add(event_id)
        merged.append(event)
        if len(merged) >= limit:
            break
    return merged


def _evaluation_surgeon_queue(db: Session, limit: int) -> list[dict[str, Any]]:
    rows = db.query(Workspace).order_by(desc(Workspace.created_at)).limit(limit).all()
    queue: list[dict[str, Any]] = []

    for workspace in rows:
        users = db.query(User).filter(User.workspace_id == workspace.id).all()
        primary_user = next((user for user in users if user.is_active), users[0] if users else None)
        active_sub = (
            db.query(Subscription)
            .filter(
                Subscription.workspace_id == workspace.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )
        tier = _enum_value(active_sub.plan) if active_sub else "free"
        wallet = db.query(TokenWallet).filter(TokenWallet.workspace_id == workspace.id).first()
        reserve_units = int(wallet.balance if wallet else 0)
        request_count = _count(db, WorkspaceRequestLog, WorkspaceRequestLog.workspace_id == workspace.id)
        pipeline_count = _count(db, PipelineRun, PipelineRun.workspace_id == workspace.id)
        runs_used = request_count + pipeline_count
        failed_runs = _count(
            db,
            WorkspaceRequestLog,
            WorkspaceRequestLog.workspace_id == workspace.id,
            WorkspaceRequestLog.status.notin_(["success", "ok", "200", "completed", "succeeded"]),
        )
        deployments = db.query(Deployment).filter(Deployment.workspace_id == workspace.id).all()
        endpoint_created = bool(deployments)
        txs = (
            db.query(TokenTransaction)
            .filter(TokenTransaction.workspace_id == workspace.id)
            .order_by(desc(TokenTransaction.created_at))
            .limit(50)
            .all()
        )
        endpoint_tested = any(
            "endpoint_test" in json.dumps(_safe_json(tx.metadata_json))
            or (tx.endpoint_path or "").endswith("/test")
            for tx in txs
        )
        evidence_count = _count(db, AIAuditLog, AIAuditLog.workspace_id == workspace.id)
        billing_events = len(txs)
        last_request = (
            db.query(WorkspaceRequestLog.created_at)
            .filter(WorkspaceRequestLog.workspace_id == workspace.id)
            .order_by(desc(WorkspaceRequestLog.created_at))
            .first()
        )
        last_pipeline = (
            db.query(PipelineRun.created_at)
            .filter(PipelineRun.workspace_id == workspace.id)
            .order_by(desc(PipelineRun.created_at))
            .first()
        )
        last_tx = (
            db.query(TokenTransaction.created_at)
            .filter(TokenTransaction.workspace_id == workspace.id)
            .order_by(desc(TokenTransaction.created_at))
            .first()
        )
        timestamps = [
            workspace.updated_at,
            last_request[0] if last_request else None,
            last_pipeline[0] if last_pipeline else None,
            last_tx[0] if last_tx else None,
        ]
        last_activity = max((ts for ts in timestamps if ts is not None), default=workspace.created_at)
        activation_score, risk_score = _evaluation_score(
            tier=tier,
            runs_used=runs_used,
            endpoint_created=endpoint_created,
            endpoint_tested=endpoint_tested,
            evidence_count=evidence_count,
            billing_events=billing_events,
            reserve_units=reserve_units,
            error_count=failed_runs,
        )
        top_action = _workspace_top_action(
            tier=tier,
            runs_used=runs_used,
            endpoint_created=endpoint_created,
            endpoint_tested=endpoint_tested,
            evidence_count=evidence_count,
            reserve_units=reserve_units,
            error_count=failed_runs,
        )
        assigned_workers = _assigned_workers_for_evaluation(
            error_count=failed_runs,
            endpoint_created=endpoint_created,
            endpoint_tested=endpoint_tested,
            evidence_count=evidence_count,
            reserve_units=reserve_units,
        )

        queue.append(
            {
                "workspace_id": workspace.id,
                "tenant_id": workspace.id,
                "workspace": workspace.name,
                "workspace_slug": workspace.slug,
                "user_id": primary_user.id if primary_user else None,
                "user_handle": (primary_user.email.split("@", 1)[0] if primary_user and primary_user.email else None),
                "tier": tier,
                "runs_used": runs_used,
                "free_evaluation_limit": 15 if tier == "free" else None,
                "last_activity": _iso(last_activity),
                "endpoint_status": "tested" if endpoint_tested else ("created" if endpoint_created else "none"),
                "evidence_activity": {
                    "audit_entries": evidence_count,
                    "status": "present" if evidence_count else "none",
                },
                "billing_state": {
                    "reserve_units": reserve_units,
                    "reserve_usd": _cash_reserve_usd(reserve_units),
                    "transactions": billing_events,
                    "paid_active": bool(active_sub),
                },
                "security_state": {
                    "mfa_enabled_users": sum(1 for user in users if user.mfa_enabled),
                    "active_users": sum(1 for user in users if user.is_active),
                },
                "risk_score": risk_score,
                "activation_probability": activation_score,
                "top_action": top_action,
                "assigned_workers": assigned_workers,
                "committee_id": "experience-assurance",
                "pillar_ids": ["product", "growth", "finance"],
                "archive_ref": f"evaluation_signal:{workspace.id}",
                "evidence": {
                    "requests": request_count,
                    "pipeline_runs": pipeline_count,
                    "failed_runs": failed_runs,
                    "deployments": len(deployments),
                    "audit_entries": evidence_count,
                    "billing_events": billing_events,
                },
                "status": "needs_attention" if risk_score >= 50 or activation_score >= 50 else "watching",
            }
        )

    queue.sort(key=lambda item: (item["activation_probability"], item["risk_score"], item["runs_used"]), reverse=True)
    return queue[:limit]


def _growth_opportunities(db: Session, limit: int) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []
    now = datetime.utcnow()
    since_7d = now - timedelta(days=7)

    failures_label = func.count(WorkspaceRequestLog.id).label("failures")
    last_seen_label = func.max(WorkspaceRequestLog.created_at).label("last_seen")
    failed_paths = (
        db.query(
            WorkspaceRequestLog.request_path,
            WorkspaceRequestLog.provider,
            failures_label,
            last_seen_label,
        )
        .filter(WorkspaceRequestLog.status.notin_(["success", "ok", "200", "completed", "succeeded"]))
        .group_by(WorkspaceRequestLog.request_path, WorkspaceRequestLog.provider)
        .order_by(desc(failures_label))
        .limit(limit)
        .all()
    )
    for path, provider, failures, last_seen in failed_paths:
        score = _bounded_score(35 + int(failures or 0) * 12)
        opportunities.append(
            {
                "opportunity_id": f"failed_route:{path or 'unknown'}:{provider or 'unknown'}",
                "kind": "failed_route",
                "title": f"Repair or productize {path or 'unknown route'}",
                "score": score,
                "risk": score,
                "source_event": "request.failed",
                "evidence": {
                    "failed_requests": int(failures or 0),
                    "provider": provider,
                    "last_seen": _iso(last_seen),
                },
                "recommended_action": _growth_action("failed_route", failures=int(failures or 0)),
                "assigned_workers": ["sentinel", "sheriff", "builder-scout", "builder-arbiter"],
                "committee_id": "builder-systems",
                "pillar_ids": ["engineering", "product", "growth"],
                "archive_ref": f"growth_signal:failed_route:{path or 'unknown'}",
                "status": "ready_for_review",
            }
        )

    if Listing is not None:
        listings = (
            db.query(Listing)
            .filter(Listing.status == "active")
            .order_by(desc(Listing.updated_at), desc(Listing.created_at))
            .limit(limit)
            .all()
        )
        for listing in listings:
            order_count = 0
            if MarketplaceOrder is not None:
                order_count = _count(
                    db,
                    MarketplaceOrder,
                    MarketplaceOrder.workspace_id == listing.workspace_id,
                    MarketplaceOrder.status.in_(["paid", "fulfilled"]),
                    MarketplaceOrder.created_at >= since_7d,
                )
            installs = int(listing.install_count or 0)
            score = _bounded_score(30 + min(installs, 20) * 2 + order_count * 12 + (10 if listing.is_featured else 0))
            opportunities.append(
                {
                    "opportunity_id": f"listing:{listing.id}",
                    "kind": "listing_signal",
                    "title": listing.title,
                    "score": score,
                    "risk": 20 if installs else 45,
                    "source_event": "marketplace.listing",
                    "evidence": {
                        "listing_id": listing.id,
                        "listing_type": listing.listing_type,
                        "category": listing.category,
                        "install_count": installs,
                        "orders_7d": order_count,
                        "price_cents": listing.price_cents,
                        "source_url": listing.source_url,
                    },
                    "recommended_action": _growth_action("listing_signal", orders=order_count, installs=installs),
                    "assigned_workers": ["harvest", "signal", "builder-scout", "builder-arbiter"],
                    "committee_id": "growth-intelligence",
                    "pillar_ids": ["growth", "marketplace", "engineering"],
                    "archive_ref": f"growth_signal:listing:{listing.id}",
                    "status": "ready_for_review" if score >= 50 else "watching",
                }
            )

    if MarketplaceOrder is not None:
        orders = (
            db.query(MarketplaceOrder)
            .filter(MarketplaceOrder.status.in_(["paid", "fulfilled"]))
            .order_by(desc(MarketplaceOrder.created_at))
            .limit(limit)
            .all()
        )
        for order in orders:
            opportunities.append(
                {
                    "opportunity_id": f"marketplace_order:{order.id}",
                    "kind": "marketplace_order",
                    "title": "Marketplace demand signal",
                    "score": _bounded_score(45 + min(int(order.total_cents or 0) // 1000, 35)),
                    "risk": 25 if order.status == "fulfilled" else 40,
                    "source_event": "marketplace.order",
                    "evidence": {
                        "order_id": order.id,
                        "workspace_id": order.workspace_id,
                        "status": order.status,
                        "total_cents": order.total_cents,
                        "created_at": _iso(order.created_at),
                    },
                    "recommended_action": _growth_action("marketplace_order"),
                    "assigned_workers": ["harvest", "mint", "ledger", "signal"],
                    "committee_id": "marketplace-operations",
                    "pillar_ids": ["growth", "finance", "marketplace"],
                    "archive_ref": f"growth_signal:marketplace_order:{order.id}",
                    "status": "ready_for_review",
                }
            )

    opportunities.sort(key=lambda item: (item["score"], -item["risk"]), reverse=True)
    return opportunities[:limit]


async def _uacp_summary_payload(
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
    evaluation_queue = _evaluation_surgeon_queue(db, 25)
    growth_opportunities = _growth_opportunities(db, 25)
    return {
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
            "evaluation_surgeon_queue_count": len(evaluation_queue),
            "growth_opportunity_count": len(growth_opportunities),
        },
        "sunnyvale": {
            "evaluation_surgeon_queue": evaluation_queue,
            "hub_growth_opportunities": growth_opportunities,
            "empty_state": {
                "evaluation_surgeon_queue": (
                    "No backend evaluation, billing, endpoint, evidence, or security events have landed yet."
                    if not evaluation_queue
                    else None
                ),
                "hub_growth_opportunities": (
                    "No marketplace, integration, or failed-route signals have landed yet."
                    if not growth_opportunities
                    else None
                ),
            },
        },
        "permission_boundary": {
            "backend_writes": ["product_events", "runs", "billing", "evidence", "workspace_state", "deployment_state", "security_events"],
            "uacp_writes": ["worker_runs", "decisions", "escalations", "archive_records", "recommendations"],
            "blocked_without_approval": ["change_pricing", "delete_user_data", "rotate_production_secrets", "ship_code", "change_compliance_claims"],
        },
    }


@router.get("/summary")
async def uacp_summary(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    return _uacp_response(await _uacp_summary_payload(_, db))


@router.get("/events")
async def uacp_events(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    return _uacp_response({"events": _recent_events(db, limit)})


@router.get("/event-stream")
async def uacp_event_stream(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    redis_events = _recent_redis_uacp_events(limit)
    events = _merge_events(redis_events, _recent_events(db, limit), limit)
    return _uacp_response({
        "stream": "redis_snapshot" if redis_events else "snapshot",
        "redis_backed": bool(redis_events),
        "events": events,
    })


@router.get("/evaluation-surgeon")
async def uacp_evaluation_surgeon(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    queue = _evaluation_surgeon_queue(db, limit)
    return _uacp_response({
        "queue": queue,
        "empty_reason": (
            "No live evaluation queue yet. Backend has no eligible workspace events to rank."
            if not queue
            else None
        ),
        "required_sources": ["workspaces", "runs", "billing", "deployments", "evidence", "security"],
    })


@router.get("/growth-opportunities")
async def uacp_growth_opportunities(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    opportunities = _growth_opportunities(db, limit)
    return _uacp_response({
        "opportunities": opportunities,
        "empty_reason": (
            "No qualified growth opportunities yet. Backend has no marketplace, integration, or failed-route signals to route."
            if not opportunities
            else None
        ),
        "required_sources": ["marketplace", "integrations", "failed_routes", "orders", "listings"],
    })


@router.get("/workspaces")
async def uacp_workspaces(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(Workspace).order_by(desc(Workspace.created_at)).limit(limit).all()
    return _uacp_response({
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
    })


@router.get("/runs")
async def uacp_runs(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    runs = []
    if VeklomRun is not None:
        runs = db.query(VeklomRun).order_by(desc(VeklomRun.created_at)).limit(limit).all()
    if not runs:
        rows = db.query(WorkspaceRequestLog).order_by(desc(WorkspaceRequestLog.created_at)).limit(limit).all()
        return _uacp_response(
            {
                "runs": [
                    {
                    "run_id": row.id,
                    "workspace_id": row.workspace_id,
                    "tenant_id": row.workspace_id,
                    "actor_id": row.user_id,
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
                    "source": "workspace_request_logs",
                    }
                    for row in rows
                ],
                "count": len(rows),
                "source": "workspace_request_logs",
            },
            source="workspace_request_logs",
        )
    return _uacp_response(
        {
            "runs": [
                {
                    "run_id": row.run_id,
                    "workspace_id": row.workspace_id,
                    "tenant_id": row.tenant_id,
                    "actor_id": row.actor_id,
                    "request_kind": "veklom.run",
                    "request_path": row.raw_intent,
                    "status": row.status.value if hasattr(row.status, "value") else row.status,
                    "governance_decision": row.governance_decision,
                    "risk_tier": row.risk_tier,
                    "provider": row.provider,
                    "model": row.model,
                    "debit_cents": str(row.debit_cents),
                    "genome_hash": row.genome_hash,
                    "input_hash": row.input_hash,
                    "output_hash": row.output_hash,
                    "decision_frame_hash": row.decision_frame_hash,
                    "request_log_id": row.request_log_id,
                    "created_at": _iso(row.created_at),
                    "updated_at": _iso(row.updated_at),
                    "sealed_at": _iso(row.sealed_at),
                    "source_table": row.source_table,
                    "source_id": row.source_id,
                    "source": "veklom_runs",
                }
                for row in runs
            ],
            "count": len(runs),
            "source": "veklom_runs",
        },
        source="veklom_runs",
    )


@router.get("/deployments")
async def uacp_deployments(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(Deployment).order_by(desc(Deployment.updated_at), desc(Deployment.deployed_at)).limit(limit).all()
    return _uacp_response({
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
    })


@router.get("/billing")
async def uacp_billing(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    txs = db.query(TokenTransaction).order_by(desc(TokenTransaction.created_at)).limit(limit).all()
    return _uacp_response({
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
    })


@router.get("/evidence")
async def uacp_evidence(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(AIAuditLog).order_by(desc(AIAuditLog.created_at)).limit(limit).all()
    return _uacp_response({
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
    })


@router.get("/monitoring")
async def uacp_monitoring(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    monitoring_payload = await _uacp_summary_payload(_, db)
    return _uacp_response(
        {
            "monitoring": {
                "generated_at": monitoring_payload.get("generated_at"),
                "product_truth": monitoring_payload.get("product_truth", {}),
                "uacp_truth": monitoring_payload.get("uacp_truth", {}),
                "permission_boundary": monitoring_payload.get("permission_boundary", {}),
                "healthy": monitoring_payload.get("permission_boundary") is not None,
            },
            "generated_at": monitoring_payload.get("generated_at"),
        }
    )


@router.get("/security")
async def uacp_security(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.query(SecurityAuditLog).order_by(desc(SecurityAuditLog.created_at)).limit(limit).all()
    return _uacp_response({
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
    })
