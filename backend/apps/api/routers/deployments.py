"""Deployments router — model deployments with canary, promote, and rollback."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from apps.api.routers.ai import AICompleteRequest, AICompleteResponse, complete
from db.models import Deployment, DeploymentStatus, DeploymentStrategy, User
from db.session import get_db


router = APIRouter(prefix="/deployments", tags=["deployments"])

_SLUG_RE = re.compile(r"[^a-z0-9-]+")


class DeploymentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: Optional[str] = Field(None, max_length=120)
    region: str = Field(..., min_length=1, max_length=64)
    service_type: str = Field("api", max_length=32)
    model_slug: Optional[str] = Field(None, max_length=120)
    provider: Optional[str] = Field(None, max_length=64)
    version: str = Field(..., min_length=1, max_length=64)
    strategy: str = Field("direct", pattern=r"^(direct|blue_green|canary)$")
    traffic_percent: int = Field(100, ge=0, le=100)


class DeploymentUpdateRequest(BaseModel):
    traffic_percent: Optional[int] = Field(None, ge=0, le=100)
    health_metrics: Optional[dict] = None
    status: Optional[str] = Field(None, pattern=r"^(active|inactive|failed|promoting|rolling_back)$")


class PromoteRequest(BaseModel):
    target_traffic_percent: int = Field(100, ge=1, le=100)


class DeploymentTestRequest(BaseModel):
    prompt: str = Field("Reply with exactly: OK", min_length=1, max_length=20000)
    max_tokens: int = Field(20, ge=1, le=512)


class DeploymentTestResponse(BaseModel):
    status: str
    response_text: str
    latency_ms: int
    provider: str
    model: str
    requested_model: str
    endpoint: str
    audit_log_id: str | None
    audit_created: bool
    usage_recorded: bool
    cost_usd: str
    reserve_units_debited: int
    request_id: str
    tested_at: str


def _slugify(s: str) -> str:
    s = _SLUG_RE.sub("-", s.lower()).strip("-")
    return s[:120] or f"deploy-{uuid.uuid4().hex[:8]}"


def _endpoint_path(d: Deployment) -> str:
    service_type = d.service_type or "api"
    slug = d.slug or d.name or d.id
    return f"https://api.veklom.com/v1/{service_type}/{slug}"


def _serialize(d: Deployment) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "slug": d.slug,
        "region": d.region,
        "service_type": d.service_type,
        "model_slug": d.model_slug,
        "provider": d.provider,
        "version": d.version,
        "previous_version": d.previous_version,
        "strategy": (d.strategy.value if hasattr(d.strategy, "value") else d.strategy) or "direct",
        "status": d.status.value if hasattr(d.status, "value") else d.status,
        "traffic_percent": d.traffic_percent if d.traffic_percent is not None else 100,
        "is_primary": bool(d.is_primary) if d.is_primary is not None else True,
        "health_metrics": d.health_metrics or {},
        "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
        "promoted_at": d.promoted_at.isoformat() if d.promoted_at else None,
        "rolled_back_at": d.rolled_back_at.isoformat() if d.rolled_back_at else None,
        "last_health_check": d.last_health_check.isoformat() if d.last_health_check else None,
    }


def _merge_health_metrics(d: Deployment, patch: dict) -> None:
    current = dict(d.health_metrics or {})
    current.update(patch)
    d.health_metrics = current
    d.last_health_check = datetime.utcnow()


@router.get("")
async def list_deployments(
    region: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Deployment).filter(Deployment.workspace_id == current_user.workspace_id)
    if region:
        q = q.filter(Deployment.region == region)
    if status:
        q = q.filter(Deployment.status == status)
    rows = q.order_by(Deployment.deployed_at.desc()).all()

    # Group by region for the UI's zone view.
    zones: dict[str, list[dict]] = {}
    for d in rows:
        zones.setdefault(d.region, []).append(_serialize(d))

    return {
        "total": len(rows),
        "items": [_serialize(d) for d in rows],
        "zones": [
            {"region": region, "deployments": items, "active_count": sum(1 for i in items if i["status"] == "active")}
            for region, items in zones.items()
        ],
    }


@router.post("", status_code=201)
async def create_deployment(
    payload: DeploymentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    slug = _slugify(payload.slug or payload.name)

    d = Deployment(
        workspace_id=current_user.workspace_id,
        name=payload.name,
        slug=slug,
        region=payload.region,
        service_type=payload.service_type,
        model_slug=payload.model_slug,
        provider=payload.provider,
        version=payload.version,
        strategy=DeploymentStrategy(payload.strategy),
        traffic_percent=payload.traffic_percent,
        is_primary=(payload.strategy == "direct"),
        status=DeploymentStatus.ACTIVE,
        deployed_at=datetime.utcnow(),
        created_by=current_user.id,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.get("/{deployment_id}")
async def get_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id, Deployment.workspace_id == current_user.workspace_id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Deployment not found")
    return _serialize(d)


@router.patch("/{deployment_id}")
async def update_deployment(
    deployment_id: str,
    payload: DeploymentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id, Deployment.workspace_id == current_user.workspace_id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Deployment not found")
    if payload.traffic_percent is not None:
        d.traffic_percent = payload.traffic_percent
    if payload.health_metrics is not None:
        d.health_metrics = payload.health_metrics
        d.last_health_check = datetime.utcnow()
    if payload.status is not None:
        d.status = DeploymentStatus(payload.status)
    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.post("/{deployment_id}/promote")
async def promote_deployment(
    deployment_id: str,
    payload: PromoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Promote a canary/blue-green deployment to a target traffic percent.

    On 100% promotion, the previous primary in the same region+model_slug is
    moved to inactive and this deployment becomes primary.
    """
    d = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id, Deployment.workspace_id == current_user.workspace_id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Deployment not found")
    if d.status in (DeploymentStatus.FAILED, DeploymentStatus.ROLLING_BACK):
        raise HTTPException(409, f"Cannot promote: status={d.status}")

    d.status = DeploymentStatus.PROMOTING
    d.traffic_percent = payload.target_traffic_percent
    db.commit()

    if payload.target_traffic_percent >= 100 and d.model_slug:
        # Demote prior primary in same region for the same model.
        prior = (
            db.query(Deployment)
            .filter(
                Deployment.workspace_id == current_user.workspace_id,
                Deployment.region == d.region,
                Deployment.model_slug == d.model_slug,
                Deployment.id != d.id,
                Deployment.is_primary == True,  # noqa: E712
            )
            .all()
        )
        for p in prior:
            p.is_primary = False
            p.status = DeploymentStatus.INACTIVE
            p.traffic_percent = 0
            d.previous_version = p.version
        d.is_primary = True

    d.status = DeploymentStatus.ACTIVE
    d.promoted_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.post("/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Roll back: reactivate the prior primary (if any) and mark this deployment inactive."""
    d = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id, Deployment.workspace_id == current_user.workspace_id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Deployment not found")

    d.status = DeploymentStatus.ROLLING_BACK
    db.commit()

    # Find the most recent prior primary for the same region+model.
    if d.model_slug:
        prior = (
            db.query(Deployment)
            .filter(
                Deployment.workspace_id == current_user.workspace_id,
                Deployment.region == d.region,
                Deployment.model_slug == d.model_slug,
                Deployment.id != d.id,
            )
            .order_by(Deployment.deployed_at.desc())
            .first()
        )
        if prior:
            prior.is_primary = True
            prior.status = DeploymentStatus.ACTIVE
            prior.traffic_percent = 100

    d.is_primary = False
    d.status = DeploymentStatus.INACTIVE
    d.traffic_percent = 0
    d.rolled_back_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.post("/{deployment_id}/test", response_model=DeploymentTestResponse)
async def test_deployment(
    deployment_id: str,
    payload: DeploymentTestRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id, Deployment.workspace_id == current_user.workspace_id)
        .first()
    )
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deployment not found")
    if d.status != DeploymentStatus.ACTIVE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Deployment is not active. Current status: {d.status.value if hasattr(d.status, 'value') else d.status}",
        )
    if not d.model_slug:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Deployment has no model configured")

    ai_payload = AICompleteRequest(
        model=d.model_slug,
        prompt=payload.prompt,
        max_tokens=payload.max_tokens,
        temperature=0,
        billing_event_type="governed_run",
        session_tag="Standard",
        auto_redact=True,
        sign_audit_on_export=True,
        lock_to_on_prem=(d.provider == "ollama"),
    )

    try:
        result: AICompleteResponse = await complete(
            payload=ai_payload,
            request=request,
            current_user=current_user,
            db=db,
        )
    except HTTPException as exc:
        _merge_health_metrics(
            d,
            {
                "last_test_status": "failed",
                "last_test_error": str(exc.detail),
                "last_test_http_status": exc.status_code,
                "last_tested_at": datetime.utcnow().isoformat() + "Z",
            },
        )
        db.commit()
        raise

    tested_at = datetime.utcnow()
    previous_series = []
    if isinstance((d.health_metrics or {}).get("rps_series"), list):
        previous_series = list((d.health_metrics or {}).get("rps_series") or [])
    rps_series = (previous_series + [1])[-32:]
    _merge_health_metrics(
        d,
        {
            "last_test_status": "passed",
            "last_tested_at": tested_at.isoformat() + "Z",
            "last_test_latency_ms": result.latency_ms,
            "last_test_provider": result.provider,
            "last_test_model": result.model,
            "last_test_audit_log_id": result.audit_log_id,
            "last_test_request_id": result.request_id,
            "p50_ms": result.latency_ms,
            "rps": max(1, int((d.health_metrics or {}).get("rps") or 0)),
            "rps_series": rps_series,
            "error_rate": 0,
        },
    )
    db.commit()
    db.refresh(d)

    return DeploymentTestResponse(
        status="passed",
        response_text=result.response_text,
        latency_ms=result.latency_ms,
        provider=result.provider,
        model=result.model,
        requested_model=result.requested_model,
        endpoint=_endpoint_path(d),
        audit_log_id=result.audit_log_id,
        audit_created=bool(result.audit_log_id),
        usage_recorded=result.reserve_units_debited >= 0,
        cost_usd=result.cost_usd,
        reserve_units_debited=result.reserve_units_debited,
        request_id=result.request_id,
        tested_at=tested_at.isoformat() + "Z",
    )


@router.delete("/{deployment_id}", status_code=204)
async def delete_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id, Deployment.workspace_id == current_user.workspace_id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Deployment not found")
    db.delete(d)
    db.commit()
    return None
