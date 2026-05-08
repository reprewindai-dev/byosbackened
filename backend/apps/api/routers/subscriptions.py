"""Stripe activation and Operating Reserve management."""
import json
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


def _configure_stripe() -> None:
    """Apply secret key and pinned API version for deterministic Stripe calls."""
    stripe.api_key = settings.stripe_secret_key
    stripe.api_version = settings.stripe_api_version

# ─── Plan catalog ─────────────────────────────────────────────────────────────
# IMPORTANT: Backend activation pricing and landing/dashboard displays must
# stay aligned. Reserve balances are USD-denominated in reserve units
# (1,000 units = $1.00) for exact integer accounting in the existing schema.

RESERVE_UNITS_PER_USD = 1000


def _reserve_units_from_cents(cents: int | str | None) -> int:
    """Convert paid reserve cents into integer reserve units."""
    return int(cents or 0) * RESERVE_UNITS_PER_USD // 100


def _reset_legacy_non_cash_reserve_before_activation(
    db: Session,
    workspace_id: str,
    session_id: str,
) -> None:
    """Remove stale non-cash balances before the first paid reserve credit.

    Older evaluation accounts could have wallet balances from token-era grants
    or endpoint middleware debits. Operating Reserve must only become spendable
    after Stripe-backed activation, so first activation starts from zero and then
    credits the paid reserve portion.
    """
    wallet = db.query(TokenWallet).filter(TokenWallet.workspace_id == workspace_id).first()
    if not wallet or wallet.balance == 0:
        return

    prior_paid_purchase = (
        db.query(TokenTransaction)
        .filter(
            TokenTransaction.workspace_id == workspace_id,
            TokenTransaction.transaction_type == "purchase",
            TokenTransaction.stripe_checkout_session_id.isnot(None),
        )
        .first()
    )
    if prior_paid_purchase:
        return

    balance_before = wallet.balance
    wallet.balance = 0
    wallet.total_credits_purchased = 0
    wallet.total_credits_used = 0
    wallet.monthly_credits_used = 0
    wallet.updated_at = datetime.utcnow()
    db.add(
        TokenTransaction(
            wallet_id=wallet.id,
            workspace_id=workspace_id,
            transaction_type="adjustment",
            amount=-balance_before,
            balance_before=balance_before,
            balance_after=0,
            request_id=f"{session_id}:legacy-reserve-reset",
            description="Legacy non-cash reserve reset before paid activation",
            metadata_json=json.dumps(
                {
                    "reason": "legacy_non_cash_reserve_reset",
                    "source": "workspace_activation",
                    "cash_backed": False,
                }
            ),
        )
    )
    db.flush()

PLANS = {
    "starter": {
        "name": "Founding Activation",
        "tier": "starter",
        "activation_cents": 39_500,
        "minimum_reserve_cents": 15_000,
        "self_serve_checkout": True,
        "monthly_credits_included": 0,
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
        "name": "Standard Activation",
        "tier": "pro",
        "activation_cents": 79_500,
        "minimum_reserve_cents": 30_000,
        "self_serve_checkout": True,
        "monthly_credits_included": 0,
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
        "name": "Regulated Activation",
        "tier": "sovereign",
        "activation_cents": 250_000,
        "minimum_reserve_cents": 250_000,
        "self_serve_checkout": False,
        "monthly_credits_included": 0,
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
        "activation_cents": None,
        "minimum_reserve_cents": None,
        "self_serve_checkout": False,
        "monthly_credits_included": 0,
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
    "name": "Free Evaluation",
    "tier": "free",
    "activation_cents": 0,
    "minimum_reserve_cents": 0,
    "self_serve_checkout": False,
    "monthly_credits_included": 0,
    "free_evaluation_limits": {
        "governed_playground_runs": 15,
        "compare_runs": 3,
        "policy_tests": 20,
        "watermarked_exports": 2,
    },
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
    billing_cycle: str = "activation"
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
        ws = db.query(Workspace).filter(
            Workspace.id == current_user.workspace_id
        ).first()
        if ws and ws.license_tier and ws.license_expires_at and ws.license_expires_at > datetime.utcnow():
            plan_info = PLANS.get(ws.license_tier, FREE_PLAN)
            return SubscriptionResponse(
                workspace_id=current_user.workspace_id,
                plan=ws.license_tier,
                status="trialing",
                billing_cycle="evaluation",
                amount_cents=0,
                currency="usd",
                current_period_end=None,
                trial_end=ws.license_expires_at.isoformat(),
                features=plan_info["features"],
            )

        plan_info = FREE_PLAN
        return SubscriptionResponse(
            workspace_id=current_user.workspace_id,
            plan="free",
            status="active",
            billing_cycle="evaluation",
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
    """Create a one-time Stripe Checkout session for workspace activation."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    _configure_stripe()
    plan_info = PLANS.get(payload.plan.value)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if not plan_info.get("self_serve_checkout"):
        raise HTTPException(status_code=400, detail="Regulated and Enterprise plans require sales-assisted activation")

    activation_cents = int(plan_info.get("activation_cents") or 0)
    minimum_reserve_cents = int(plan_info.get("minimum_reserve_cents") or 0)
    amount = activation_cents + minimum_reserve_cents
    if activation_cents <= 0:
        raise HTTPException(status_code=400, detail="Plan is not available for self-serve activation")

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
                status=SubscriptionStatus.INCOMPLETE,
                billing_cycle="activation",
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
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=payload.success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=payload.cancel_url,
        metadata={
            "workspace_id": current_user.workspace_id,
            "plan": payload.plan.value,
            "billing_cycle": "activation",
            "type": "workspace_activation",
            "activation_cents": str(activation_cents),
            "minimum_reserve_cents": str(minimum_reserve_cents),
            "reserve_units": str(_reserve_units_from_cents(minimum_reserve_cents)),
        },
    )
    return CheckoutResponse(checkout_url=session.url, session_id=session.id)


@router.get("/session/{session_id}")
async def check_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll Stripe session status after checkout redirect and reconcile paid sessions."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    _configure_stripe()
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.get("metadata", {}).get("workspace_id") != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Checkout session does not belong to this workspace")
        applied = False
        if session.status == "complete" and session.payment_status == "paid":
            applied = _apply_paid_checkout_session(db, session)
        return {
            "status": session.status,
            "payment_status": session.payment_status,
            "applied": applied,
        }
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
    _configure_stripe()

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
    if is_checkout_completed:
        _apply_paid_checkout_session(db, data)

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
            resolved_amount = resolved_plan.get("activation_cents") or 0
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

    return {"received": True}


def _apply_paid_checkout_session(db: Session, session) -> bool:
    """Idempotently apply a paid Stripe Checkout session to local state."""
    if session.get("mode") != "payment" or session.get("payment_status") != "paid":
        return False

    metadata = session.get("metadata", {}) or {}
    workspace_id = metadata.get("workspace_id")
    session_id = session.get("id")
    if not workspace_id or not session_id:
        return False

    session_type = metadata.get("type")
    if session_type == "operating_reserve":
        reserve_units = metadata.get("reserve_units") or metadata.get("credits")
        if not reserve_units:
            return False
        existing = db.query(TokenTransaction).filter(
            TokenTransaction.stripe_checkout_session_id == session_id,
            TokenTransaction.transaction_type == "purchase",
        ).first()
        if existing:
            return False
        _credit_token_wallet(
            db,
            workspace_id,
            int(reserve_units),
            stripe_checkout_session_id=session_id,
            stripe_payment_intent_id=session.get("payment_intent"),
        )
        return True

    if session_type == "workspace_activation":
        plan_val = metadata.get("plan", "starter")
        sub = db.query(Subscription).filter(Subscription.workspace_id == workspace_id).first()
        if not sub:
            sub = Subscription(workspace_id=workspace_id)
            db.add(sub)

        if (sub.subscription_metadata or {}).get("activation_session_id") == session_id:
            return False

        try:
            sub.plan = PlanTier(plan_val)
        except ValueError:
            sub.plan = PlanTier.STARTER
        plan_info = PLANS.get(sub.plan.value, PLANS["starter"])
        sub.status = SubscriptionStatus.ACTIVE
        sub.billing_cycle = "activation"
        sub.amount_cents = str(plan_info.get("activation_cents") or 0)
        sub.monthly_credits_included = "0"
        if session.get("customer"):
            sub.stripe_customer_id = session["customer"]
        if session.get("payment_intent"):
            sub.subscription_metadata = {
                **(sub.subscription_metadata or {}),
                "activation_session_id": session_id,
                "activation_payment_intent_id": session.get("payment_intent"),
                "activated_at": datetime.utcnow().isoformat(),
                "minimum_reserve_cents": metadata.get("minimum_reserve_cents", "0"),
                "activation_cents": metadata.get("activation_cents", str(plan_info.get("activation_cents") or 0)),
                "reserve_units": metadata.get("reserve_units", "0"),
            }

        reserve_units = int(metadata.get("reserve_units") or _reserve_units_from_cents(metadata.get("minimum_reserve_cents")))
        if reserve_units > 0:
            existing = db.query(TokenTransaction).filter(
                TokenTransaction.stripe_checkout_session_id == session_id,
                TokenTransaction.transaction_type == "purchase",
            ).first()
            if not existing:
                _reset_legacy_non_cash_reserve_before_activation(db, workspace_id, session_id)
                _credit_token_wallet(
                    db,
                    workspace_id,
                    reserve_units,
                    stripe_checkout_session_id=session_id,
                    stripe_payment_intent_id=session.get("payment_intent"),
                    description="Minimum operating reserve from activation",
                )
            else:
                db.commit()
        else:
            db.commit()
        return True

    return False


def _credit_token_wallet(
    db: Session,
    workspace_id: str,
    credits: int,
    stripe_checkout_session_id: str = None,
    stripe_payment_intent_id: str = None,
    description: str = "Operating reserve funding"
):
    """Credit operating reserve for a workspace."""
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
