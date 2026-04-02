"""Stripe billing - checkout sessions, subscriptions, portal. NO WEBHOOKS - polling only."""

import stripe
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.user import User
from db.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus, Payment, PaymentStatus
from apps.api.deps import get_current_user, get_current_workspace_id
from core.config import get_settings
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/stripe", tags=["stripe-billing"])

# Configure Stripe API key
stripe.api_key = settings.stripe_secret_key or ""

# ─── Stripe product catalog ───────────────────────────────────────────────────
# These are the BYOS product tiers. Prices in cents.
BYOS_PLANS = {
    "starter": {
        "name": "BYOS Starter",
        "description": "AI backend for individuals - 10K requests/month, 3 providers",
        "price_monthly": 2900,   # $29/mo
        "price_yearly": 29000,   # $290/yr (2 months free)
        "tier": SubscriptionTier.BASIC,
        "features": ["10,000 AI requests/month", "3 AI providers", "Cost Intelligence", "Basic Routing"],
    },
    "pro": {
        "name": "BYOS Pro",
        "description": "AI backend for teams - 100K requests/month, all providers",
        "price_monthly": 7900,   # $79/mo
        "price_yearly": 79000,   # $790/yr
        "tier": SubscriptionTier.PREMIUM,
        "features": ["100,000 AI requests/month", "All AI providers", "Anomaly Detection", "Budget Guardrails", "Priority Support"],
    },
    "enterprise": {
        "name": "BYOS Enterprise",
        "description": "Unlimited AI backend with SLA",
        "price_monthly": 29900,  # $299/mo
        "price_yearly": 299000,  # $2990/yr
        "tier": SubscriptionTier.VIP,
        "features": ["Unlimited requests", "Dedicated infrastructure", "Custom models", "SLA guarantee", "White-glove onboarding"],
    },
}


def ensure_stripe_key():
    """Ensure Stripe API key is configured."""
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured. Set STRIPE_SECRET_KEY.")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CheckoutSessionRequest(BaseModel):
    plan: str  # "starter", "pro", "enterprise"
    billing_period: str = "monthly"  # "monthly" or "yearly"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    plan: str
    amount: int
    currency: str


class SubscriptionStatusResponse(BaseModel):
    active: bool
    plan: Optional[str]
    status: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]


class BillingPortalResponse(BaseModel):
    portal_url: str


class PlanResponse(BaseModel):
    id: str
    name: str
    description: str
    price_monthly: int
    price_yearly: int
    features: List[str]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans():
    """List all available BYOS subscription plans."""
    return [
        PlanResponse(id=plan_id, **{k: v for k, v in plan.items() if k != "tier"})
        for plan_id, plan in BYOS_PLANS.items()
    ]


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout Session. User pays on Stripe's hosted page.
    Frontend polls /stripe/session/{session_id} to confirm payment."""
    ensure_stripe_key()
    
    if request.plan not in BYOS_PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {request.plan}. Choose: {list(BYOS_PLANS.keys())}")

    plan = BYOS_PLANS[request.plan]
    amount = plan["price_yearly"] if request.billing_period == "yearly" else plan["price_monthly"]
    interval = "year" if request.billing_period == "yearly" else "month"

    try:
        # Get or create Stripe customer
        # Check if workspace has existing stripe_customer_id
        existing_sub = db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id,
            Subscription.stripe_customer_id.isnot(None),
        ).first()

        stripe_customer_id = None
        if existing_sub and existing_sub.stripe_customer_id:
            stripe_customer_id = existing_sub.stripe_customer_id
        else:
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.email,
                metadata={"workspace_id": workspace_id, "user_id": user.id},
            )
            stripe_customer_id = customer.id

        # Create price on the fly
        price = stripe.Price.create(
            unit_amount=amount,
            currency="usd",
            recurring={"interval": interval},
            product_data={"name": plan["name"]},
            metadata={"plan": request.plan, "workspace_id": workspace_id},
        )

        # Create checkout session
        base_url = settings.frontend_url
        success_url = request.success_url or f"{base_url}/settings?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.cancel_url or f"{base_url}/settings?payment=cancelled"

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=stripe_customer_id,
            line_items=[{"price": price.id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={
                "metadata": {"workspace_id": workspace_id, "plan": request.plan},
            },
            metadata={"workspace_id": workspace_id, "plan": request.plan},
            allow_promotion_codes=True,
            billing_address_collection="auto",
        )

        return CheckoutSessionResponse(
            session_id=session.id,
            checkout_url=session.url,
            plan=request.plan,
            amount=amount,
            currency="usd",
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


@router.get("/session/{session_id}")
async def poll_checkout_session(
    session_id: str,
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Poll Stripe Checkout Session status. Frontend calls this after redirect from Stripe.
    When payment_status == 'paid', subscription is activated in DB."""
    ensure_stripe_key()
    
    try:
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["subscription"]
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    payment_status = session.payment_status  # "paid", "unpaid", "no_payment_required"
    plan_id = session.metadata.get("plan", "starter") if session.metadata else "starter"
    plan = BYOS_PLANS.get(plan_id, BYOS_PLANS["starter"])

    # If paid, activate/update subscription in DB
    if payment_status == "paid":
        stripe_sub = session.subscription
        stripe_sub_id = stripe_sub if isinstance(stripe_sub, str) else (stripe_sub.id if stripe_sub else None)
        stripe_customer_id = session.customer

        # Determine expiry
        expires_at = datetime.utcnow() + timedelta(days=365 if request.billing_period == "yearly" else 30)
        if stripe_sub and isinstance(stripe_sub, str):
            # Expand subscription if needed
            stripe_sub = stripe.Subscription.retrieve(stripe_sub)
        
        if stripe_sub and hasattr(stripe_sub, 'current_period_end'):
            expires_at = datetime.utcfromtimestamp(stripe_sub.current_period_end)

        # Check existing sub
        sub = db.query(Subscription).filter(
            Subscription.workspace_id == workspace_id,
        ).first()

        if sub:
            sub.tier = plan["tier"]
            sub.status = SubscriptionStatus.ACTIVE
            sub.stripe_customer_id = stripe_customer_id
            sub.stripe_subscription_id = stripe_sub_id
            sub.expires_at = expires_at
            sub.auto_renew = True
            sub.payment_provider = "stripe"
            sub.payment_provider_subscription_id = stripe_sub_id
        else:
            sub = Subscription(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                user_id=user.id,
                tier=plan["tier"],
                status=SubscriptionStatus.ACTIVE,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_sub_id,
                started_at=datetime.utcnow(),
                expires_at=expires_at,
                auto_renew=True,
                payment_provider="stripe",
                payment_provider_subscription_id=stripe_sub_id,
                price_period=plan["price_monthly"] / 100,
                billing_period_days=30,
            )
            db.add(sub)

        # Record payment
        payment = Payment(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_id=user.id,
            subscription_id=sub.id,
            amount=session.amount_total / 100 if session.amount_total else 0,
            currency=session.currency.upper() if session.currency else "USD",
            status=PaymentStatus.COMPLETED,
            payment_provider="stripe",
            stripe_payment_intent_id=str(getattr(session, 'payment_intent', '') or ''),
            description=f"BYOS {plan_id.title()} subscription",
        )
        db.add(payment)
        db.commit()

    return {
        "session_id": session_id,
        "payment_status": payment_status,
        "plan": plan_id,
        "amount_total": session.amount_total,
        "currency": session.currency,
        "customer_email": session.customer_details.email if session.customer_details else None,
        "subscription_activated": payment_status == "paid",
    }


@router.post("/portal", response_model=BillingPortalResponse)
async def create_billing_portal(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create Stripe Customer Portal session for self-service billing management.
    User can update payment method, cancel, download invoices."""
    ensure_stripe_key()
    
    # Find stripe customer ID
    sub = db.query(Subscription).filter(
        Subscription.workspace_id == workspace_id,
        Subscription.stripe_customer_id.isnot(None),
    ).first()

    if not sub or not sub.stripe_customer_id:
        raise HTTPException(
            status_code=404,
            detail="No Stripe subscription found. Create a subscription first.",
        )

    try:
        base_url = settings.frontend_url

        portal = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=f"{base_url}/settings",
        )

        return BillingPortalResponse(portal_url=portal.url)
    except stripe.error.StripeError as e:
        logger.error(f"Stripe portal error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create portal: {str(e)}")


@router.get("/subscription", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get current subscription status. Syncs with Stripe if stripe_subscription_id exists."""
    ensure_stripe_key()
    
    sub = db.query(Subscription).filter(
        Subscription.workspace_id == workspace_id,
    ).first()

    if not sub:
        return SubscriptionStatusResponse(
            active=False, plan=None, status="none",
            current_period_end=None, cancel_at_period_end=False,
            stripe_customer_id=None, stripe_subscription_id=None,
        )

    # Sync with Stripe if we have an ID
    if sub.stripe_subscription_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
            # Update local status from Stripe
            status_map = {
                "active": SubscriptionStatus.ACTIVE,
                "canceled": SubscriptionStatus.CANCELED,
                "past_due": SubscriptionStatus.EXPIRED,
                "unpaid": SubscriptionStatus.EXPIRED,
                "trialing": SubscriptionStatus.ACTIVE,
            }
            sub.status = status_map.get(stripe_sub.status, sub.status)
            if hasattr(stripe_sub, 'current_period_end'):
                sub.expires_at = datetime.utcfromtimestamp(stripe_sub.current_period_end)
            db.commit()
        except Exception as e:
            logger.warning(f"Stripe sync failed: {e}")

    # Map tier to plan name
    tier_plan_map = {
        SubscriptionTier.BASIC: "starter",
        SubscriptionTier.PREMIUM: "pro",
        SubscriptionTier.VIP: "enterprise",
        SubscriptionTier.FREE: "free",
    }

    return SubscriptionStatusResponse(
        active=sub.status == SubscriptionStatus.ACTIVE,
        plan=tier_plan_map.get(sub.tier, str(sub.tier)),
        status=sub.status,
        current_period_end=sub.expires_at.isoformat() if sub.expires_at else None,
        cancel_at_period_end=not sub.auto_renew,
        stripe_customer_id=sub.stripe_customer_id,
        stripe_subscription_id=sub.stripe_subscription_id,
    )


@router.post("/cancel")
async def cancel_subscription(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Cancel Stripe subscription at period end. Does NOT cancel immediately."""
    ensure_stripe_key()
    
    sub = db.query(Subscription).filter(
        Subscription.workspace_id == workspace_id,
    ).first()

    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")

    try:
        if sub.stripe_subscription_id:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=True,
            )

        sub.auto_renew = False
        db.commit()

        return {
            "message": "Subscription will cancel at end of billing period",
            "cancels_at": sub.expires_at.isoformat() if sub.expires_at else None,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe cancel error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to cancel: {str(e)}")


@router.get("/invoices")
async def list_invoices(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List Stripe invoices for this customer."""
    ensure_stripe_key()
    
    sub = db.query(Subscription).filter(
        Subscription.workspace_id == workspace_id,
        Subscription.stripe_customer_id.isnot(None),
    ).first()

    if not sub or not sub.stripe_customer_id:
        return {"invoices": []}

    try:
        invoices = stripe.Invoice.list(customer=sub.stripe_customer_id, limit=20)

        return {
            "invoices": [
                {
                    "id": inv.id,
                    "amount_paid": inv.amount_paid,
                    "currency": inv.currency,
                    "status": inv.status,
                    "created": datetime.utcfromtimestamp(inv.created).isoformat(),
                    "invoice_pdf": inv.invoice_pdf,
                    "hosted_invoice_url": inv.hosted_invoice_url,
                    "description": inv.description or "",
                }
                for inv in invoices.data
            ]
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe invoice error: {e}")
        return {"invoices": [], "error": str(e)}
