"""Operating Reserve router — USD-denominated reserve balance for governed Veklom execution.

Pricing ladder (v1_public, 2026-05-01):
  Tier             | Activation  | Min Reserve | Playground Run | Compare Run | BYOK /1k | Managed /1k
  Founding         | $395        | $150        | $0.25          | $0.75       | $6       | $12
  Standard         | $795        | $300        | $0.40          | $1.20       | $8       | $16
  Regulated        | from $2,500 | $2,500      | contact        | contact     | $10      | $20

Add-ons (all tiers, per-tier pricing):
  Signed Evidence Package  — Founding $99 / Standard $149 / Regulated $199
  Auditor Bundle           — Founding $249 / Standard $349 / Regulated $499

Marketplace:
  Standard take: 12% | Preferred partner: 8% | Founding vendor first $2,500 GMV: 0%
  Payouts: NET-14

Design:
- Reserve balance is USD-denominated (Decimal, 6dp), never expires.
- Activation creates the workspace record at a tier and charges the activation fee +
  minimum reserve top-up via Stripe Checkout.
- Debit is atomic with SELECT ... FOR UPDATE to prevent overdraft races.
- Every debit/credit emits a ReserveTransaction row with an event_type label that
  maps directly to the pricing table above — audit-ready and queryable by the
  workspace dashboard.
- Hard-stop: if reserve_balance_usd < event_cost, raise 402 with a topup URL.
  Callers (pipelines/execute, governance, evidence) call `reserve_debit()` before
  doing any real work.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from core.redis_pool import get_redis
from db.session import Base, get_db
from db.models import User

settings = get_settings()
router = APIRouter(prefix="/reserve", tags=["reserve"])


# ── ORM Models ─────────────────────────────────────────────────────────────────
# These extend the existing db.models module.  If you prefer to colocate all
# models in db/models.py, move these classes there and remove the Base import.

class WorkspaceReserve(Base):
    """One row per workspace — the Operating Reserve ledger header."""
    __tablename__ = "workspace_reserve"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(String(64), nullable=False, unique=True, index=True)
    tier = Column(String(32), nullable=False, default="founding")  # founding | standard | regulated
    activation_status = Column(String(32), nullable=False, default="pending")  # pending | active | suspended
    activation_stripe_session_id = Column(String(256), nullable=True)
    activation_fee_usd = Column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    reserve_balance_usd = Column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    total_funded_usd = Column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    total_debited_usd = Column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    activated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReserveTransaction(Base):
    """Immutable ledger of every debit/credit against the Operating Reserve."""
    __tablename__ = "reserve_transaction"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(String(64), nullable=False, index=True)
    reserve_id = Column(PGUUID(as_uuid=True), ForeignKey("workspace_reserve.id"), nullable=False)
    event_type = Column(String(64), nullable=False)  # see EVENT_PRICING keys
    direction = Column(String(8), nullable=False)    # credit | debit
    amount_usd = Column(Numeric(14, 6), nullable=False)
    balance_before_usd = Column(Numeric(14, 6), nullable=False)
    balance_after_usd = Column(Numeric(14, 6), nullable=False)
    stripe_session_id = Column(String(256), nullable=True)
    ref_id = Column(String(128), nullable=True)      # pipeline_run_id, evidence_id, etc.
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ── Pricing Tables ─────────────────────────────────────────────────────────────

TIER_CONFIG: dict[str, dict[str, Any]] = {
    "founding": {
        "activation_fee_usd": Decimal("395.00"),
        "min_reserve_usd": Decimal("150.00"),
        "display": "Founding Activation",
    },
    "standard": {
        "activation_fee_usd": Decimal("795.00"),
        "min_reserve_usd": Decimal("300.00"),
        "display": "Standard",
    },
    "regulated": {
        "activation_fee_usd": Decimal("2500.00"),
        "min_reserve_usd": Decimal("2500.00"),
        "display": "Regulated / Enterprise",
    },
}

# event_type → per-tier cost in USD
EVENT_PRICING: dict[str, dict[str, Decimal]] = {
    "playground_run": {
        "founding": Decimal("0.25"),
        "standard": Decimal("0.40"),
        "regulated": Decimal("0"),   # contact pricing — caller must pre-approve
    },
    "compare_run": {
        "founding": Decimal("0.75"),
        "standard": Decimal("1.20"),
        "regulated": Decimal("0"),
    },
    "signed_playground_export": {
        "founding": Decimal("3.00"),
        "standard": Decimal("4.00"),
        "regulated": Decimal("0"),
    },
    # Governance calls are priced per-1000; callers pass quantity and we multiply.
    "byok_governance_call": {
        "founding": Decimal("0.006"),   # $6 / 1,000
        "standard": Decimal("0.008"),
        "regulated": Decimal("0.010"),
    },
    "managed_governance_call": {
        "founding": Decimal("0.012"),   # $12 / 1,000
        "standard": Decimal("0.016"),
        "regulated": Decimal("0.020"),
    },
    "signed_evidence_package": {
        "founding": Decimal("99.00"),
        "standard": Decimal("149.00"),
        "regulated": Decimal("199.00"),
    },
    "auditor_bundle": {
        "founding": Decimal("249.00"),
        "standard": Decimal("349.00"),
        "regulated": Decimal("499.00"),
    },
}

MARKETPLACE_TAKE = {
    "standard": Decimal("0.12"),
    "preferred_partner": Decimal("0.08"),
    "founding_vendor_gmv_threshold": Decimal("2500.00"),  # 0% until this GMV
}


# ── Schemas ────────────────────────────────────────────────────────────────────

class ActivationRequest(BaseModel):
    tier: str = Field(..., pattern=r"^(founding|standard|regulated)$")
    success_url: str = Field(..., min_length=10, max_length=2000)
    cancel_url: str = Field(..., min_length=10, max_length=2000)


class TopupRequest(BaseModel):
    amount_usd: Decimal = Field(..., gt=Decimal("0"), le=Decimal("50000"))
    success_url: str = Field(..., min_length=10, max_length=2000)
    cancel_url: str = Field(..., min_length=10, max_length=2000)


class DebitRequest(BaseModel):
    event_type: str
    quantity: int = Field(1, ge=1, le=100_000)
    ref_id: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None, max_length=500)


class EventCostQuery(BaseModel):
    event_type: str
    quantity: int = 1


# ── Helpers ────────────────────────────────────────────────────────────────────

def _q6(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _get_reserve(db: Session, workspace_id: str) -> Optional[WorkspaceReserve]:
    return (
        db.query(WorkspaceReserve)
        .filter(WorkspaceReserve.workspace_id == workspace_id)
        .first()
    )


def _require_active_reserve(db: Session, workspace_id: str) -> WorkspaceReserve:
    r = _get_reserve(db, workspace_id)
    if not r:
        raise HTTPException(402, "Workspace not activated. POST /api/v1/reserve/activate to begin.")
    if r.activation_status != "active":
        raise HTTPException(
            402,
            f"Workspace activation status is '{r.activation_status}'. "
            "Complete checkout at POST /api/v1/reserve/activate.",
        )
    return r


def _event_cost(tier: str, event_type: str, quantity: int) -> Decimal:
    tier_prices = EVENT_PRICING.get(event_type)
    if tier_prices is None:
        raise HTTPException(400, f"Unknown event_type '{event_type}'")
    unit = tier_prices.get(tier, Decimal("0"))
    if unit == Decimal("0") and tier == "regulated":
        raise HTTPException(
            402,
            "Regulated tier pricing is private. Contact sales to pre-approve this event.",
        )
    return _q6(unit * quantity)


def _invalidate_reserve_cache(workspace_id: str) -> None:
    try:
        get_redis().delete(f"reserve:balance:{workspace_id}")
    except Exception:
        pass


def _cache_reserve_balance(workspace_id: str, balance: Decimal, ttl: int = 60) -> None:
    try:
        get_redis().setex(f"reserve:balance:{workspace_id}", ttl, str(balance))
    except Exception:
        pass


# ── Public debit helper (called by pipelines, governance, evidence routers) ────

def reserve_debit(
    db: Session,
    workspace_id: str,
    event_type: str,
    quantity: int = 1,
    ref_id: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Atomic reserve debit — call before doing any billable work.

    Returns dict with {amount_usd, balance_after_usd, transaction_id}.
    Raises HTTP 402 if insufficient balance or workspace not activated.
    """
    r = _require_active_reserve(db, workspace_id)
    cost = _event_cost(r.tier, event_type, quantity)

    # Lock the row for the duration of this transaction.
    r = (
        db.query(WorkspaceReserve)
        .filter(WorkspaceReserve.workspace_id == workspace_id)
        .with_for_update()
        .first()
    )

    if Decimal(str(r.reserve_balance_usd)) < cost:
        raise HTTPException(
            402,
            {
                "detail": "Insufficient Operating Reserve balance.",
                "required_usd": str(cost),
                "balance_usd": str(r.reserve_balance_usd),
                "topup_url": "/api/v1/reserve/topup",
            },
        )

    balance_before = Decimal(str(r.reserve_balance_usd))
    balance_after = _q6(balance_before - cost)

    r.reserve_balance_usd = balance_after
    r.total_debited_usd = _q6(Decimal(str(r.total_debited_usd)) + cost)
    r.updated_at = datetime.utcnow()

    txn = ReserveTransaction(
        workspace_id=workspace_id,
        reserve_id=r.id,
        event_type=event_type,
        direction="debit",
        amount_usd=cost,
        balance_before_usd=balance_before,
        balance_after_usd=balance_after,
        ref_id=ref_id,
        description=description or f"{event_type} x{quantity}",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    _invalidate_reserve_cache(workspace_id)

    return {
        "transaction_id": str(txn.id),
        "event_type": event_type,
        "amount_usd": str(cost),
        "balance_after_usd": str(balance_after),
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/balance")
async def get_reserve_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the workspace Operating Reserve balance and tier info."""
    r = _get_reserve(db, current_user.workspace_id)
    if not r:
        return {
            "activated": False,
            "reserve_balance_usd": "0.000000",
            "tier": None,
            "activation_status": "pending",
            "activate_url": "/api/v1/reserve/activate",
        }
    return {
        "activated": r.activation_status == "active",
        "tier": r.tier,
        "activation_status": r.activation_status,
        "reserve_balance_usd": str(r.reserve_balance_usd),
        "total_funded_usd": str(r.total_funded_usd),
        "total_debited_usd": str(r.total_debited_usd),
        "activated_at": r.activated_at.isoformat() if r.activated_at else None,
    }


@router.post("/activate", status_code=201)
async def activate_workspace(
    payload: ActivationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session that collects activation fee + minimum reserve top-up.

    On successful payment the Stripe webhook (subscriptions webhook handler) must:
      1. Set workspace_reserve.activation_status = 'active'
      2. Credit reserve_balance_usd with the min_reserve amount
      3. Record a 'credit' ReserveTransaction with event_type='activation_topup'
    """
    if not settings.stripe_secret_key:
        raise HTTPException(503, "Stripe not configured")

    existing = _get_reserve(db, current_user.workspace_id)
    if existing and existing.activation_status == "active":
        raise HTTPException(409, "Workspace is already activated")

    tier_cfg = TIER_CONFIG.get(payload.tier)
    if not tier_cfg:
        raise HTTPException(400, f"Unknown tier '{payload.tier}'")

    import stripe
    stripe.api_key = settings.stripe_secret_key

    activation_fee = tier_cfg["activation_fee_usd"]
    min_reserve = tier_cfg["min_reserve_usd"]
    total_cents = int((activation_fee + min_reserve) * 100)

    success_sep = "&" if "?" in payload.success_url else "?"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Veklom {tier_cfg['display']} — Activation + Operating Reserve",
                        "description": (
                            f"${activation_fee} activation fee + "
                            f"${min_reserve} minimum Operating Reserve (never expires)"
                        ),
                    },
                    "unit_amount": total_cents,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=payload.success_url + f"{success_sep}session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=payload.cancel_url,
        metadata={
            "workspace_id": current_user.workspace_id,
            "type": "reserve_activation",
            "tier": payload.tier,
            "activation_fee_usd": str(activation_fee),
            "min_reserve_usd": str(min_reserve),
        },
    )

    # Upsert a pending reserve record so we can correlate the webhook.
    if existing:
        existing.tier = payload.tier
        existing.activation_stripe_session_id = session.id
        existing.activation_fee_usd = activation_fee
        existing.updated_at = datetime.utcnow()
    else:
        reserve = WorkspaceReserve(
            workspace_id=current_user.workspace_id,
            tier=payload.tier,
            activation_status="pending",
            activation_stripe_session_id=session.id,
            activation_fee_usd=activation_fee,
        )
        db.add(reserve)
    db.commit()

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "tier": payload.tier,
        "activation_fee_usd": str(activation_fee),
        "min_reserve_usd": str(min_reserve),
        "total_charged_usd": str(activation_fee + min_reserve),
    }


@router.post("/topup", status_code=201)
async def topup_reserve(
    payload: TopupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session to top-up the Operating Reserve.

    On successful payment the Stripe webhook must credit reserve_balance_usd
    and add a ReserveTransaction with direction='credit', event_type='topup'.
    """
    if not settings.stripe_secret_key:
        raise HTTPException(503, "Stripe not configured")

    _require_active_reserve(db, current_user.workspace_id)

    import stripe
    stripe.api_key = settings.stripe_secret_key

    amount_cents = int(payload.amount_usd * 100)
    success_sep = "&" if "?" in payload.success_url else "?"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Veklom Operating Reserve Top-Up",
                        "description": f"${payload.amount_usd} added to your never-expiring reserve",
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=payload.success_url + f"{success_sep}session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=payload.cancel_url,
        metadata={
            "workspace_id": current_user.workspace_id,
            "type": "reserve_topup",
            "amount_usd": str(payload.amount_usd),
        },
    )

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "amount_usd": str(payload.amount_usd),
    }


@router.post("/webhook/fulfil", include_in_schema=False)
async def fulfil_reserve_payment(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Internal endpoint called by the Stripe webhook handler to credit the reserve.

    NOT exposed in OpenAPI docs. Called from apps/api/routers/subscriptions.py
    after verifying the Stripe signature on the raw webhook payload.

    Expected metadata keys:
      type          — 'reserve_activation' | 'reserve_topup'
      workspace_id  — str
      amount_usd    — str (topup) | implicit from min_reserve_usd (activation)
      tier          — str (activation only)
      min_reserve_usd — str (activation only)
    """
    import stripe
    stripe.api_key = settings.stripe_secret_key

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        raise HTTPException(400, f"Stripe session retrieval failed: {exc}")

    if session.payment_status != "paid":
        raise HTTPException(400, "Session not paid")

    meta = session.metadata or {}
    workspace_id = meta.get("workspace_id")
    event_kind = meta.get("type")

    if not workspace_id or event_kind not in ("reserve_activation", "reserve_topup"):
        raise HTTPException(400, "Invalid session metadata")

    r = (
        db.query(WorkspaceReserve)
        .filter(WorkspaceReserve.workspace_id == workspace_id)
        .with_for_update()
        .first()
    )
    if not r:
        raise HTTPException(404, "Reserve record not found")

    if event_kind == "reserve_activation":
        credit_usd = _q6(Decimal(meta.get("min_reserve_usd", "0")))
        r.activation_status = "active"
        r.activated_at = datetime.utcnow()
        event_type_label = "activation_topup"
    else:
        credit_usd = _q6(Decimal(meta.get("amount_usd", "0")))
        event_type_label = "topup"

    if credit_usd <= Decimal("0"):
        raise HTTPException(400, "Credit amount must be positive")

    balance_before = Decimal(str(r.reserve_balance_usd))
    balance_after = _q6(balance_before + credit_usd)
    r.reserve_balance_usd = balance_after
    r.total_funded_usd = _q6(Decimal(str(r.total_funded_usd)) + credit_usd)
    r.updated_at = datetime.utcnow()

    txn = ReserveTransaction(
        workspace_id=workspace_id,
        reserve_id=r.id,
        event_type=event_type_label,
        direction="credit",
        amount_usd=credit_usd,
        balance_before_usd=balance_before,
        balance_after_usd=balance_after,
        stripe_session_id=session_id,
        description=f"Stripe fulfillment: {event_kind}",
    )
    db.add(txn)
    db.commit()
    db.refresh(r)
    _invalidate_reserve_cache(workspace_id)

    return {
        "workspace_id": workspace_id,
        "event_kind": event_kind,
        "credit_usd": str(credit_usd),
        "balance_after_usd": str(r.reserve_balance_usd),
        "activation_status": r.activation_status,
    }


@router.post("/debit")
async def manual_debit(
    payload: DebitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Debit the Operating Reserve for a billable event.

    Primarily used by internal service routers via `reserve_debit()`.  Exposed
    as a REST endpoint so the playground UI can also trigger it directly when a
    user initiates a governed run from the frontend.
    """
    result = reserve_debit(
        db=db,
        workspace_id=current_user.workspace_id,
        event_type=payload.event_type,
        quantity=payload.quantity,
        ref_id=payload.ref_id,
        description=payload.description,
    )
    return result


@router.get("/pricing")
async def get_pricing_ladder():
    """Public pricing ladder — no auth required.

    Returns the full versioned event pricing table so the frontend pricing
    section and the API catalog playground can render live, always-accurate
    prices without hardcoding them.
    """
    return {
        "version": "v1_public",
        "effective_date": "2026-05-01",
        "tiers": {
            tier: {
                "display": cfg["display"],
                "activation_fee_usd": str(cfg["activation_fee_usd"]),
                "min_reserve_usd": str(cfg["min_reserve_usd"]),
            }
            for tier, cfg in TIER_CONFIG.items()
        },
        "events": {
            event: {t: str(p) for t, p in prices.items()}
            for event, prices in EVENT_PRICING.items()
        },
        "marketplace": {
            "standard_take": str(MARKETPLACE_TAKE["standard"]),
            "preferred_partner_take": str(MARKETPLACE_TAKE["preferred_partner"]),
            "founding_vendor_free_gmv_usd": str(MARKETPLACE_TAKE["founding_vendor_gmv_threshold"]),
            "payout_terms": "NET-14",
        },
    }


@router.get("/transactions")
async def list_reserve_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    direction: Optional[str] = Query(None, pattern=r"^(credit|debit)$"),
    event_type: Optional[str] = Query(None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Paginated reserve transaction ledger for the workspace dashboard."""
    _require_active_reserve(db, current_user.workspace_id)
    q = db.query(ReserveTransaction).filter(
        ReserveTransaction.workspace_id == current_user.workspace_id
    )
    if direction:
        q = q.filter(ReserveTransaction.direction == direction)
    if event_type:
        q = q.filter(ReserveTransaction.event_type == event_type)
    total = q.count()
    rows = q.order_by(ReserveTransaction.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(t.id),
                "event_type": t.event_type,
                "direction": t.direction,
                "amount_usd": str(t.amount_usd),
                "balance_before_usd": str(t.balance_before_usd),
                "balance_after_usd": str(t.balance_after_usd),
                "ref_id": t.ref_id,
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            }
            for t in rows
        ],
    }


@router.get("/event-cost")
async def preview_event_cost(
    event_type: str = Query(..., max_length=64),
    quantity: int = Query(1, ge=1, le=100_000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview cost before committing — used by the playground before running."""
    r = _require_active_reserve(db, current_user.workspace_id)
    cost = _event_cost(r.tier, event_type, quantity)
    balance = Decimal(str(r.reserve_balance_usd))
    return {
        "event_type": event_type,
        "quantity": quantity,
        "unit_cost_usd": str(EVENT_PRICING[event_type][r.tier]),
        "total_cost_usd": str(cost),
        "current_balance_usd": str(balance),
        "sufficient": balance >= cost,
    }
