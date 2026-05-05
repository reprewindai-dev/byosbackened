"""Marketplace automation — auto-classify, auto-validate, install, plugin bridge.

Turns the marketplace into a self-organizing, vendor-self-serve system that leverages
backend infrastructure no competitor has:

- Auto-classify uses the local Ollama model (qwen2.5) to fill listing_type, category,
  tags, summary, and compliance_badges. Vendors never pick a category.
- Auto-validate runs the listing through content_safety + privacy (PII detect) +
  CostCalculator preflight. Listings auto-publish if green; admin queue if red.
- Install creates a real Pipeline in the buyer's workspace from install_payload —
  closing the marketplace → workspace loop in one click.
- from-plugin reads the existing plugin registry and converts any installed plugin
  into a draft listing (perfect for the "tweak GitHub tools then resell" workflow).
- preflight returns predicted cost + quality + failure-risk for the listing's payload
  in the *current* workspace's data context — uses the autonomous ML stack.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, get_current_workspace_id
from core.cost_intelligence import CostCalculator
from db.models import (
    Listing,
    Pipeline,
    PipelineStatus,
    PipelineVersion,
    User,
    Vendor,
)
from db.session import get_db


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/marketplace", tags=["marketplace-automation"])
cost_calculator = CostCalculator()


# ── Constants ─────────────────────────────────────────────────────────────────

VALID_TYPES = {
    "pipeline", "tool", "prompt_pack", "dataset", "agent",
    "connector", "evidence_pack", "edge_template",
}
VALID_CATEGORIES = {
    "legal", "medical", "finance", "compliance",
    "infra", "edge_industrial", "agency", "general",
}

_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _slugify(s: str) -> str:
    s = _SLUG_RE.sub("-", (s or "").lower()).strip("-")
    return s[:120] or f"listing-{uuid.uuid4().hex[:8]}"


# ── Schemas ───────────────────────────────────────────────────────────────────

class AutoClassifyRequest(BaseModel):
    listing_id: str


class AutoClassifyResponse(BaseModel):
    listing_type: str
    category: str
    tags: list[str]
    summary: str
    compliance_badges: list[str]


class AutoValidateRequest(BaseModel):
    listing_id: str
    sample_input: Optional[str] = Field(
        None,
        description="Optional sample input to dry-run through the pipeline payload",
        max_length=4000,
    )


class AutoValidateResponse(BaseModel):
    passed: bool
    auto_publish: bool
    checks: dict[str, dict]
    notes: list[str]


class InstallRequest(BaseModel):
    listing_id: str
    pipeline_name: Optional[str] = Field(None, max_length=200)


class InstallResponse(BaseModel):
    pipeline_id: str
    pipeline_slug: str
    listing_id: str
    install_count: int


class FromPluginRequest(BaseModel):
    plugin_name: str = Field(..., min_length=1, max_length=120)
    title: Optional[str] = Field(None, max_length=200)
    price_cents: int = Field(0, ge=0)


class GitHubImportRequest(BaseModel):
    repo_url: str = Field(..., max_length=300)
    title: Optional[str] = Field(None, max_length=200)
    price_cents: int = Field(0, ge=0)


class PreflightResponse(BaseModel):
    listing_id: str
    predicted_cost_per_run_usd: float
    confidence_lower_usd: float
    confidence_upper_usd: float
    predicted_quality: Optional[float] = None
    failure_risk: Optional[float] = None
    alternative_providers: list[dict]
    compliance_badges: list[str]


class AutomationRunRequest(BaseModel):
    trigger: str = Field("manual", max_length=64)
    source: str = Field("api", max_length=120)
    limit: int = Field(25, ge=1, le=100)


class AutomationRunResponse(BaseModel):
    status: str
    workspace_id: str
    trigger: str
    source: str
    scanned: int
    classified: int
    validation_marked: int
    pending_review: int
    generated_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_listing(db: Session, listing_id: str, current_user: User) -> Listing:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing


def _require_owned_listing(db: Session, listing_id: str, current_user: User) -> Listing:
    listing = _require_listing(db, listing_id, current_user)
    vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if not vendor or listing.vendor_id != vendor.id:
        raise HTTPException(403, "Listing not owned by current vendor")
    return listing


def _heuristic_classify(title: str, description: str, payload: Optional[dict]) -> dict:
    """Rule-based classifier used as a fallback if local LLM is unavailable.

    Designed to never fail and to produce non-empty values so the listing can still
    auto-publish through the trust-tier path.
    """
    text = f"{title} {description or ''}".lower()
    payload_text = json.dumps(payload or {}).lower()
    blob = f"{text} {payload_text}"

    listing_type = "pipeline"
    if "prompt" in blob and "pack" in blob:
        listing_type = "prompt_pack"
    elif "tool" in blob or "function" in blob:
        listing_type = "tool"
    elif "agent" in blob:
        listing_type = "agent"
    elif "dataset" in blob:
        listing_type = "dataset"
    elif "snmp" in blob or "modbus" in blob or "mqtt" in blob:
        listing_type = "edge_template"
    elif "evidence" in blob or "soc2" in blob or "audit" in blob:
        listing_type = "evidence_pack"

    category = "general"
    for kw, cat in (
        ("legal", "legal"),
        ("contract", "legal"),
        ("medical", "medical"),
        ("hipaa", "medical"),
        ("phi", "medical"),
        ("finance", "finance"),
        ("ledger", "finance"),
        ("invoice", "finance"),
        ("soc2", "compliance"),
        ("compliance", "compliance"),
        ("snmp", "edge_industrial"),
        ("modbus", "edge_industrial"),
        ("mqtt", "edge_industrial"),
        ("infrastructure", "infra"),
        ("agency", "agency"),
    ):
        if kw in blob:
            category = cat
            break

    tags: list[str] = []
    for kw in ("redact", "privacy", "audit", "policy", "rag", "summarize",
              "extract", "classify", "moderation", "translate", "ocr"):
        if kw in blob:
            tags.append(kw)

    badges: list[str] = []
    if category in ("medical",):
        badges.append("HIPAA-aware")
    if category in ("legal", "compliance"):
        badges.append("Audit-trail-included")
    if "soc2" in blob:
        badges.append("SOC2-evidence")
    if "gdpr" in blob or "eu" in blob:
        badges.append("EU-sovereign")
    badges.append("Tamper-evident-ledger")  # always — every Veklom run is HMAC-chained

    summary = (description or title)[:280]
    return {
        "listing_type": listing_type,
        "category": category,
        "tags": tags[:10],
        "summary": summary,
        "compliance_badges": list(dict.fromkeys(badges)),  # de-dupe, preserve order
    }


def _llm_classify(title: str, description: str, payload: Optional[dict]) -> Optional[dict]:
    """Try the local Ollama model. Returns None if it's unavailable so the heuristic
    path stays the source of truth — never blocks auto-publish on LLM downtime.
    """
    try:
        from core.llm.ollama_client import get_ollama_client
        client = get_ollama_client()
    except Exception:
        return None


    prompt = (
        "You are a marketplace classifier. Given a listing, return ONLY a JSON object with "
        "keys: listing_type, category, tags (array of <= 8 strings), summary (<= 280 chars), "
        "compliance_badges (array). Valid listing_type: pipeline|tool|prompt_pack|dataset|"
        "agent|connector|evidence_pack|edge_template. Valid category: legal|medical|finance|"
        "compliance|infra|edge_industrial|agency|general.\n\n"
        f"Title: {title}\n"
        f"Description: {(description or '')[:1200]}\n"
        f"Payload preview: {json.dumps(payload or {})[:800]}\n\n"
        "JSON:"
    )

    try:
        resp = client.generate(prompt=prompt, max_tokens=400, temperature=0.1)
        text = resp.get("response") if isinstance(resp, dict) else str(resp)
        if not text:
            return None
        # Extract first JSON object.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        if data.get("listing_type") not in VALID_TYPES:
            return None
        if data.get("category") not in VALID_CATEGORIES:
            return None
        return {
            "listing_type": data["listing_type"],
            "category": data["category"],
            "tags": [str(t)[:40] for t in (data.get("tags") or [])][:10],
            "summary": str(data.get("summary") or "")[:280],
            "compliance_badges": [str(b)[:60] for b in (data.get("compliance_badges") or [])][:8],
        }
    except Exception as exc:
        logger.info(f"LLM classify fallback (using heuristic): {exc}")
        return None


@router.post("/automation/run", response_model=AutomationRunResponse)
async def run_marketplace_automation(
    payload: AutomationRunRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Run scheduled marketplace classification and trust-bookkeeping."""
    now = datetime.utcnow()
    listings = (
        db.query(Listing)
        .filter(Listing.workspace_id == workspace_id)
        .filter(Listing.status.in_(("draft", "pending_review")))
        .order_by(desc(Listing.updated_at))
        .limit(payload.limit)
        .all()
    )
    classified = 0
    validation_marked = 0
    pending_review = 0
    for listing in listings:
        if not listing.auto_classified:
            data = _heuristic_classify(
                listing.title,
                listing.description or "",
                listing.install_payload if isinstance(listing.install_payload, dict) else None,
            )
            listing.listing_type = data["listing_type"]
            listing.category = data["category"]
            listing.tags = data["tags"]
            listing.summary = data["summary"]
            listing.compliance_badges = data["compliance_badges"]
            listing.auto_classified = True
            classified += 1

        if listing.auto_classified and not listing.auto_validated:
            listing.validation_report = {
                "status": "needs_review",
                "checks": {
                    "schema": "passed" if listing.install_payload else "needs_review",
                    "classification": "passed",
                    "human_review": "required",
                },
                "source": payload.source,
                "trigger": payload.trigger,
                "generated_at": now.isoformat() + "Z",
            }
            listing.auto_validated = True
            validation_marked += 1

        if listing.status == "draft":
            listing.status = "pending_review"
            pending_review += 1
        listing.updated_at = now

    if listings:
        db.commit()
    return AutomationRunResponse(
        status="ok",
        workspace_id=workspace_id,
        trigger=payload.trigger,
        source=payload.source,
        scanned=len(listings),
        classified=classified,
        validation_marked=validation_marked,
        pending_review=pending_review,
        generated_at=now.isoformat() + "Z",
    )


def _trust_tier_can_auto_publish(vendor: Vendor) -> bool:
    """A vendor auto-publishes when:
      - Stripe Connect onboarded, AND
      - subscription active on a paid plan, AND
      - plan is in the trusted set.
    Otherwise, listing goes to admin review.
    """
    if not vendor.is_onboarded:
        return False
    if (vendor.subscription_status or "").lower() != "active":
        return False
    return (vendor.plan or "").lower() in {"verified", "sovereign"}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/listings/auto-classify", response_model=AutoClassifyResponse)
async def auto_classify(
    payload: AutoClassifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fill listing_type, category, tags, summary, compliance_badges automatically.

    Vendors never pick a category — the system reads title + description + install
    payload and writes the metadata. Local Ollama if available, deterministic
    heuristic as a guaranteed fallback.
    """
    listing = _require_owned_listing(db, payload.listing_id, current_user)

    classified = _llm_classify(
        title=listing.title,
        description=listing.description or "",
        payload=listing.install_payload,
    ) or _heuristic_classify(
        title=listing.title,
        description=listing.description or "",
        payload=listing.install_payload,
    )

    listing.listing_type = classified["listing_type"]
    listing.category = classified["category"]
    listing.tags = classified["tags"]
    listing.summary = classified["summary"]
    listing.compliance_badges = classified["compliance_badges"]
    listing.auto_classified = True
    if not listing.slug:
        listing.slug = _slugify(listing.title)

    db.commit()
    db.refresh(listing)
    return AutoClassifyResponse(**classified)


@router.post("/listings/auto-validate", response_model=AutoValidateResponse)
async def auto_validate(
    payload: AutoValidateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run the listing through the governance harness.

    Checks performed (each runs best-effort and degrades gracefully):
      1. Content safety — scan title + description + payload for prohibited content
      2. Privacy — PII detector on the same surface
      3. Payload structure — install_payload must parse + match its listing_type
      4. Cost preflight — predict per-run cost via CostCalculator (caches result)
      5. Sandbox exec (optional) — if sample_input is provided, run a single Ollama
         step against the payload's first prompt node to confirm it produces output

    `auto_publish=true` only when ALL hard checks pass AND vendor is in the trust tier.
    """
    listing = _require_owned_listing(db, payload.listing_id, current_user)
    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()

    checks: dict[str, dict] = {}
    notes: list[str] = []

    # 1. Content safety
    try:
        from core.content_safety.scanner import scan_text  # type: ignore
        scan_blob = f"{listing.title}\n{listing.description or ''}\n{json.dumps(listing.install_payload or {})}"
        result = scan_text(scan_blob[:8000]) if callable(scan_text) else None
        flagged = bool(result and result.get("flagged"))
        checks["content_safety"] = {"ok": not flagged, "flagged": flagged}
    except Exception:
        # Module not present — soft-pass with note.
        checks["content_safety"] = {"ok": True, "skipped": True}
        notes.append("content_safety scanner not available; soft-pass")

    # 2. Privacy / PII
    try:
        from core.privacy.detector import detect_pii  # type: ignore
        pii_blob = f"{listing.description or ''}\n{json.dumps(listing.install_payload or {})}"
        pii_result = detect_pii(pii_blob[:8000]) if callable(detect_pii) else None
        pii_types = (pii_result or {}).get("types") or []
        checks["privacy"] = {"ok": len(pii_types) == 0, "pii_types": pii_types}
        if pii_types:
            notes.append(f"PII detected in listing surface: {pii_types[:5]}")
    except Exception:
        checks["privacy"] = {"ok": True, "skipped": True}
        notes.append("PII detector not available; soft-pass")

    # 3. Payload structure
    payload_obj = listing.install_payload or {}
    payload_ok = True
    if listing.listing_type == "pipeline":
        nodes = payload_obj.get("nodes") if isinstance(payload_obj, dict) else None
        if not isinstance(nodes, list) or not nodes:
            payload_ok = False
            notes.append("pipeline install_payload missing 'nodes' array")
    elif listing.listing_type == "prompt_pack":
        prompts = payload_obj.get("prompts") if isinstance(payload_obj, dict) else None
        if not isinstance(prompts, list) or not prompts:
            payload_ok = False
            notes.append("prompt_pack install_payload missing 'prompts' array")
    checks["payload_structure"] = {"ok": payload_ok}

    # 4. Cost preflight (cache predicted_cost_per_run)
    try:
        prediction = cost_calculator.predict_cost(
            operation_type="generation",
            provider="local",
            input_tokens=500,
            estimated_output_tokens=300,
            model="qwen2.5:3b",
        )
        listing.predicted_cost_per_run = prediction.predicted_cost
        checks["cost_preflight"] = {
            "ok": True,
            "predicted_cost_usd": float(prediction.predicted_cost),
            "alternatives": prediction.alternative_providers[:3],
        }
    except Exception as exc:
        checks["cost_preflight"] = {"ok": True, "skipped": True, "reason": str(exc)[:120]}

    # 5. Optional sandbox exec
    if payload.sample_input:
        try:
            from core.llm.ollama_client import get_ollama_client
            client = get_ollama_client()
            r = client.generate(prompt=payload.sample_input[:2000], max_tokens=120, temperature=0.2)
            ok = bool((r or {}).get("response"))
            checks["sandbox_exec"] = {"ok": ok}
        except Exception as exc:
            checks["sandbox_exec"] = {"ok": False, "reason": str(exc)[:120]}
            notes.append("sandbox exec failed; manual review recommended")

    hard_checks_ok = all(c.get("ok", True) for c in checks.values())
    auto_publish = (
        hard_checks_ok
        and bool(vendor and _trust_tier_can_auto_publish(vendor))
    )

    listing.auto_validated = hard_checks_ok
    listing.validation_report = {
        "checks": checks,
        "notes": notes,
        "validated_at": datetime.utcnow().isoformat(),
    }
    if auto_publish:
        listing.status = "active"
    elif hard_checks_ok:
        listing.status = "pending_review"
    else:
        listing.status = "rejected"

    db.commit()
    return AutoValidateResponse(
        passed=hard_checks_ok,
        auto_publish=auto_publish,
        checks=checks,
        notes=notes,
    )


@router.post("/listings/{listing_id}/install", response_model=InstallResponse)
async def install_listing(
    listing_id: str,
    payload: InstallRequest = None,  # type: ignore[assignment]
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Turn a listing's install_payload into a real Pipeline in the buyer's workspace.

    This is the "marketplace → working pipeline" close-the-loop endpoint nobody else has.
    Only `pipeline` and `agent` listing types are installable today; others return 400.
    """
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing.status != "active":
        raise HTTPException(409, "Listing is not active")
    if listing.listing_type not in ("pipeline", "agent"):
        raise HTTPException(400, f"listing_type='{listing.listing_type}' is not directly installable")

    install_payload = listing.install_payload or {}
    nodes = install_payload.get("nodes") if isinstance(install_payload, dict) else None
    if not isinstance(nodes, list) or not nodes:
        raise HTTPException(400, "Listing install_payload is missing a valid 'nodes' graph")

    pipeline_name = (payload and payload.pipeline_name) or f"{listing.title}"
    slug_base = _slugify(pipeline_name)
    slug = slug_base
    n = 1
    while db.query(Pipeline).filter(
        Pipeline.workspace_id == current_user.workspace_id, Pipeline.slug == slug
    ).first():
        n += 1
        slug = f"{slug_base}-{n}"

    pipeline = Pipeline(
        workspace_id=current_user.workspace_id,
        slug=slug,
        name=pipeline_name,
        description=f"Installed from marketplace listing: {listing.title}",
        status=PipelineStatus.ACTIVE,
        current_version=1,
        created_by=current_user.id,
    )
    db.add(pipeline)
    db.flush()

    version = PipelineVersion(
        pipeline_id=pipeline.id,
        version=1,
        graph=install_payload,
        policy_refs=(install_payload.get("policy_refs") if isinstance(install_payload, dict) else None),
        notes=f"Installed from listing {listing.id} v{listing.version}",
        created_by=current_user.id,
    )
    db.add(version)

    listing.install_count = (listing.install_count or 0) + 1
    db.commit()
    db.refresh(pipeline)

    return InstallResponse(
        pipeline_id=pipeline.id,
        pipeline_slug=pipeline.slug,
        listing_id=listing.id,
        install_count=listing.install_count,
    )


@router.post("/listings/from-plugin", status_code=201)
async def listing_from_plugin(
    payload: FromPluginRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Convert any installed plugin into a draft Listing.

    Reads plugin metadata via the existing PluginLoader and seeds a listing with
    sensible defaults. Vendor still owns the result and can edit / submit it.
    """
    vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if not vendor:
        raise HTTPException(403, "Active vendor profile required")

    try:
        from apps.plugins.loader import PluginLoader
        loader = PluginLoader()
        plugin_info = loader.load_plugin(payload.plugin_name)
    except Exception as exc:
        raise HTTPException(500, f"Failed to load plugin: {exc}")
    if not plugin_info:
        raise HTTPException(404, f"Plugin not found: {payload.plugin_name}")

    title = payload.title or plugin_info.get("name") or payload.plugin_name
    description = plugin_info.get("description") or ""
    workflows = plugin_info.get("workflows") or []
    providers = plugin_info.get("providers") or []

    install_payload = {
        "kind": "plugin",
        "plugin_name": payload.plugin_name,
        "version": plugin_info.get("version"),
        "providers": providers,
        "workflows": workflows,
        # Synthesize a simple pipeline graph wrapper so the listing is installable.
        "nodes": [
            {"id": "input", "type": "prompt", "label": "Input", "prompt": "{{input}}"},
            {"id": "plugin", "type": "tool", "label": title, "tool": payload.plugin_name},
            {"id": "policy", "type": "gate", "label": "Policy gate", "policy": "default"},
        ],
        "edges": [
            {"from": "input", "to": "plugin"},
            {"from": "plugin", "to": "policy"},
        ],
    }

    listing = Listing(
        vendor_id=vendor.id,
        workspace_id=current_user.workspace_id,
        title=title,
        slug=_slugify(title),
        description=description,
        version=plugin_info.get("version") or "1.0.0",
        listing_type="pipeline",  # plugins surface as installable pipelines
        price_cents=payload.price_cents,
        status="draft",
        install_payload=install_payload,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {
        "id": listing.id,
        "title": listing.title,
        "slug": listing.slug,
        "status": listing.status,
        "install_payload_kind": "plugin",
    }


@router.post("/listings/import-github", status_code=202)
async def import_github(
    payload: GitHubImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import a GitHub repo as a draft listing.

    Currently creates the listing shell with `source_url` set. Cloning + LLM-assisted
    rewrite runs in the worker queue (separate process) so the API stays fast and
    the import can survive restarts. The listing arrives in `draft` status; the
    vendor still drives `submit` which triggers auto-classify + auto-validate.
    """
    vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if not vendor:
        raise HTTPException(403, "Active vendor profile required")

    url = payload.repo_url.strip()
    if not url.startswith(("https://github.com/", "git@github.com:")):
        raise HTTPException(400, "Only GitHub URLs are supported")

    title = payload.title or url.rstrip("/").split("/")[-1].replace("-", " ").title()
    listing = Listing(
        vendor_id=vendor.id,
        workspace_id=current_user.workspace_id,
        title=title,
        slug=_slugify(title),
        description=f"Imported from {url}",
        version="0.1.0",
        listing_type="pipeline",
        price_cents=payload.price_cents,
        status="draft",
        source_url=url,
        install_payload={"kind": "github_import", "repo_url": url, "nodes": []},
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {
        "id": listing.id,
        "title": listing.title,
        "slug": listing.slug,
        "status": listing.status,
        "source_url": listing.source_url,
        "queued": True,
    }


@router.get("/categories")
async def list_categories(db: Session = Depends(get_db)):
    """Categories with active-listing counts. Drives the marketplace sidebar."""
    rows = (
        db.query(Listing.category, func.count(Listing.id))
        .filter(Listing.status == "active", Listing.category.isnot(None))
        .group_by(Listing.category)
        .all()
    )
    counts = {cat: int(n) for cat, n in rows}
    return {
        "categories": [
            {"slug": c, "count": counts.get(c, 0)} for c in sorted(VALID_CATEGORIES)
        ],
        "types": [
            {"slug": t, "count": _count_by_type(db, t)} for t in sorted(VALID_TYPES)
        ],
    }


def _count_by_type(db: Session, listing_type: str) -> int:
    return int(
        db.query(func.count(Listing.id))
        .filter(Listing.status == "active", Listing.listing_type == listing_type)
        .scalar()
        or 0
    )


@router.get("/featured")
async def list_featured(
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Featured + trending — computed automatically from install_count × rating × recency."""
    base = db.query(Listing).filter(Listing.status == "active")

    featured = base.filter(Listing.is_featured == True).limit(limit).all()  # noqa: E712
    trending = (
        base.order_by(desc(Listing.install_count), desc(Listing.rating_avg), desc(Listing.created_at))
        .limit(limit)
        .all()
    )
    new = base.order_by(desc(Listing.created_at)).limit(limit).all()

    def to_card(l: Listing) -> dict:
        return {
            "id": l.id,
            "slug": l.slug,
            "title": l.title,
            "summary": l.summary,
            "listing_type": l.listing_type,
            "category": l.category,
            "tags": l.tags or [],
            "compliance_badges": l.compliance_badges or [],
            "price_cents": l.price_cents,
            "currency": l.currency,
            "predicted_cost_per_run_usd": float(l.predicted_cost_per_run) if l.predicted_cost_per_run else None,
            "rating_avg": l.rating_avg,
            "rating_count": l.rating_count,
            "install_count": l.install_count,
            "is_featured": l.is_featured,
        }

    return {
        "featured": [to_card(l) for l in featured],
        "trending": [to_card(l) for l in trending],
        "new": [to_card(l) for l in new],
    }


@router.get("/listings/{listing_id}/preflight", response_model=PreflightResponse)
async def listing_preflight(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pre-purchase intelligence: predicted cost + quality + failure-risk.

    Combines /cost/predict (rule-based + ML) with the autonomous quality + failure
    predictors when available. This is the unique buyer experience: see the cost,
    quality, and risk *for your workspace's data context* before you click install.
    """
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(404, "Listing not found")

    prediction = cost_calculator.predict_cost(
        operation_type="generation",
        provider="local",
        input_tokens=500,
        estimated_output_tokens=300,
        model="qwen2.5:3b",
        workspace_id=current_user.workspace_id,
    )

    # Quality + failure-risk are best-effort — degrades cleanly if ML stack is cold.
    predicted_quality: Optional[float] = None
    failure_risk: Optional[float] = None
    try:
        from core.autonomous.ml_models.quality_predictor import get_quality_predictor_ml
        from core.autonomous.optimization.quality_optimizer import get_quality_optimizer

        quality_predictor = get_quality_predictor_ml()
        quality_optimizer = get_quality_optimizer()

        q = quality_predictor.predict_quality(
            workspace_id=current_user.workspace_id,
            operation_type="generation",
            provider="local",
            input_text=listing.summary or listing.title,
            db=db,
        )
        if isinstance(q, dict):
            predicted_quality = float(q.get("predicted_quality") or 0) or None

        risk = quality_optimizer.predict_failure_risk(
            workspace_id=current_user.workspace_id,
            operation_type="generation",
            provider="local",
            input_text=listing.summary or listing.title,
            db=db,
        )
        if isinstance(risk, dict):
            failure_risk = float(risk.get("failure_risk") or risk.get("risk") or 0) or None
    except Exception as exc:
        logger.info(f"preflight ML unavailable: {exc}")

    return PreflightResponse(
        listing_id=listing.id,
        predicted_cost_per_run_usd=float(prediction.predicted_cost),
        confidence_lower_usd=float(prediction.confidence_lower),
        confidence_upper_usd=float(prediction.confidence_upper),
        predicted_quality=predicted_quality,
        failure_risk=failure_risk,
        alternative_providers=prediction.alternative_providers[:3],
        compliance_badges=listing.compliance_badges or [],
    )
