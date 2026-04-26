"""Stripe subscription management: plans, checkout, webhook, portal."""
import json
import stripe
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, require_admin
from core.config import get_settings
from db.session import get_db
from db.models import Subscription, PlanTier, SubscriptionStatus, Workspace, User

settings = get_settings()
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# ─── Plan catalog ─────────────────────────────────────────────────────────────
# IMPORTANT: These prices MUST stay in sync with the public landing page
# (landing/index.html — pricing section). Any change here without updating
# the page constitutes a billing-disclosure mismatch. See PRICING_TRUTH.md.
#
# Pricing model: monthly OR annual. Annual = monthly × 10 (two months free,
# matches public-page disclaimer language).
#
# Internal enum keys (`starter` / `pro` / `enterprise`) are kept stable to
# avoid a database migration on the PlanTier enum. Display names follow the
# public page: Sovereign · Standard / Pro / Enterprise.

PLANS = {
    "starter": {
        "name": "Sovereign · Standard",
        "tier": "starter",
        "price_monthly_cents":   750_000,   # $7,500.00 / month
        "price_yearly_cents":  7_500_000,   # $75,000.00 / year (2 months free)
        "features": {
            "deployment": "self_host_vpc_or_onprem",
            "source_access": "perpetual",
            "sla_bug_fix_business_days": 14,
            "version_update_cadence": "quarterly",
            "support_channel": "private_discord_async",
            "support": "written_first",
            "compliance_docs": False,
            "pen_test_report": False,
            "white_label_rights": False,
            "custom_feature_commitments": False,
            "priority_engineering_channel": False,
        },
    },
    "pro": {
        "name": "Sovereign · Pro",
        "tier": "pro",
        "price_monthly_cents":  1_800_000,  # $18,000.00 / month
        "price_yearly_cents":  18_000_000,  # $180,000.00 / year (2 months free)
        "features": {
            "deployment": "self_host_vpc_or_onprem",
            "source_access": "perpetual",
            "sla_bug_fix_business_days": 5,
            "version_update_cadence": "monthly",
            "support_channel": "direct_email",
            "support": "24h_first_response",
            "annual_architecture_review": True,
            "white_label_rights": True,
            "compliance_docs": False,
            "pen_test_report": False,
            "custom_feature_commitments": False,
            "priority_engineering_channel": False,
        },
    },
    "enterprise": {
        "name": "Sovereign · Enterprise",
        "tier": "enterprise",
        "price_monthly_cents":  4_500_000,  # $45,000.00 / month
        "price_yearly_cents":  45_000_000,  # $450,000.00 / year (2 months free)
        "features": {
            "deployment": "self_host_vpc_or_onprem",
            "source_access": "perpetual",
            "sla_bug_fix_hours": 24,
            "version_update_cadence": "monthly",
            "support_channel": "priority_engineering",
            "support": "priority_engineering",
            "annual_architecture_review": True,
            "white_label_rights": True,
            "custom_feature_commitments_per_quarter": True,
            "compliance_docs": True,
            "pen_test_report": True,
            "pen_test_retest_on_request": True,
            "procurement_friendly_msa": True,
            "priority_engineering_channel": True,
        },
    },
}

# Acquisition is intentionally NOT a subscription plan. It is a one-time deal
# negotiated outside the self-serve checkout flow ($750,000 IP transfer).
# See landing page section "vii. Engagement" → "Acquisition" tier.


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: PlanTier
    billing_cycle: str = "monthly"
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionResponse(BaseModel):
    workspace_id: str
    plan: str
    status: str
    billing_cycle: str
    amount_cents: int
    currency: str
    current_period_end: Optional[str]
    trial_end: Optional[str]
    features: dict


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans():
    """Return all available plans (public endpoint)."""
    return {"plans": list(PLANS.values())}


@router.get("/current", response_model=SubscriptionResponse)
async def current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current workspace subscription."""
    sub = db.query(Subscription).filter(
        Subscription.workspace_id == current_user.workspace_id
    ).first()
    if not sub:
        plan_info = PLANS["starter"]
        return SubscriptionResponse(
            workspace_id=current_user.workspace_id,
            plan="starter",
            status="trialing",
            billing_cycle="monthly",
            amount_cents=0,  # No implicit free tier — checkout sets the real amount
            currency="usd",
            current_period_end=None,
            trial_end=None,
            features=plan_info["features"],
        )
    plan_info = PLANS.get(sub.plan.value, PLANS["starter"])
    return SubscriptionResponse(
        workspace_id=sub.workspace_id,
        plan=sub.plan.value,
        status=sub.status.value,
        billing_cycle=sub.billing_cycle,
        amount_cents=int(sub.amount_cents),
        currency=sub.currency,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
        trial_end=sub.trial_end.isoformat() if sub.trial_end else None,
        features=plan_info["features"],
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

    price_key = "price_yearly_cents" if payload.billing_cycle == "yearly" else "price_monthly_cents"
    amount = plan_info[price_key]

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

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": plan_info["name"],  # e.g. "Sovereign · Pro"
                    "description": f"Veklom AI operations platform — {plan_info['tier']} tier",
                },
                "unit_amount": amount,
                "recurring": {
                    "interval": "year" if payload.billing_cycle == "yearly" else "month"
                },
            },
            "quantity": 1,
        }],
        mode="subscription",
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
    """Create a Stripe Customer Portal session for self-service billing."""
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

    if event_type in ("checkout.session.completed", "customer.subscription.updated",
                      "customer.subscription.created"):
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

            stripe_status = data.get("status", "active")
            status_map = {
                "active": SubscriptionStatus.ACTIVE,
                "trialing": SubscriptionStatus.TRIALING,
                "past_due": SubscriptionStatus.PAST_DUE,
                "canceled": SubscriptionStatus.CANCELED,
                "incomplete": SubscriptionStatus.INCOMPLETE,
                "paused": SubscriptionStatus.PAUSED,
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

    elif event_type == "customer.subscription.deleted":
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
