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
from core.operations.operator_watch import evaluate_operator_watch
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
    "builder-scout": {
        "name": "BUILDER SCOUT",
        "mission": "Find public tool pain signals from compliant sources and convert them into clean-room marketplace opportunities.",
        "owned_surfaces": ["public issue metadata", "package registries", "developer forums", "docs/changelog watchlists"],
        "required_config": [],
        "hard_kpis": ["qualified_pain_signals", "clean_room_opportunities", "license_clearance_rate", "duplicate_rejection_rate"],
    },
    "builder-forge": {
        "name": "BUILDER FORGE",
        "mission": "Turn approved opportunities into original Veklom-native MCP, SDK, CLI, CI/CD, and agent tool packages.",
        "owned_surfaces": ["marketplace build specs", "tool package workspaces", "integration test harnesses"],
        "required_config": [],
        "hard_kpis": ["tools_built", "test_pass_rate", "time_to_package", "install_success_rate"],
    },
    "builder-arbiter": {
        "name": "BUILDER ARBITER",
        "mission": "Enforce provenance, license safety, no-copy rules, marketplace quality gates, and release readiness.",
        "owned_surfaces": ["source lineage records", "license review", "release gates", "marketplace approval queue"],
        "required_config": [],
        "hard_kpis": ["blocked_unsafe_builds", "provenance_completeness", "release_gate_pass_rate", "audit_replay_success"],
    },
    "sentinel": {
        "name": "SENTINEL",
        "mission": "Run end-to-end uptime, route, API, and critical production flow verification across app surfaces.",
        "owned_surfaces": ["route map", "API health checks", "auth flows", "critical user journeys"],
        "required_config": ["BACKEND_URL"],
        "hard_kpis": ["core_route_pass_rate", "auth_flow_success", "broken_flow_detection_time", "silent_breakage_count"],
    },
    "mirror": {
        "name": "MIRROR",
        "mission": "Validate that frontend-visible data matches backend truth and catch fake, stale, null, or mismatched display state.",
        "owned_surfaces": ["command center widgets", "overview telemetry", "workspace dashboard", "API response truth sets"],
        "required_config": ["DATABASE_URL"],
        "hard_kpis": ["truth_match_rate", "stale_widget_count", "display_confidence", "null_misrepresentation_count"],
    },
    "polish": {
        "name": "POLISH",
        "mission": "Enforce premium visual quality, command-surface hierarchy, empty-state quality, and non-cheap interaction standards.",
        "owned_surfaces": ["command center", "overview", "first-run surfaces", "premium product screens"],
        "required_config": [],
        "hard_kpis": ["premium_surface_score", "layout_defect_count", "cheap_pattern_count", "usability_confidence"],
    },
    "glide": {
        "name": "GLIDE",
        "mission": "Verify navigation, transitions, CTAs, controls, forms, and command-surface movement feel seamless and consistent.",
        "owned_surfaces": ["navigation map", "route transitions", "CTA paths", "interactive controls"],
        "required_config": ["BACKEND_URL"],
        "hard_kpis": ["dead_route_count", "click_friction", "control_success_rate", "transition_defect_count"],
    },
    "pulse": {
        "name": "PULSE",
        "mission": "Ensure live telemetry is actually live, fresh, evidenced, and not decorative.",
        "owned_surfaces": ["live widgets", "telemetry timestamps", "health feeds", "realtime counters"],
        "required_config": ["DATABASE_URL"],
        "hard_kpis": ["freshness_score", "stale_feed_count", "telemetry_truth_rate", "decorative_panel_count"],
    },
    "sheriff": {
        "name": "SHERIFF",
        "mission": "Detect regressions after deploys, config changes, permission changes, and workflow updates.",
        "owned_surfaces": ["build outputs", "smoke tests", "permission diffs", "deployment workflows"],
        "required_config": ["BACKEND_URL"],
        "hard_kpis": ["escaped_regressions", "post_deploy_confidence", "rollback_detection_time", "workflow_drift_count"],
    },
    "welcome": {
        "name": "WELCOME",
        "mission": "Protect first-run, landing-to-app, signup, onboarding, and empty-state experience for new users.",
        "owned_surfaces": ["landing-to-app path", "signup flow", "new workspace state", "onboarding copy"],
        "required_config": [],
        "hard_kpis": ["time_to_value", "first_run_confusion_count", "onboarding_completion", "first_impression_score"],
    },
}


COMMITTEE_REGISTRY: dict[str, dict[str, Any]] = {
    "marketplace-operations": {
        "name": "Marketplace Operations Committee",
        "workers": ["herald", "harvest", "bouncer", "gauge", "arbiter"],
        "authority": "Operate marketplace supply, demand, trust, and health loops.",
    },
    "governance-evidence": {
        "name": "Governance & Evidence Committee",
        "workers": ["ledger", "oracle", "builder-arbiter", "sheriff"],
        "authority": "Own policy posture, evidence integrity, release gates, and production safety.",
    },
    "growth-intelligence": {
        "name": "Growth & Intelligence Committee",
        "workers": ["signal", "scout", "mint", "welcome"],
        "authority": "Convert market signal, pricing, positioning, and onboarding into revenue leverage.",
    },
    "builder-systems": {
        "name": "Builder Systems Committee",
        "workers": ["builder-scout", "builder-forge", "builder-arbiter"],
        "authority": "Convert clean public pain signals into original Veklom-native tool assets.",
    },
    "experience-assurance": {
        "name": "Experience Assurance Committee",
        "workers": ["sentinel", "mirror", "polish", "glide", "pulse", "sheriff", "welcome"],
        "authority": "Keep the product live, truthful, premium, navigable, and regression-resistant.",
    },
}


MINIMUM_LIVE_SET = ["gauge", "ledger", "sentinel", "mirror", "pulse", "sheriff", "polish"]


WORKER_OPERATING_SPEC: dict[str, dict[str, Any]] = {
    "herald": {
        "primary_pillar": "Growth / Sales",
        "trigger": "New lead, vendor event, messaging failure, or campaign launch.",
        "inputs": ["contact records", "delivery events", "suppression status", "lifecycle state"],
        "outputs": ["outbound messages", "funnel updates", "suppression actions", "delivery reports"],
        "success_metric": "Delivery rate, reply rate, and low suppression drift.",
        "escalation": "Escalate to Growth lead if deliverability drops or suppression spikes.",
        "rollout_stage": "ready",
    },
    "harvest": {
        "primary_pillar": "Sales / Operations",
        "trigger": "New sourcing cycle, low supply depth, or new category push.",
        "inputs": ["vendor records", "category targets", "qualification rules", "external signals"],
        "outputs": ["qualified account lists", "sourcing recommendations", "pipeline updates"],
        "success_metric": "Qualified vendors added, acceptance rate, and fill rate.",
        "escalation": "Escalate to scout and arbiter if category quality is weak.",
        "rollout_stage": "ready",
    },
    "bouncer": {
        "primary_pillar": "Compliance / Risk",
        "trigger": "New vendor intake, risky action, abuse signal, or trust anomaly.",
        "inputs": ["vendor submissions", "trust signals", "abuse heuristics", "policy rules"],
        "outputs": ["block decisions", "allow decisions", "trust flags", "review queues"],
        "success_metric": "Low fraud leakage and low false-allow rate.",
        "escalation": "Escalate to oracle and arbiter on high-risk or regulated cases.",
        "rollout_stage": "ready",
    },
    "gauge": {
        "primary_pillar": "Operations / Finance",
        "trigger": "Scheduled telemetry check, metric threshold breach, or deploy completion.",
        "inputs": ["telemetry", "wallet data", "route status", "usage data", "conversion events"],
        "outputs": ["health summaries", "anomaly reports", "KPI snapshots"],
        "success_metric": "Healthy routes, accurate dashboards, and fast anomaly detection.",
        "escalation": "Escalate to sentinel and ledger if telemetry mismatches evidence.",
        "rollout_stage": "minimum_live",
    },
    "ledger": {
        "primary_pillar": "Finance / Compliance",
        "trigger": "Compliance review, customer request, audit export, or incident follow-up.",
        "inputs": ["events", "runs", "logs", "privacy actions", "approvals", "trace data"],
        "outputs": ["audit packs", "proof bundles", "explainability reports"],
        "success_metric": "Complete evidence trail, export accuracy, and fast retrieval.",
        "escalation": "Escalate to oracle if evidence is incomplete or policy-sensitive.",
        "rollout_stage": "minimum_live",
    },
    "signal": {
        "primary_pillar": "Growth / Knowledge",
        "trigger": "New release, launch, adoption dip, or ecosystem monitoring cycle.",
        "inputs": ["product updates", "community channels", "feedback", "engagement signals"],
        "outputs": ["distribution plans", "community summaries", "ecosystem insights"],
        "success_metric": "Engagement lift, signal coverage, and feedback quality.",
        "escalation": "Escalate to scout if competitor movement changes positioning.",
        "rollout_stage": "ready",
    },
    "oracle": {
        "primary_pillar": "Governance / Compliance",
        "trigger": "New policy question, risky vendor/tool, or regulated customer path.",
        "inputs": ["policies", "laws", "procurement needs", "privacy requirements", "trust status"],
        "outputs": ["policy rulings", "procurement guidance", "compliance decisions"],
        "success_metric": "Low policy drift, fast risk decisions, and clear rulings.",
        "escalation": "Escalate to founder governance on legal ambiguity or high-risk actions.",
        "rollout_stage": "ready",
    },
    "mint": {
        "primary_pillar": "Finance / Growth",
        "trigger": "Pricing review, wallet anomaly, packaging change, or monetization experiment.",
        "inputs": ["revenue data", "wallet balances", "packaging configs", "usage data"],
        "outputs": ["pricing updates", "monetization models", "wallet policy actions"],
        "success_metric": "Margin quality, conversion lift, and reduced wallet drift.",
        "escalation": "Escalate to gauge and founder if monetization hurts trust or usage.",
        "rollout_stage": "ready",
    },
    "scout": {
        "primary_pillar": "Knowledge / Growth",
        "trigger": "Scheduled market watch, launch detection, or partnership signal.",
        "inputs": ["public competitor signals", "partner data", "category trends", "market events"],
        "outputs": ["threat briefs", "opportunity maps", "movement alerts"],
        "success_metric": "Fast threat detection and useful opportunity identification.",
        "escalation": "Escalate to signal, harvest, and builder-scout on actionable gaps.",
        "rollout_stage": "ready",
    },
    "arbiter": {
        "primary_pillar": "Operations / Compliance",
        "trigger": "Vendor dispute, trust downgrade, review event, or install anomaly.",
        "inputs": ["vendor history", "dispute records", "install events", "trust signals"],
        "outputs": ["trust decisions", "dispute outcomes", "integrity rulings"],
        "success_metric": "Low dispute backlog, trust accuracy, and review integrity.",
        "escalation": "Escalate to bouncer and oracle if abuse or regulation is involved.",
        "rollout_stage": "ready",
    },
    "builder-scout": {
        "primary_pillar": "Knowledge / Engineering",
        "trigger": "Builder discovery cycle, missing integration, or broken public tool signal.",
        "inputs": ["public issues", "docs", "changelogs", "registries", "support threads"],
        "outputs": ["opportunity dossiers", "pain clusters", "source lineage records"],
        "success_metric": "High-quality legal opportunities identified.",
        "escalation": "Escalate to builder-arbiter before spec approval.",
        "rollout_stage": "staged",
    },
    "builder-forge": {
        "primary_pillar": "Engineering / Product",
        "trigger": "Approved builder spec, release sprint, or integration opportunity.",
        "inputs": ["approved specs", "contracts", "tests", "policy constraints"],
        "outputs": ["original tool packages", "docs", "tests", "build artifacts"],
        "success_metric": "Build quality, test pass rate, and time to usable asset.",
        "escalation": "Escalate to builder-arbiter if provenance or quality gates fail.",
        "rollout_stage": "staged",
    },
    "builder-arbiter": {
        "primary_pillar": "Governance / Compliance",
        "trigger": "New builder output, release request, or provenance review.",
        "inputs": ["source lineage", "licenses", "tests", "docs", "quality reports"],
        "outputs": ["release approval", "release denial", "compliance gate result", "quality ruling"],
        "success_metric": "Zero illegal copying, strong release hygiene, and trusted outputs.",
        "escalation": "Escalate to founder governance on ambiguous legal or reputational risk.",
        "rollout_stage": "staged",
    },
    "sentinel": {
        "primary_pillar": "Operations / Engineering",
        "trigger": "Deploy complete, cron interval, incident report, or health anomaly.",
        "inputs": ["route map", "API endpoints", "auth flows", "critical user journeys"],
        "outputs": ["synthetic check results", "incident alerts", "broken-flow reports"],
        "success_metric": "Core routes pass, auth works, and no silent breakage.",
        "escalation": "Escalate to sheriff and gauge when a production path breaks.",
        "rollout_stage": "minimum_live",
    },
    "mirror": {
        "primary_pillar": "Product / Operations",
        "trigger": "Dashboard render, page load audit, telemetry refresh, or incident report.",
        "inputs": ["UI payloads", "API responses", "DB-backed truth sets", "timestamps"],
        "outputs": ["truth mismatch reports", "stale-data alerts", "display confidence score"],
        "success_metric": "No fake, stale, or null misrepresentation on key surfaces.",
        "escalation": "Escalate to ledger and pulse if displayed data cannot be evidenced.",
        "rollout_stage": "minimum_live",
    },
    "polish": {
        "primary_pillar": "Product",
        "trigger": "UI change merged, design review cycle, or user complaint.",
        "inputs": ["screens", "layouts", "spacing", "typography", "empty states", "hierarchy"],
        "outputs": ["UX quality reviews", "polish issues", "premium-surface recommendations"],
        "success_metric": "Reduced cheap/template feel and higher usability confidence.",
        "escalation": "Escalate to product owner if command surfaces degrade trust.",
        "rollout_stage": "minimum_live",
    },
    "glide": {
        "primary_pillar": "Product / Engineering",
        "trigger": "Route update, component release, UX complaint, or weekly audit.",
        "inputs": ["click paths", "nav map", "transition logic", "interactive elements"],
        "outputs": ["broken-nav reports", "interaction QA", "friction maps"],
        "success_metric": "Low click friction, no dead routes, and smooth control transitions.",
        "escalation": "Escalate to sentinel if broken navigation affects critical journeys.",
        "rollout_stage": "ready",
    },
    "pulse": {
        "primary_pillar": "Operations / Engineering",
        "trigger": "Real-time refresh cycle, dashboard check, or telemetry incident.",
        "inputs": ["WebSocket streams", "polling outputs", "timestamps", "counters", "health feeds"],
        "outputs": ["live-status verification", "stale-widget alerts", "freshness scores"],
        "success_metric": "Accurate live widgets, fresh timestamps, and no fake real-time panels.",
        "escalation": "Escalate to gauge and mirror if telemetry and UI disagree.",
        "rollout_stage": "minimum_live",
    },
    "sheriff": {
        "primary_pillar": "Engineering / Governance",
        "trigger": "Post-merge, post-deploy, permission change, or workflow patch.",
        "inputs": ["build outputs", "smoke tests", "permission diffs", "route checks", "logs"],
        "outputs": ["regression reports", "rollback recommendations", "defect queues"],
        "success_metric": "Low escaped regressions and fast post-deploy confidence.",
        "escalation": "Escalate to founder or release owner if production safety is at risk.",
        "rollout_stage": "minimum_live",
    },
    "welcome": {
        "primary_pillar": "Product / Growth",
        "trigger": "New signup flow, landing-to-app path audit, or onboarding update.",
        "inputs": ["landing pages", "signup flow", "empty-state copy", "initial workspace state"],
        "outputs": ["onboarding issues", "first-run improvement list", "friction summaries"],
        "success_metric": "Faster time-to-value, lower confusion, and stronger first impression.",
        "escalation": "Escalate to polish and glide if onboarding makes the app feel broken or cheap.",
        "rollout_stage": "ready",
    },
}


def _config_present(key: str) -> bool:
    if key == "BACKEND_URL":
        return bool(os.getenv(key) or "https://api.veklom.com")
    if key == "RESEND_API_KEY":
        return bool(settings.resend_api_key or os.getenv(key))
    if key == "RESEND_WEBHOOK_SECRET":
        return bool(settings.resend_webhook_secret or os.getenv(key))
    if key == "STRIPE_SECRET_KEY":
        return bool(settings.stripe_secret_key or os.getenv(key))
    if key == "DATABASE_URL":
        return bool(settings.database_url or os.getenv(key))
    return bool(os.getenv(key))


def _worker_committees(worker_id: str) -> list[str]:
    return [
        committee_id
        for committee_id, committee in COMMITTEE_REGISTRY.items()
        if worker_id in committee["workers"]
    ]


def _worker_payload(worker_id: str, worker: dict[str, Any]) -> dict[str, Any]:
    spec = WORKER_OPERATING_SPEC.get(worker_id, {})
    readiness = {
        key: _config_present(key)
        for key in worker.get("required_config", [])
    }
    missing = [key for key, present in readiness.items() if not present]
    return {
        "id": worker_id,
        "name": worker["name"],
        "mission": worker["mission"],
        "primary_pillar": spec.get("primary_pillar", "Operations"),
        "committees": _worker_committees(worker_id),
        "trigger": spec.get("trigger", "Manual operator run or scheduled health cycle."),
        "inputs": spec.get("inputs", []),
        "outputs": spec.get("outputs", []),
        "success_metric": spec.get("success_metric", "Useful output with evidence and no policy violation."),
        "escalation": spec.get("escalation", "Escalate to founder governance if risk or uncertainty is material."),
        "rollout_stage": spec.get("rollout_stage", "ready"),
        "minimum_live": worker_id in MINIMUM_LIVE_SET,
        "owned_surfaces": worker["owned_surfaces"],
        "hard_kpis": worker["hard_kpis"],
        "readiness": readiness,
        "missing_config": missing,
        "customer_visible": False,
        "ships_to_buyer_package": False,
        "status": "ready" if not missing else "needs_config",
    }


def _committee_payload(committee_id: str, committee: dict[str, Any]) -> dict[str, Any]:
    workers = [
        _worker_payload(worker_id, WORKER_REGISTRY[worker_id])
        for worker_id in committee["workers"]
        if worker_id in WORKER_REGISTRY
    ]
    return {
        "id": committee_id,
        "name": committee["name"],
        "authority": committee["authority"],
        "workers": workers,
        "worker_ids": [worker["id"] for worker in workers],
        "ready_workers": sum(1 for worker in workers if worker["status"] == "ready"),
        "needs_config": [worker["id"] for worker in workers if worker["status"] != "ready"],
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
                "committees": _worker_committees(worker_id),
                "primary_pillar": WORKER_OPERATING_SPEC.get(worker_id, {}).get("primary_pillar"),
                "rollout_stage": WORKER_OPERATING_SPEC.get(worker_id, {}).get("rollout_stage"),
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
    minimum_live_workers = [worker for worker in workers if worker["minimum_live"]]
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
        "committee_count": len(COMMITTEE_REGISTRY),
        "minimum_live_count": len(minimum_live_workers),
        "minimum_live_ready": sum(1 for worker in minimum_live_workers if worker["status"] == "ready"),
        "needs_config": [worker["id"] for worker in workers if worker["status"] != "ready"],
        "recent_failure_count": len(recent_failures),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/digest")
async def operator_digest(
    principal: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    """Backend-owned operator digest.

    This is the non-Slack source for what the owner needs to know before the
    system becomes critical. It evaluates live telemetry without mutating state.
    """
    return evaluate_operator_watch(db, workspace_id=None, persist=False)


@router.post("/watch")
async def operator_watch(
    principal: OperatorPrincipal = Depends(require_internal_operator),
    db: Session = Depends(get_db),
):
    """Run the operator watch loop and persist actionable alerts."""
    return evaluate_operator_watch(db, workspace_id=None, persist=True)


@router.get("/workers")
async def list_workers(_: OperatorPrincipal = Depends(require_internal_operator)):
    return {
        "workers": [_worker_payload(worker_id, worker) for worker_id, worker in WORKER_REGISTRY.items()],
        "visibility": "veklom_internal_only",
    }


@router.get("/registry")
async def worker_registry(_: OperatorPrincipal = Depends(require_internal_operator)):
    workers = [_worker_payload(worker_id, worker) for worker_id, worker in WORKER_REGISTRY.items()]
    return {
        "version": "uacp_v3",
        "visibility": "veklom_internal_only",
        "customer_visible": False,
        "ships_to_buyer_package": False,
        "workers": workers,
        "committees": [
            _committee_payload(committee_id, committee)
            for committee_id, committee in COMMITTEE_REGISTRY.items()
        ],
        "minimum_live_set": [
            _worker_payload(worker_id, WORKER_REGISTRY[worker_id])
            for worker_id in MINIMUM_LIVE_SET
            if worker_id in WORKER_REGISTRY
        ],
        "promotion_logic": {
            "promote": "Consistently hits success metrics, produces useful outputs, and reduces founder intervention.",
            "demote": "Causes false positives, misses obvious failures, creates noise, or operates outside policy boundaries.",
            "archive_requirement": "Every promotion or demotion is written to Archives with timestamp, evidence, reason, and approving authority.",
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
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
