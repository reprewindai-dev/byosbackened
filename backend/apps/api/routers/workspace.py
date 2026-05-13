"""Workspace gateway dashboard APIs."""
from __future__ import annotations

import hashlib
import html
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from core.notifications.emailer import send_email
from core.security.encryption import encrypt_field
from core.services.workspace_profiles import (
    build_static_gpc_handoff,
    dumps_payload,
    ensure_workspace_profile_defaults,
    normalize_industry,
    resolve_workspace_profile,
)
from db.models import (
    CommercialArtifact,
    InviteStatus,
    ProductUsageEvent,
    StatusSubscription,
    User,
    UserRole,
    Workspace,
    WorkspaceInvite,
)
from db.session import get_db
from core.services.financial_analytics import (
    fetch_workspace_request_metrics,
    workspace_financial_summary,
)
from core.services.workspace_gateway import (
    fetch_api_key_rows,
    fetch_cost_budget_payload,
    fetch_observability_payload,
    fetch_overview,
    fetch_public_status_payload,
    fetch_model_rows,
    set_model_enabled,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])
public_router = APIRouter(tags=["public-status"])
settings = get_settings()


class ModelToggleRequest(BaseModel):
    enabled: bool


class BudgetUpdateRequest(BaseModel):
    budget_type: str = "monthly"
    amount: Decimal
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    alert_thresholds: Optional[list[int]] = [50, 80, 95]


class StatusSubscribeRequest(BaseModel):
    channel: str
    target: str


class WorkspaceProfileUpdateRequest(BaseModel):
    industry: Optional[str] = None


class PlaygroundHandoffRequest(BaseModel):
    scenario_id: str
    scenario_title: Optional[str] = None
    user_input: str = Field(default="", max_length=12000)


class CommercialArtifactCreateRequest(BaseModel):
    title: str
    handoff: dict
    community_or_source: Optional[str] = None
    url: Optional[str] = None
    audience_type: Optional[str] = None
    pain_signal: Optional[str] = None
    why_veklom_fits: Optional[str] = None
    suggested_reply_or_post: Optional[str] = None
    cta: Optional[str] = None
    archive_record_id: Optional[str] = None


class CommercialArtifactUpdateRequest(BaseModel):
    founder_review_status: Optional[str] = None
    outcome: Optional[str] = None
    archive_record_id: Optional[str] = None


def _parse_datetime_param(value: Optional[str], field: str) -> Optional[datetime]:
    """Parse optional ISO8601 datetime query string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (AttributeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid ISO datetime for {field}") from exc


def _status_target_hash(channel: str, target: str) -> str:
    return hashlib.sha256(f"{channel}:{target}".encode("utf-8")).hexdigest()


def _mask_status_target(channel: str, target: str) -> str:
    if channel == "email":
        name, _, domain = target.partition("@")
        return f"{name[:2]}***@{domain}" if domain else "email subscriber"
    parsed = urlparse(target)
    path = parsed.path.rstrip("/")
    tail = path.split("/")[-1] if path else ""
    masked_tail = f"{tail[:4]}..." if tail else "endpoint"
    return f"{parsed.scheme}://{parsed.netloc}/.../{masked_tail}"


def _is_public_webhook_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower()
    if not host or host in {"localhost", "example.com", "example.org", "example.net"}:
        return False
    if host.endswith(".local"):
        return False
    try:
        ip = ipaddress.ip_address(host)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )
    except ValueError:
        return "." in host


def _validate_status_target(channel: str, target: str) -> str:
    channel = (channel or "").strip().lower()
    target = (target or "").strip()
    if channel not in {"email", "webhook", "slack"}:
        raise HTTPException(status_code=400, detail="Channel must be email, webhook, or slack")

    if len(target) > 2048:
        raise HTTPException(status_code=400, detail="Subscription target is too long")

    if channel == "email":
        if not target or "@" not in target or "." not in target.rsplit("@", 1)[-1]:
            raise HTTPException(status_code=400, detail="A valid email address is required")
        return target.lower()

    parsed = urlparse(target)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Webhook subscriptions require a public HTTPS URL")
    hostname = parsed.hostname or ""
    if not _is_public_webhook_host(hostname):
        raise HTTPException(status_code=400, detail="Webhook host must be public and routable")
    if channel == "slack" and not (hostname == "hooks.slack.com" and parsed.path.startswith("/services/")):
        raise HTTPException(status_code=400, detail="Slack subscriptions require a hooks.slack.com/services webhook")
    return target


def _email_transport_configured() -> bool:
    resend_ready = bool(settings.resend_api_key and settings.mail_from)
    smtp_ready = bool(settings.smtp_host and settings.mail_from)
    return resend_ready or smtp_ready


async def _send_status_email_confirmation(email: str) -> None:
    if not _email_transport_configured():
        raise HTTPException(status_code=503, detail="Email delivery is not configured")
    await send_email(
        to_email=email,
        subject="Veklom status updates enabled",
        text_body=(
            "You are subscribed to Veklom status updates.\n\n"
            "Public JSON: https://api.veklom.com/status/data\n"
            "RSS: https://api.veklom.com/status/rss.xml\n"
        ),
        html_body=(
            "<p>You are subscribed to <strong>Veklom status updates</strong>.</p>"
            '<p>Public JSON: <a href="https://api.veklom.com/status/data">status/data</a><br />'
            'RSS: <a href="https://api.veklom.com/status/rss.xml">status/rss.xml</a></p>'
        ),
    )


async def _send_slack_confirmation(url: str) -> None:
    payload = {
        "text": "Veklom status updates enabled.",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Veklom status updates enabled.*\nThis Slack channel will receive Veklom incident and maintenance notices.",
                },
            }
        ],
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(url, json=payload)
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail="Slack webhook rejected the confirmation message")


def _status_items_for_feed(payload: dict) -> list[dict]:
    items = []
    for incident in payload.get("incidents", []):
        items.append(
            {
                "id": incident.get("id"),
                "title": incident.get("title") or "Veklom incident",
                "description": incident.get("description") or "",
                "category": f"{incident.get('severity', 'incident')} / {incident.get('status', 'open')}",
                "created_at": incident.get("created_at") or payload.get("timestamp"),
            }
        )
    for item in payload.get("maintenance", []):
        items.append(
            {
                "id": item.get("id"),
                "title": item.get("title") or "Scheduled maintenance",
                "description": item.get("description") or "",
                "category": f"maintenance / {item.get('severity', 'info')}",
                "created_at": item.get("created_at") or payload.get("timestamp"),
            }
        )
    if not items:
        items.append(
            {
                "id": "veklom-operational",
                "title": "All Veklom services operational",
                "description": "No active incidents or scheduled maintenance are currently reported.",
                "category": "operational",
                "created_at": payload.get("timestamp") or datetime.utcnow().isoformat(),
            }
        )
    return items


def _render_status_rss(payload: dict) -> str:
    items_xml = []
    for item in _status_items_for_feed(payload):
        title = html.escape(str(item["title"]))
        description = html.escape(str(item["description"]))
        category = html.escape(str(item["category"]))
        link = f"https://veklom.com/status#{html.escape(str(item['id']))}"
        guid = html.escape(str(item["id"]))
        pub_date = html.escape(str(item["created_at"]))
        items_xml.append(
            f"<item><title>{title}</title><link>{link}</link><guid>{guid}</guid>"
            f"<category>{category}</category><pubDate>{pub_date}</pubDate>"
            f"<description>{description}</description></item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        "<title>Veklom Status</title>"
        "<link>https://veklom.com/status</link>"
        "<description>Veklom public incident and maintenance feed.</description>"
        f"<lastBuildDate>{html.escape(str(payload.get('timestamp') or datetime.utcnow().isoformat()))}</lastBuildDate>"
        + "".join(items_xml)
        + "</channel></rss>"
    )


@router.get("/analytics/summary")
async def workspace_financial_overview(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return workspace_financial_summary(
        db=db,
        workspace_id=current_user.workspace_id,
        start_date=_parse_datetime_param(start_date, "start_date"),
        end_date=_parse_datetime_param(end_date, "end_date"),
    )


@router.get("/overview")
async def workspace_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return fetch_overview(db, workspace_id=current_user.workspace_id)


@router.get("/playground/profile")
async def workspace_playground_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ensure_workspace_profile_defaults(workspace)
    db.commit()
    db.refresh(workspace)
    return resolve_workspace_profile(workspace)


@router.patch("/profile")
async def workspace_profile_update(
    payload: WorkspaceProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if payload.industry is not None:
        normalized = normalize_industry(payload.industry)
        workspace.industry = normalized
        workspace.playground_profile = normalized
        workspace.risk_tier = None
        workspace.default_policy_pack = None
        workspace.default_demo_scenarios = None
        workspace.default_evidence_requirements = None
        workspace.default_blocking_rules = None
    ensure_workspace_profile_defaults(workspace)
    db.commit()
    db.refresh(workspace)
    return resolve_workspace_profile(workspace)


@router.post("/playground/handoff", status_code=201)
async def create_playground_handoff(
    payload: PlaygroundHandoffRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        handoff = build_static_gpc_handoff(
            workspace,
            scenario_id=payload.scenario_id,
            scenario_title=payload.scenario_title,
            user_input=payload.user_input,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="Unknown playground scenario") from exc
    db.add(
        ProductUsageEvent(
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            event_type="feature_use",
            surface="playground",
            route="/playground",
            feature="gpc_handoff_prepared",
            metadata_json=dumps_payload(
                {
                    "scenario_id": handoff["scenario_id"],
                    "industry": handoff["industry"],
                    "playground_profile": handoff["playground_profile"],
                    "claim_level": handoff["claim_level"],
                    "risk_tier": handoff["risk_tier"],
                }
            ),
        )
    )
    db.commit()
    return handoff


@router.post("/commercial/community-awareness-run", status_code=201)
async def create_community_awareness_artifact(
    payload: CommercialArtifactCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    handoff = payload.handoff or {}
    industry = str(handoff.get("industry") or "generic")
    regulated = industry in {
        "banking_fintech",
        "healthcare_hospital",
        "insurance",
        "legal_compliance",
        "government_public_sector",
    }
    artifact_payload = {
        "run_type": "Community Awareness Run",
        "community/source": payload.community_or_source,
        "URL": payload.url,
        "audience type": payload.audience_type,
        "pain signal": payload.pain_signal,
        "why Veklom fits": payload.why_veklom_fits,
        "suggested reply/post": payload.suggested_reply_or_post,
        "CTA": payload.cta,
        "spam risk": "medium",
        "regulated claim risk": "high" if regulated else "medium",
        "competitor claim risk": "medium",
        "founderReviewStatus": "pending_founder_review",
        "archiveRecordId": payload.archive_record_id,
        "outcome": "draft",
        "rules": {
            "auto_posting": False,
            "spam_allowed": False,
            "unsupported_competitor_attacks_allowed": False,
            "regulated_claims_require_founder_approval": True,
            "fake_urgency_allowed": False,
        },
    }
    artifact = CommercialArtifact(
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        artifact_type="community_awareness_run",
        title=payload.title.strip()[:200] or "Community Awareness Run",
        source_type="vertical_playground",
        source_scenario_id=str(handoff.get("scenario_id") or "")[:160] or None,
        handoff_json=dumps_payload(handoff),
        artifact_json=dumps_payload(artifact_payload),
        founder_review_status="pending_founder_review",
        spam_risk="medium",
        regulated_claim_risk="high" if regulated else "medium",
        competitor_claim_risk="medium",
        archive_record_id=(payload.archive_record_id or "")[:200] or None,
        outcome="draft",
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return {
        "id": artifact.id,
        "artifact_type": artifact.artifact_type,
        "title": artifact.title,
        "founderReviewStatus": artifact.founder_review_status,
        "archiveRecordId": artifact.archive_record_id,
        "outcome": artifact.outcome,
        "artifact": json.loads(artifact.artifact_json),
    }


@router.patch("/commercial/artifacts/{artifact_id}")
async def update_commercial_artifact(
    artifact_id: str,
    payload: CommercialArtifactUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    artifact = (
        db.query(CommercialArtifact)
        .filter(
            CommercialArtifact.id == artifact_id,
            CommercialArtifact.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if not artifact:
        raise HTTPException(status_code=404, detail="Commercial artifact not found")
    artifact_payload = json.loads(artifact.artifact_json)
    if payload.founder_review_status is not None:
        artifact.founder_review_status = payload.founder_review_status.strip()[:80] or artifact.founder_review_status
        artifact_payload["founderReviewStatus"] = artifact.founder_review_status
    if payload.outcome is not None:
        artifact.outcome = payload.outcome.strip()[:120] or artifact.outcome
        artifact_payload["outcome"] = artifact.outcome
    if payload.archive_record_id is not None:
        artifact.archive_record_id = payload.archive_record_id.strip()[:200] or None
        artifact_payload["archiveRecordId"] = artifact.archive_record_id
    artifact.artifact_json = dumps_payload(artifact_payload)
    db.commit()
    db.refresh(artifact)
    return {
        "id": artifact.id,
        "founderReviewStatus": artifact.founder_review_status,
        "archiveRecordId": artifact.archive_record_id,
        "outcome": artifact.outcome,
    }


@router.get("/commercial/scorecard")
async def workspace_commercial_scorecard(
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    usage_query = db.query(ProductUsageEvent).filter(
        ProductUsageEvent.workspace_id == current_user.workspace_id,
        ProductUsageEvent.created_at >= start,
        ProductUsageEvent.created_at <= now,
    )
    artifact_query = db.query(CommercialArtifact).filter(
        CommercialArtifact.workspace_id == current_user.workspace_id,
        CommercialArtifact.created_at >= start,
        CommercialArtifact.created_at <= now,
    )
    return {
        "generated_at": now.isoformat(),
        "window_days": days,
        "counters": {
            "vertical_demos_generated": usage_query.filter(
                ProductUsageEvent.event_type == "feature_use",
                ProductUsageEvent.feature == "vertical_demo_generated",
            ).count(),
            "gpc_handoffs_prepared": usage_query.filter(
                ProductUsageEvent.event_type == "feature_use",
                ProductUsageEvent.feature == "gpc_handoff_prepared",
            ).count(),
            "founder_reviewed_vertical_artifacts": artifact_query.filter(
                CommercialArtifact.founder_review_status != "pending_founder_review"
            ).count(),
            "evaluation_conversations_influenced_by_vertical_demo": usage_query.filter(
                ProductUsageEvent.event_type == "feature_use",
                ProductUsageEvent.feature == "evaluation_conversation_influenced_by_vertical_demo",
            ).count(),
        },
        "targets_14d": {
            "qualified_evaluation_conversations": 3,
            "serious_byos_private_backend_access_requests": 1,
            "credible_vendor_tool_conversations": 1,
            "approved_package_concepts": 3,
            "founder_approved_public_community_interactions": 10,
        },
        "over_the_bar": {
            "signed_evaluation_agreements": 1,
            "paid_pilot_or_operating_reserve_funded": 1,
            "technical_procurement_processes_started": 1,
            "credible_vendor_tool_committed": 1,
        },
    }


@router.get("/observability")
async def workspace_observability(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    model: Optional[str] = None,
    status: Optional[str] = None,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    payload = fetch_observability_payload(
        db,
        workspace_id=current_user.workspace_id,
        start_date=start_date,
        end_date=end_date,
        model=model,
        status=status,
    )
    payload["rows"] = payload["rows"][offset : offset + limit]
    payload["limit"] = limit
    payload["offset"] = offset
    return payload


@router.get("/analytics/requests")
async def workspace_analytics_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    request_path: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=0, le=500),
    offset: int = Query(0, ge=0),
    include_rows: bool = Query(False),
):
    parsed_end = _parse_datetime_param(end_date, "end_date") or datetime.utcnow()
    parsed_start = _parse_datetime_param(start_date, "start_date") or (parsed_end - timedelta(days=30))
    return fetch_workspace_request_metrics(
        db=db,
        workspace_id=current_user.workspace_id,
        start_date=parsed_start,
        end_date=parsed_end,
        model=model,
        request_path=request_path,
        status=status,
        limit=limit,
        offset=offset,
        include_rows=include_rows,
    )


@router.get("/api-keys")
async def workspace_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "keys": fetch_api_key_rows(db, workspace_id=current_user.workspace_id),
    }


@router.get("/models")
async def workspace_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "models": fetch_model_rows(db, workspace_id=current_user.workspace_id),
    }


@router.patch("/models/{model_slug}")
async def workspace_model_toggle(
    model_slug: str,
    payload: ModelToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = set_model_enabled(db, current_user.workspace_id, model_slug, payload.enabled)
    return {
        "model_slug": row.model_slug,
        "enabled": row.enabled,
        "bedrock_model_id": row.bedrock_model_id,
    }


@router.get("/cost-budget")
async def workspace_cost_budget(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return fetch_cost_budget_payload(db, workspace_id=current_user.workspace_id)


@router.post("/budget")
async def workspace_budget_update(
    payload: BudgetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from apps.api.routers.budget import create_budget, BudgetRequest

    request = BudgetRequest(
        budget_type=payload.budget_type,
        amount=payload.amount,
        period_start=payload.period_start,
        period_end=payload.period_end,
        alert_thresholds=payload.alert_thresholds,
    )
    return await create_budget(request=request, workspace_id=current_user.workspace_id, db=db)


@router.get("/budget")
async def workspace_budget_get(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from apps.api.routers.budget import get_budget_status

    return await get_budget_status(
        workspace_id=current_user.workspace_id,
        budget_type="monthly",
        db=db,
        limit=100,
    )


@router.get("/cost-budget.csv")
async def workspace_cost_budget_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = fetch_cost_budget_payload(db, workspace_id=current_user.workspace_id)
    lines = ["date,cost_usd"]
    for row in payload["monthly_spend_chart"]:
        lines.append(f"{row['date']},{row['cost_usd']}")
    csv = "\n".join(lines) + "\n"
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="veklom-costs.csv"'})


# ── Members + invites ──────────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str
    role: str = "user"


class InviteAcceptRequest(BaseModel):
    token: str


def _is_admin(user: User) -> bool:
    return user.role in (UserRole.OWNER, UserRole.ADMIN) or user.is_superuser


@router.get("/members")
async def list_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    members = (
        db.query(User)
        .filter(User.workspace_id == current_user.workspace_id)
        .order_by(User.created_at.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value if hasattr(u.role, "value") else u.role,
                "status": u.status.value if hasattr(u.status, "value") else u.status,
                "is_active": u.is_active,
                "mfa_enabled": u.mfa_enabled,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in members
        ]
    }


@router.get("/members/invites")
async def list_invites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin access required")
    rows = (
        db.query(WorkspaceInvite)
        .filter(WorkspaceInvite.workspace_id == current_user.workspace_id)
        .order_by(WorkspaceInvite.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": i.id,
                "email": i.email,
                "role": i.role,
                "status": i.status.value if hasattr(i.status, "value") else i.status,
                "expires_at": i.expires_at.isoformat() if i.expires_at else None,
                "created_at": i.created_at.isoformat(),
            }
            for i in rows
        ]
    }


@router.post("/members/invite", status_code=201)
async def invite_member(
    payload: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(403, "Only admins can invite team members")

    email = (payload.email or "").strip().lower()
    if not email or "@" not in email or len(email) > 200:
        raise HTTPException(400, "Invalid email address")

    role = payload.role.lower()
    valid_roles = {r.value for r in UserRole}
    if role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of {sorted(valid_roles)}")
    if role == UserRole.OWNER.value and not current_user.is_superuser:
        raise HTTPException(403, "Only superusers can invite owners")

    existing_user = (
        db.query(User)
        .filter(User.email == email, User.workspace_id == current_user.workspace_id)
        .first()
    )
    if existing_user:
        raise HTTPException(409, "User with this email is already a workspace member")

    pending = (
        db.query(WorkspaceInvite)
        .filter(
            WorkspaceInvite.workspace_id == current_user.workspace_id,
            WorkspaceInvite.email == email,
            WorkspaceInvite.status == InviteStatus.PENDING,
        )
        .first()
    )
    if pending:
        raise HTTPException(409, "Pending invite already exists for this email")

    invite = WorkspaceInvite(
        workspace_id=current_user.workspace_id,
        email=email,
        role=role,
        invited_by=current_user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {
        "id": invite.id,
        "email": invite.email,
        "role": invite.role,
        "status": invite.status.value,
        "token": invite.token,  # one-shot — caller is responsible for delivering
        "expires_at": invite.expires_at.isoformat(),
        "created_at": invite.created_at.isoformat(),
    }


@router.post("/members/invites/{invite_id}/revoke")
async def revoke_invite(
    invite_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin access required")
    invite = (
        db.query(WorkspaceInvite)
        .filter(
            WorkspaceInvite.id == invite_id,
            WorkspaceInvite.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if not invite:
        raise HTTPException(404, "Invite not found")
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(409, f"Cannot revoke invite with status {invite.status}")
    invite.status = InviteStatus.REVOKED
    invite.revoked_at = datetime.utcnow()
    db.commit()
    return {"id": invite.id, "status": invite.status.value}


@public_router.get("/status/data")
async def public_status_data(db: Session = Depends(get_db)):
    return fetch_public_status_payload(db)


@public_router.get("/status/json")
async def public_status_json(db: Session = Depends(get_db)):
    return fetch_public_status_payload(db)


@public_router.get("/status/rss.xml", include_in_schema=False)
async def public_status_rss(db: Session = Depends(get_db)):
    payload = fetch_public_status_payload(db)
    return Response(content=_render_status_rss(payload), media_type="application/rss+xml")


@public_router.post("/status/subscribe", status_code=201)
async def public_status_subscribe(
    payload: StatusSubscribeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    channel = (payload.channel or "").strip().lower()
    target = _validate_status_target(channel, payload.target)
    target_hash = _status_target_hash(channel, target)
    existing = db.query(StatusSubscription).filter(StatusSubscription.target_hash == target_hash).first()

    confirmation_sent = False
    verification_status = "pending"
    last_delivery_status = None

    if channel == "email":
        await _send_status_email_confirmation(target)
        confirmation_sent = True
        verification_status = "verified"
        last_delivery_status = "confirmation_sent"
    elif channel == "slack":
        await _send_slack_confirmation(target)
        confirmation_sent = True
        verification_status = "verified"
        last_delivery_status = "confirmation_sent"
    else:
        verification_status = "accepted"
        last_delivery_status = "not_tested"

    if existing:
        existing.status = "active"
        existing.verification_status = verification_status
        existing.last_delivery_status = last_delivery_status
        existing.last_delivery_at = datetime.utcnow() if confirmation_sent else existing.last_delivery_at
        existing.updated_at = datetime.utcnow()
        row = existing
    else:
        row = StatusSubscription(
            channel=channel,
            target_hash=target_hash,
            target_encrypted=encrypt_field(target),
            target_label=_mask_status_target(channel, target),
            status="active",
            verification_status=verification_status,
            last_delivery_status=last_delivery_status,
            last_delivery_at=datetime.utcnow() if confirmation_sent else None,
            source_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "channel": row.channel,
        "status": row.status,
        "verification_status": row.verification_status,
        "target": row.target_label,
        "confirmation_sent": confirmation_sent,
        "json_url": "https://api.veklom.com/status/data",
        "rss_url": "https://api.veklom.com/status/rss.xml",
    }


@public_router.get("/status/page", include_in_schema=False)
async def public_status_page():
    status_path = Path(__file__).resolve().parents[3] / "landing" / "status.html"
    return FileResponse(status_path, media_type="text/html")
