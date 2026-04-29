"""Stripe subscription management: plans, checkout, webhook, portal."""
import stripe
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from db.session import get_db
from db.models import Subscription, PlanTier, SubscriptionStatus, Workspace, User, TokenWallet, TokenTransaction

settings = get_settings()
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# ─── Plan catalog ─────────────────────────────────────────────────────────────
# IMPORTANT: Backend subscription pricing and landing/dashboard displays must
# stay aligned. Token packs are separate one-time purchases handled by the
# wallet router.

PLANS = {
    "starter": {
        "name": "Starter",
        "tier": "starter",
        "price_monthly_cents": 9_900,       # $99.00 / month
        "price_yearly_cents": 99_000,       # $990.00 / year
        "self_serve_checkout": True,
        "monthly_credits_included": 10_000_000,
        "features": {
            "api_keys_max": 5,
            "support_channel": "ai_bot",
            "support_response_hours": 0,
            "support_escalation": "email_48h",
            "cost_prediction": "limited",
            "execution": "limited",
            "usage_summary": True,
            "kill_switch": False,
            "compliance_reports": False,
            "audit_logs_retention_days": 7,
            "advanced_routing": False,
            "advanced_security": False,
            "plugin_execution": False,
            "enterprise_admin": False,
            "sla_guarantee": None,
            "white_label": False,
        },
    },
    "pro": {
        "name": "Pro",
        "tier": "pro",
        "price_monthly_cents": 49_900,      # $499.00 / month
        "price_yearly_cents": 499_000,      # $4,990.00 / year
        "self_serve_checkout": True,
        "monthly_credits_included": 100_000_000,
        "features": {
            "api_keys_max": 20,
            "support_channel": "ai_bot_priority",
            "support_response_hours": 0,
            "support_escalation": "email_24h",
            "cost_prediction": True,
            "routing_select": True,
            "savings_insights": True,
            "budget_management": True,
            "performance_metrics": True,
            "alerts": True,
            "content_scan": "text",
            "audit_logs_retention_days": 30,
            "kill_switch": False,
            "compliance_reports": False,
            "advanced_security": False,
            "plugin_execution": False,
            "sla_guarantee": None,
            "white_label": False,
        },
    },
    "sovereign": {
        "name": "Sovereign",
        "tier": "sovereign",
        "price_monthly_cents": 250_000,     # $2,500.00 / month
        "price_yearly_cents": 2_500_000,    # $25,000.00 / year
        "self_serve_checkout": True,
        "monthly_credits_included": 500_000_000,
        "features": {
            "api_keys_max": 100,
            "support_channel": "ai_bot_priority",
            "support_response_hours": 0,
            "support_escalation": "priority_8h",
            "kill_switch": True,
            "audit_logs": True,
            "audit_verification": True,
            "compliance_checks": True,
            "compliance_reports": True,
            "privacy_workflows": True,
            "explainability": True,
            "detailed_health": True,
            "threat_stats": True,
            "security_controls": True,
            "content_scan": "full",
            "content_logs": True,
            "governed_execution": True,
            "audit_exports": True,
            "plugin_execution": True,
            "sla_guarantee": "99.9%",
            "white_label": True,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "tier": "enterprise",
        "price_monthly_cents": None,
        "price_yearly_cents": None,
        "self_serve_checkout": False,
        "monthly_credits_included": None,
        "features": {
            "api_keys_max": None,            # Unlimited
            "support_channel": "ai_bot_dedicated",
            "support_response_hours": 0,
            "support_escalation": "dedicated_4h",
            "kill_switch": True,
            "audit_logs": True,
            "audit_verification": True,
            "compliance_checks": True,
            "compliance_reports": True,
            "privacy_workflows": True,
            "explainability": True,
            "detailed_health": True,
            "threat_stats": True,
            "security_controls": True,
            "content_scan": "full",
            "content_logs": True,
            "governed_execution": True,
            "audit_exports": True,
            "plugin_execution": True,
            "custom_endpoints": True,
            "custom_training": True,
            "workspace_admin": True,
            "advanced_security": True,
            "custom_routing": True,
            "private_deployment": True,
            "sla_guarantee": "99.99%",
            "white_label": True,
            "annual_review": True,
        },
    },
}

# Free tier is handled outside Stripe subscription checkout.
FREE_PLAN = {
    "name": "Free",
    "tier": "free",
    "price_monthly_cents": 0,
    "price_yearly_cents": 0,
    "self_serve_checkout": False,
    "monthly_credits_included": 50_000,
    "features": {
        "view_marketplace": True,
        "comment": True,
        "ask_questions": True,
        "api_keys_max": 1,
        "download_free_tools": True,
        "support_channel": "community",
        "support_response_hours": None,
        "kill_switch": False,
        "compliance_reports": False,
        "advanced_routing": False,
        "advanced_security": False,
        "plugin_execution": False,
        "enterprise_admin": False,
        "sla_guarantee": None,
    },
}

# Strategic transfer transactions are intentionally NOT a subscription plan.
# They are negotiated privately outside of self-serve checkout.


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
    public_keys = ("starter", "pro", "sovereign", "enterprise")
    return {"plans": [FREE_PLAN] + [PLANS[k] for k in public_keys]}


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
        plan_info = FREE_PLAN
        return SubscriptionResponse(
            workspace_id=current_user.workspace_id,
            plan="free",
            status="active",
            billing_cycle="monthly",
            amount_cents=0,
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
        amount_cents=int(sub.amount_cents or 0),
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
    if payload.billing_cycle not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="Invalid billing cycle")
    if not plan_info.get("self_serve_checkout"):
        raise HTTPException(status_code=400, detail="Enterprise plan requires sales-assisted checkout")

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

            sub.billing_cycle = data.get("metadata", {}).get("billing_cycle", sub.billing_cycle or "monthly")
            resolved_plan = PLANS.get(sub.plan.value, PLANS["starter"])
            resolved_price_key = "price_yearly_cents" if sub.billing_cycle == "yearly" else "price_monthly_cents"
            resolved_amount = resolved_plan.get(resolved_price_key) or 0
            sub.amount_cents = str(resolved_amount)
            sub.monthly_credits_included = str(resolved_plan.get("monthly_credits_included") or 0)

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

    if event_type == "checkout.session.completed":
        # Handle token pack purchases (one-time payments)
        session = data
        if session.get("mode") == "payment":
            workspace_id = session.get("metadata", {}).get("workspace_id")
            credits = session.get("metadata", {}).get("credits")
            if workspace_id and credits:
                _credit_token_wallet(
                    db, workspace_id, int(credits),
                    stripe_checkout_session_id=session.get("id"),
                    stripe_payment_intent_id=session.get("payment_intent")
                )

    return {"received": True}


def _credit_token_wallet(
    db: Session,
    workspace_id: str,
    credits: int,
    stripe_checkout_session_id: str = None,
    stripe_payment_intent_id: str = None,
    description: str = "Token pack purchase"
):
    """Credit token wallet for a workspace."""
    # Get or create wallet
    wallet = db.query(TokenWallet).filter(
        TokenWallet.workspace_id == workspace_id
    ).first()
    
    if not wallet:
        wallet = TokenWallet(
            workspace_id=workspace_id,
            balance=0
        )
        db.add(wallet)
        db.flush()
    
    # Record transaction
    balance_before = wallet.balance
    balance_after = balance_before + credits
    
    transaction = TokenTransaction(
        wallet_id=wallet.id,
        workspace_id=workspace_id,
        transaction_type="purchase",
        amount=credits,
        balance_before=balance_before,
        balance_after=balance_after,
        stripe_checkout_session_id=stripe_checkout_session_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        description=description
    )
    db.add(transaction)
    
    # Update wallet
    wallet.balance = balance_after
    wallet.total_credits_purchased = (wallet.total_credits_purchased or 0) + credits
    wallet.updated_at = datetime.utcnow()
    
    db.commit()
    return wallet
