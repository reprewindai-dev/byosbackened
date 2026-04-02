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

PLANS = {
    "starter": {
        "name": "Starter",
        "tier": "starter",
        "price_monthly_cents": 2900,
        "price_yearly_cents": 29000,
        "features": {
            "api_calls_per_month": 10000,
            "storage_gb": 10,
            "workspaces": 1,
            "users": 3,
            "ai_providers": ["huggingface"],
            "security_suite": True,
            "audit_logs": True,
            "support": "email",
        },
    },
    "pro": {
        "name": "Pro",
        "tier": "pro",
        "price_monthly_cents": 7900,
        "price_yearly_cents": 79000,
        "features": {
            "api_calls_per_month": 100000,
            "storage_gb": 100,
            "workspaces": 5,
            "users": 15,
            "ai_providers": ["huggingface", "openai", "local"],
            "security_suite": True,
            "audit_logs": True,
            "compliance_reports": True,
            "content_filtering": True,
            "support": "priority_email",
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "tier": "enterprise",
        "price_monthly_cents": 29900,
        "price_yearly_cents": 299000,
        "features": {
            "api_calls_per_month": -1,
            "storage_gb": -1,
            "workspaces": -1,
            "users": -1,
            "ai_providers": ["huggingface", "openai", "local", "custom"],
            "security_suite": True,
            "audit_logs": True,
            "compliance_reports": True,
            "content_filtering": True,
            "age_verification": True,
            "sla": "99.9%",
            "support": "dedicated_slack",
            "custom_domain": True,
        },
    },
}


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
            amount_cents=2900,
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
                "product_data": {"name": f"BYOS AI Backend - {plan_info['name']}"},
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
