"""Veklom-only internal operator center.

This router is not a customer feature. It is the owner/operator surface for the
autonomous marketplace workers that run Veklom itself.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.config import get_settings
from db.models import APIKey, SecurityAuditLog, User, UserStatus
from db.session import get_db


router = APIRouter(prefix="/internal/operators", tags=["internal-operators"])
settings = get_settings()
MAX_DETAILS_BYTES = 20_000


class OperatorPrincipal(BaseModel):
    workspace_id: str | None
    user_id: str | None = None
    principal_type: Literal["superuser", "automation_key"]


class WorkerRunIn(BaseModel):
    worker_id: str = Field(..., min_length=2, max_length=64)
    status: Literal["ok", "warning", "failed", "blocked"]
    summary: str = Field(..., min_length=1, max_length=500)
    source: str = Field("operator-center", max_length=120)
    duration_ms: int | None = Field(None, ge=0, le=86_400_000)
    details: dict[str, Any] = Field(default_factory=dict)


class WorkerHeartbeatIn(BaseModel):
    status: Literal["ok", "warning", "failed", "blocked"] = "ok"
    summary: str = Field("heartbeat received", max_length=500)
    source: str = Field("operator-center", max_length=120)
    details: dict[str, Any] = Field(default_factory=dict)


WORKER_REGISTRY: dict[str, dict[str, Any]] = {
    "herald": {
        "name": "HERALD",
        "mission": "Own Resend funnels, vendor/buyer lifecycle messaging, suppression health, and deliverability.",
        "owned_surfaces": ["/api/v1/webhooks/resend", "Resend audiences", "vendor funnel", "regulated buyer funnel"],
        "required_config": ["RESEND_API_KEY", "RESEND_WEBHOOK_SECRET"],
        "hard_kpis": ["delivery_rate", "reply_rate", "qualified_meetings", "unsubscribe_rate"],
    },
    "harvest": {
        "name": "HARVEST",
        "mission": "Find and qualify marketplace vendors and regulated buyer accounts from compliant public sources.",
        "owned_surfaces": ["/api/v1/listings", "/api/v1/marketplace/vendors/onboard"],
        "required_config": [],
        "hard_kpis": ["qualified_leads", "vendor_signups", "buyer_accounts", "source_quality"],
    },
    "bouncer": {
        "name": "BOUNCER",
        "mission": "Run LockerSphere-backed intake defense, vendor review, abuse detection, and marketplace threat control.",
        "owned_surfaces": ["/api/v1/security", "/api/v1/locker/security", "/api/v1/content-safety"],
        "required_config": [],
        "hard_kpis": ["blocked_risk", "clean_vendor_rate", "review_sla", "security_events_resolved"],
    },
    "gauge": {
        "name": "GAUGE",
        "mission": "Monitor marketplace health, usage, route health, wallet drift, conversion, and operating metrics.",
        "owned_surfaces": ["/api/v1/monitoring", "/api/v1/billing", "/api/v1/wallet"],
        "required_config": ["DATABASE_URL"],
        "hard_kpis": ["uptime", "route_health", "wallet_drift", "conversion_rate"],
    },
    "ledger": {
        "name": "LEDGER",
        "mission": "Own audit packs, explainability reports, evidence bundles, privacy events, and proof exports.",
        "owned_surfaces": ["/api/v1/audit", "/api/v1/compliance", "/api/v1/explain", "/api/v1/privacy"],
        "required_config": [],
        "hard_kpis": ["evidence_generated", "audit_integrity", "export_success", "compliance_gap_count"],
    },
    "signal": {
        "name": "SIGNAL",
        "mission": "Track developer/community signal and turn marketplace proof into distribution loops.",
        "owned_surfaces": ["marketplace listings", "community research", "launch calendar"],
        "required_config": [],
        "hard_kpis": ["developer_mentions", "listing_views", "organic_sources", "community_replies"],
    },
    "oracle": {
        "name": "ORACLE",
        "mission": "Watch AI policy, procurement, sovereignty, privacy, and regulated-industry requirements.",
        "owned_surfaces": ["/api/v1/compliance/regulations", "policy watchlist"],
        "required_config": [],
        "hard_kpis": ["policy_updates", "country_watch_items", "regulatory_risk_reduction"],
    },
    "mint": {
        "name": "MINT",
        "mission": "Own pricing, wallet economics, packaging, top-ups, and conversion-sensitive monetization.",
        "owned_surfaces": ["/api/v1/subscriptions", "/api/v1/billing", "/api/v1/cost"],
        "required_config": ["STRIPE_SECRET_KEY"],
        "hard_kpis": ["activation_rate", "reserve_balance", "gross_margin", "top_up_conversion"],
    },
    "scout": {
        "name": "SCOUT",
        "mission": "Watch competitors, marketplace movement, partner signals, and category threats.",
        "owned_surfaces": ["competitor watchlist", "market signal log"],
        "required_config": [],
        "hard_kpis": ["signals_captured", "threats_ranked", "positioning_updates"],
    },
    "arbiter": {
        "name": "ARBITER",
        "mission": "Own vendor quality, dispute routing, install trust state, and review integrity.",
        "owned_surfaces": ["/api/v1/marketplace/listings/review", "/api/v1/marketplace/orders"],
        "required_config": [],
        "hard_kpis": ["review_quality", "dispute_resolution_time", "trusted_listing_rate"],
    },
}


def _config_present(key: str) -> bool:
    if key == "RESEND_API_KEY":
        return bool(settings.resend_api_key or os.getenv(key))
    if key == "RESEND_WEBHOOK_SECRET":
        return bool(settings.resend_webhook_secret or os.getenv(key))
    if key == "STRIPE_SECRET_KEY":
        return bool(settings.stripe_secret_key or os.getenv(key))
    if key == "DATABASE_URL":
        return bool(settings.database_url or os.getenv(key))
    return bool(os.getenv(key))


def _worker_payload(worker_id: str, worker: dict[str, Any]) -> dict[str, Any]:
    readiness = {
        key: _config_present(key)
        for key in worker.get("required_config", [])
    }
    missing = [key for key, present in readiness.items() if not present]
    return {
        "id": worker_id,
        "name": worker["name"],
        "mission": worker["mission"],
        "owned_surfaces": worker["owned_surfaces"],
        "hard_kpis": worker["hard_kpis"],
        "readiness": readiness,
        "missing_config": missing,
        "customer_visible": False,
        "ships_to_buyer_package": False,
        "status": "ready" if not missing else "needs_config",
    }


def _redact_details(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            upper = str(key).upper()
            if any(marker in upper for marker in ("SECRET", "TOKEN", "KEY", "PASSWORD")):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_details(item)
        return redacted
    if isinstance(value, list):
        return [_redact_details(item) for item in value]
    return value


def _safe_details_json(details: dict[str, Any]) -> str:
    redacted = _redact_details(details)
    encoded = json.dumps(redacted, sort_keys=True, default=str)
    if len(encoded.encode("utf-8")) > MAX_DETAILS_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Internal operator details payload is too large",
        )
    return encoded


def _is_active_superuser_key_owner(owner: User | None, api_key: APIKey) -> bool:
    """Return whether an API key is owned by an active platform superuser."""
    if owner is None:
        return False
    status_value = getattr(owner.status, "value", owner.status)
    return (
        bool(owner.is_superuser)
        and bool(owner.is_active)
        and status_value == UserStatus.ACTIVE.value
        and owner.workspace_id == api_key.workspace_id
    )


async def require_internal_operator(
    request: Request,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> OperatorPrincipal:
    if getattr(request.state, "is_superuser", False):
        return OperatorPrincipal(
            workspace_id=getattr(request.state, "workspace_id", None),
            user_id=getattr(request.state, "user_id", None),
            principal_type="superuser",
        )

    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header") from exc
    if scheme.lower() != "bearer" or not token.startswith("byos_"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Internal operator access required")

    key_hash = hashlib.sha256(token.encode()).hexdigest()
    api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash, APIKey.is_active.is_(True)).first()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid automation key")
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Automation key expired")
    scopes = set(api_key.scopes or [])
    if scopes.isdisjoint({"AUTOMATION", "ADMIN"}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Automation scope required")
    owner = db.query(User).filter(User.id == api_key.user_id).first()
    if not _is_active_superuser_key_owner(owner, api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser automation key required")
    return OperatorPrincipal(
        workspace_id=api_key.workspace_id,
        user_id=api_key.user_id,
        principal_type="automation_key",
    )


def _write_run_log(
    *,
    db: Session,
    principal: OperatorPrincipal,
    event_type: str,
    worker_id: str,
    status_value: str,
    summary: str,
    source: str,
    details: dict[str, Any],
) -> SecurityAuditLog:
    now = datetime.utcnow()
    safe_details = json.loads(_safe_details_json(details))
    row = SecurityAuditLog(
        workspace_id=principal.workspace_id,
        user_id=principal.user_id,
        event_type=event_type,
        event_category="internal_ops",
        success=status_value in {"ok", "warning"},
        failure_reason=None if status_value in {"ok", "warning"} else summary[:250],
        details=json.dumps(
            {
                "worker_id": worker_id,
                "worker_name": WORKER_REGISTRY.get(worker_id, {}).get("name", worker_id.upper()),
                "status": status_value,
                "summary": summary,
                "source": source,
                "details": safe_details,
                "customer_visible": False,
                "ships_to_buyer_package": False,
            },
            sort_keys=True,
            default=str,
        ),
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/overview")
async def operator_overview(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    workers = [_worker_payload(worker_id, worker) for worker_id, worker in WORKER_REGISTRY.items()]
    recent_failures = (
        db.query(SecurityAuditLog)
        .filter(SecurityAuditLog.event_category == "internal_ops", SecurityAuditLog.success.is_(False))
        .order_by(desc(SecurityAuditLog.created_at))
        .limit(10)
        .all()
    )
    return {
        "status": "ok",
        "visibility": "veklom_internal_only",
        "customer_visible": False,
        "ships_to_buyer_package": False,
        "worker_count": len(workers),
        "ready_workers": sum(1 for worker in workers if worker["status"] == "ready"),
        "needs_config": [worker["id"] for worker in workers if worker["status"] != "ready"],
        "recent_failure_count": len(recent_failures),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/workers")
async def list_workers(_: OperatorPrincipal = Depends(require_internal_operator)):
    return {
        "workers": [_worker_payload(worker_id, worker) for worker_id, worker in WORKER_REGISTRY.items()],
        "visibility": "veklom_internal_only",
    }


@router.get("/workers/{worker_id}")
async def get_worker(worker_id: str, _: OperatorPrincipal = Depends(require_internal_operator)):
    worker = WORKER_REGISTRY.get(worker_id.lower())
    if not worker:
        raise HTTPException(status_code=404, detail="Unknown worker")
    return _worker_payload(worker_id.lower(), worker)


@router.post("/workers/{worker_id}/heartbeat")
async def worker_heartbeat(
    worker_id: str,
    payload: WorkerHeartbeatIn,
    principal: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    worker_key = worker_id.lower()
    if worker_key not in WORKER_REGISTRY:
        raise HTTPException(status_code=404, detail="Unknown worker")
    row = _write_run_log(
        db=db,
        principal=principal,
        event_type="internal_worker_heartbeat",
        worker_id=worker_key,
        status_value=payload.status,
        summary=payload.summary,
        source=payload.source,
        details=payload.details,
    )
    return {"ok": True, "run_id": row.id, "worker_id": worker_key, "status": payload.status}


@router.post("/runs")
async def record_worker_run(
    payload: WorkerRunIn,
    principal: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    worker_key = payload.worker_id.lower()
    if worker_key not in WORKER_REGISTRY:
        raise HTTPException(status_code=404, detail="Unknown worker")
    details = dict(payload.details)
    if payload.duration_ms is not None:
        details["duration_ms"] = payload.duration_ms
    row = _write_run_log(
        db=db,
        principal=principal,
        event_type="internal_worker_run",
        worker_id=worker_key,
        status_value=payload.status,
        summary=payload.summary,
        source=payload.source,
        details=details,
    )
    return {"ok": True, "run_id": row.id, "worker_id": worker_key, "status": payload.status}


@router.get("/runs")
async def list_worker_runs(
    _: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=250),
):
    rows = (
        db.query(SecurityAuditLog)
        .filter(SecurityAuditLog.event_category == "internal_ops")
        .order_by(desc(SecurityAuditLog.created_at))
        .limit(limit)
        .all()
    )
    runs = []
    for row in rows:
        try:
            details = json.loads(row.details or "{}")
        except json.JSONDecodeError:
            details = {}
        runs.append(
            {
                "id": row.id,
                "event_type": row.event_type,
                "success": row.success,
                "failure_reason": row.failure_reason,
                "details": details,
                "created_at": row.created_at.isoformat() + "Z",
            }
        )
    return {"runs": runs, "count": len(runs)}
