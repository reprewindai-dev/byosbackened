"""Stripe subscription management: plans, checkout, webhook, portal.

Pricing model: flat annual license — charge for the control plane, not inference.
Tiers: Free (permanent) → Team ($12K/yr) → Business ($35K/yr) → Enterprise (custom).

DB enum mapping (PlanTier in db/models.py must stay in sync):
    free       → Free
    starter    → Team        ($12,000/year)
    pro        → Business    ($35,000/year)
    enterprise → Enterprise  (custom, sales-assisted)

NOTE: The DB enum values 'starter' and 'pro' are kept stable to avoid a
migration. Display names are 'Team' and 'Business' in all API responses and UI.
"""
import stripe
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from core.license import (
    LicenseStatus,
    require_active_license,
    TIER_FREE, TIER_TEAM, TIER_BUSINESS, TIER_ENTERPRISE,
    TIER_API_KEY_LIMITS, TIER_REQUEST_LIMITS, TIER_VENDOR_LIMITS,
)
from db.session import get_db
from db.models import Subscription, PlanTier, SubscriptionStatus, Workspace, User, TokenWallet, TokenTransaction

settings = get_settings()
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ─── Plan catalog ──────────────────────────────────────────────────────────────
# Flat annual license model. No per-token credits — charge for the control
# plane (routing, governance, cost intelligence, security), not inference.
#
# Price keys use 'yearly' only. Monthly billing is available as a convenience
# at a 20% premium (annual_cents / 10 * 1.2 per month).

PLANS = {
    "starter": {                                    # DB enum: starter | Display: Team
        "name": "Team",
        "tier": "starter",
        "price_monthly_cents": 120_000,             # $1,200/month (20% premium over annual)
        "price_yearly_cents": 1_200_000,            # $12,000/year flat
        "self_serve_checkout": True,
        "trial_days": 14,
        "monthly_credits_included": None,           # No credit model — flat license
        "limits": {
            "api_keys_max": TIER_API_KEY_LIMITS[TIER_TEAM],
            "requests_per_month": TIER_REQUEST_LIMITS[TIER_TEAM],
            "vendor_connections": TIER_VENDOR_LIMITS[TIER_TEAM],
        },
        "features": {
            "multi_vendor_routing":   True,
            "advanced_routing":       True,
            "cost_dashboard":         True,
            "budget_controls":        True,
            "kill_switch":            True,
            "savings_insights":       True,
            "audit_logs":             True,
            "rbac":                   True,
            "support_tier":           "silver",
            "support_sla_sev1_hrs":   1,
            # Business+ only
            "sso":                    False,
            "compliance_reports":     False,
            "gdpr_exports":           False,
            "hipaa_controls":         False,
            "failover_routing":       False,
            "content_safety":         False,
            "data_masking":           False,
            "privacy_audit_trail":    False,
            "locker_security":        False,
            "plugin_execution":       False,
            "governed_execution":     False,
            "audit_exports":          False,
            "white_label":            False,
            "sla_guarantee":          None,
            "private_deployment":     False,
        },
    },

    "pro": {                                        # DB enum: pro | Display: Business
        "name": "Business",
        "tier": "pro",
        "price_monthly_cents": 350_000,             # $3,500/month (20% premium)
        "price_yearly_cents": 3_500_000,            # $35,000/year flat
        "self_serve_checkout": True,
        "trial_days": 14,
        "monthly_credits_included": None,
        "limits": {
            "api_keys_max": TIER_API_KEY_LIMITS[TIER_BUSINESS],
            "requests_per_month": TIER_REQUEST_LIMITS[TIER_BUSINESS],
            "vendor_connections": TIER_VENDOR_LIMITS[TIER_BUSINESS],
        },
        "features": {
            "multi_vendor_routing":   True,
            "advanced_routing":       True,
            "failover_routing":       True,
            "cost_dashboard":         True,
            "budget_controls":        True,
            "kill_switch":            True,
            "savings_insights":       True,
            "audit_logs":             True,
            "audit_exports":          True,
            "rbac":                   True,
            "sso":                    True,
            "compliance_reports":     True,
            "gdpr_exports":           True,
            "hipaa_controls":         True,
            "content_safety":         True,
            "data_masking":           True,
            "privacy_audit_trail":    True,
            "locker_security":        True,
            "plugin_execution":       True,
            "governed_execution":     True,
            "support_tier":           "gold",
            "support_sla_sev1_hrs":   0.5,
            # Enterprise only
            "custom_routing":         False,
            "custom_endpoints":       False,
            "workspace_admin":        False,
            "white_label":            False,
            "private_deployment":     False,
            "sla_guarantee":          None,
            "annual_review":          False,
        },
    },

    "enterprise": {
        "name": "Enterprise",
        "tier": "enterprise",
        "price_monthly_cents": None,                # Sales-assisted, custom pricing
        "price_yearly_cents": None,                 # Minimum $75,000/year
        "self_serve_checkout": False,               # No self-serve — demo + scoping call required
        "trial_days": 0,                            # No trial — POC via scoping call instead
        "monthly_credits_included": None,
        "limits": {
            "api_keys_max": TIER_API_KEY_LIMITS[TIER_ENTERPRISE],   # None = unlimited
            "requests_per_month": TIER_REQUEST_LIMITS[TIER_ENTERPRISE],
            "vendor_connections": TIER_VENDOR_LIMITS[TIER_ENTERPRISE],
        },
        "features": {
            "multi_vendor_routing":   True,
            "advanced_routing":       True,
            "failover_routing":       True,
            "custom_routing":         True,
            "cost_dashboard":         True,
            "budget_controls":        True,
            "kill_switch":            True,
            "savings_insights":       True,
            "audit_logs":             True,
            "audit_exports":          True,
            "rbac":                   True,
            "sso":                    True,
            "compliance_reports":     True,
            "gdpr_exports":           True,
            "hipaa_controls":         True,
            "content_safety":         True,
            "data_masking":           True,
            "privacy_audit_trail":    True,
            "locker_security":        True,
            "advanced_security":      True,
            "plugin_execution":       True,
            "governed_execution":     True,
            "custom_endpoints":       True,
            "workspace_admin":        True,
            "white_label":            True,
            "private_deployment":     True,
            "annual_review":          True,
            "sla_guarantee":          "99.99%",
            "support_tier":           "platinum",
            "support_sla_sev1_hrs":   0,             # 24x7 Sev1+2
            "dedicated_tse":          True,
        },
    },
}

# Free tier — permanent, no expiry, no Stripe subscription needed.
FREE_PLAN = {
    "name": "Free",
    "tier": "free",
    "price_monthly_cents": 0,
    "price_yearly_cents": 0,
    "self_serve_checkout": False,
    "trial_days": 0,
    "monthly_credits_included": None,
    "limits": {
        "api_keys_max": TIER_API_KEY_LIMITS[TIER_FREE],
        "requests_per_month": TIER_REQUEST_LIMITS[TIER_FREE],
        "vendor_connections": TIER_VENDOR_LIMITS[TIER_FREE],
    },
    "features": {
        "view_marketplace":       True,
        "multi_vendor_routing":   False,
        "advanced_routing":       False,
        "cost_dashboard":         False,
        "budget_controls":        False,
        "kill_switch":            False,
        "audit_logs":             False,
        "rbac":                   False,
        "sso":                    False,
        "compliance_reports":     False,
        "plugin_execution":       False,
        "white_label":            False,
        "sla_guarantee":          None,
        "support_tier":           "community",
        "support_sla_sev1_hrs":   None,
    },
}


# ─── Schemas ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: PlanTier
    billing_cycle: str = "yearly"           # Default to annual — aligns with flat license model
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionResponse(BaseModel):
    workspace_id: str
    plan: str
    plan_display_name: str
    status: str
    billing_cycle: str
    amount_cents: Optional[int]
    currency: str
    current_period_end: Optional[str]
    trial_end: Optional[str]
    trial_days_remaining: Optional[int]
    limits: dict
    features: dict


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans():
    """Return all available plans (public endpoint — no auth required)."""
    return {"plans": [FREE_PLAN] + [PLANS[k] for k in ("starter", "pro", "enterprise")]}


@router.get("/current", response_model=SubscriptionResponse)
async def current_subscription(
    license_status: LicenseStatus = Depends(require_active_license),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current workspace subscription and license status."""
    sub = db.query(Subscription).filter(
        Subscription.workspace_id == current_user.workspace_id
    ).first()

    plan_info = PLANS.get(license_status.tier, FREE_PLAN)

    return SubscriptionResponse(
        workspace_id=current_user.workspace_id,
        plan=license_status.tier,
        plan_display_name=license_status.display_tier,
        status=license_status.state.value,
        billing_cycle=sub.billing_cycle if sub else "yearly",
        amount_cents=int(sub.amount_cents or 0) if sub and sub.amount_cents else None,
        currency=sub.currency if sub else "usd",
        current_period_end=sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
        trial_end=license_status.trial_end.isoformat() if license_status.trial_end else None,
        trial_days_remaining=license_status.days_remaining,
        limits=plan_info.get("limits", {}),
        features=plan_info.get("features", {}),
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for a plan upgrade."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key
    plan_info = PLANS.get(payload.plan.value)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if payload.billing_cycle not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="billing_cycle must be 'monthly' or 'yearly'")
    if not plan_info.get("self_serve_checkout"):
        raise HTTPException(
            status_code=400,
            detail="Enterprise plan requires a scoping call. Contact sales@co2router.com"
        )

    price_key = "price_yearly_cents" if payload.billing_cycle == "yearly" else "price_monthly_cents"
    amount = plan_info[price_key]
    if not amount:
        raise HTTPException(status_code=400, detail="Price not configured for this plan/cycle")

    sub = db.query(Subscription).filter(
        Subscription.workspace_id == current_user.workspace_id
    ).first()

    customer_id = sub.stripe_customer_id if sub and sub.stripe_customer_id else None
    if not customer_id:
        ws = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
        customer = stripe.Customer.create(
            email=current_user.email,
            name=ws.name if ws else current_user.email,
            metadata={"workspace_id": current_user.workspace_id},
        )
        customer_id = customer.id
        if not sub:
            sub = Subscription(
                workspace_id=current_user.workspace_id,
                stripe_customer_id=customer_id,
                plan=PlanTier.STARTER,
                status=SubscriptionStatus.TRIALING,
            )
            db.add(sub)
        else:
            sub.stripe_customer_id = customer_id
        db.commit()

    # Add 14-day trial for Team and Business self-serve checkouts
    trial_days = plan_info.get("trial_days", 0)
    subscription_data = {
        "metadata": {
            "workspace_id": current_user.workspace_id,
            "plan": payload.plan.value,
            "billing_cycle": payload.billing_cycle,
        }
    }
    if trial_days > 0:
        subscription_data["trial_period_days"] = trial_days

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"BYOS AI Router — {plan_info['name']} License",
                    "description": (
                        f"Flat annual license for the BYOS AI control plane. "
                        f"Routing · Cost intelligence · Governance · Security."
                    ),
                },
                "unit_amount": amount,
                "recurring": {
                    "interval": "year" if payload.billing_cycle == "yearly" else "month"
                },
            },
            "quantity": 1,
        }],
        mode="subscription",
        subscription_data=subscription_data,
        success_url=payload.success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=payload.cancel_url,
        metadata={
            "workspace_id": current_user.workspace_id,
            "plan": payload.plan.value,
            "billing_cycle": payload.billing_cycle,
        },
    )
    return CheckoutResponse(checkout_url=session.url, session_id=session.id)


@router.get("/session/{session_id}")
async def check_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Poll Stripe session status after checkout redirect."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe.api_key = settings.stripe_secret_key
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {"status": session.status, "payment_status": session.payment_status}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portal")
async def billing_portal(
    return_url: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for self-service billing management."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe.api_key = settings.stripe_secret_key

    sub = db.query(Subscription).filter(
        Subscription.workspace_id == current_user.workspace_id
    ).first()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found. Complete a checkout first.")

    portal = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url,
    )
    return {"portal_url": portal.url}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """Stripe webhook handler — processes subscription lifecycle events."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    body = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    is_checkout_completed = event_type == "checkout.session.completed"
    is_subscription_checkout = is_checkout_completed and data.get("mode") == "subscription"

    if event_type in ("customer.subscription.updated", "customer.subscription.created") or is_subscription_checkout:
        workspace_id = data.get("metadata", {}).get("workspace_id")
        if not workspace_id and data.get("customer"):
            sub_lookup = db.query(Subscription).filter(
                Subscription.stripe_customer_id == data["customer"]
            ).first()
            if sub_lookup:
                workspace_id = sub_lookup.workspace_id

        if workspace_id:
            sub = db.query(Subscription).filter(
                Subscription.workspace_id == workspace_id
            ).first()
            if not sub:
                sub = Subscription(workspace_id=workspace_id)
                db.add(sub)

            plan_val = data.get("metadata", {}).get("plan", "starter")
            try:
                sub.plan = PlanTier(plan_val)
            except ValueError:
                sub.plan = PlanTier.STARTER

            sub.billing_cycle = data.get("metadata", {}).get("billing_cycle", sub.billing_cycle or "yearly")
            resolved_plan = PLANS.get(sub.plan.value, PLANS["starter"])
            resolved_price_key = "price_yearly_cents" if sub.billing_cycle == "yearly" else "price_monthly_cents"
            resolved_amount = resolved_plan.get(resolved_price_key) or 0
            sub.amount_cents = str(resolved_amount)
            # No monthly_credits in flat license model
            sub.monthly_credits_included = None

            stripe_status = data.get("status", "active")
            status_map = {
                "active":     SubscriptionStatus.ACTIVE,
                "trialing":   SubscriptionStatus.TRIALING,
                "past_due":   SubscriptionStatus.PAST_DUE,
                "canceled":   SubscriptionStatus.CANCELED,
                "incomplete": SubscriptionStatus.INCOMPLETE,
                "paused":     SubscriptionStatus.PAUSED,
            }
            sub.status = status_map.get(stripe_status, SubscriptionStatus.ACTIVE)

            if data.get("customer"):
                sub.stripe_customer_id = data["customer"]
            if data.get("id") and event_type != "checkout.session.completed":
                sub.stripe_subscription_id = data["id"]
            if data.get("current_period_start"):
                sub.current_period_start = datetime.utcfromtimestamp(data["current_period_start"])
            if data.get("current_period_end"):
                sub.current_period_end = datetime.utcfromtimestamp(data["current_period_end"])
            if data.get("trial_end"):
                sub.trial_end = datetime.utcfromtimestamp(data["trial_end"])

            db.commit()

    if event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        if customer_id:
            sub = db.query(Subscription).filter(
                Subscription.stripe_customer_id == customer_id
            ).first()
            if sub:
                sub.status = SubscriptionStatus.CANCELED
                sub.canceled_at = datetime.utcnow()
                db.commit()

    return {"received": True}
