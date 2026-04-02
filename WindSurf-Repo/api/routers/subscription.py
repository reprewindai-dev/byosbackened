"""Subscription and payment API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.user import User
from db.models.subscription import (
    Subscription,
    SubscriptionTier,
    SubscriptionStatus,
    Payment,
    PaymentStatus,
)
from apps.api.deps import get_current_user, get_current_workspace_id
from apps.api.deps_subscription import get_user_subscription
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription", tags=["subscription"])


# Pydantic schemas
class SubscriptionResponse(BaseModel):
    id: str
    tier: str
    status: str
    started_at: datetime
    expires_at: Optional[datetime]
    auto_renew: bool
    days_remaining: int
    is_active: bool

    model_config = {"from_attributes": True}


class CreateSubscriptionRequest(BaseModel):
    tier: SubscriptionTier
    billing_period_days: int = 30  # 7, 30, 90, 365
    payment_method: str = "bitcoin"  # "bitcoin" or "internal" (for testing)


class PaymentResponse(BaseModel):
    id: str
    amount: float
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# Pricing configuration
TIER_PRICING = {
    SubscriptionTier.BASIC: {
        7: 9.99,
        30: 29.99,
        90: 79.99,
        365: 299.99,
    },
    SubscriptionTier.PREMIUM: {
        7: 19.99,
        30: 49.99,
        90: 129.99,
        365: 499.99,
    },
    SubscriptionTier.VIP: {
        7: 39.99,
        30: 99.99,
        90: 249.99,
        365: 999.99,
    },
}


@router.get("/", response_model=Optional[SubscriptionResponse])
async def get_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's subscription."""
    subscription = await get_user_subscription(user, db)
    if not subscription:
        return None

    return SubscriptionResponse(
        id=subscription.id,
        tier=subscription.tier.value,
        status=subscription.status.value,
        started_at=subscription.started_at,
        expires_at=subscription.expires_at,
        auto_renew=subscription.auto_renew,
        days_remaining=subscription.days_remaining(),
        is_active=subscription.is_active(),
    )


@router.post("/create", response_model=Dict)
async def create_subscription(
    request: CreateSubscriptionRequest,
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create a new subscription with Bitcoin payment."""
    # Validate billing period
    if request.billing_period_days not in [7, 30, 90, 365]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid billing period. Must be 7, 30, 90, or 365 days",
        )

    # Get pricing
    if request.tier not in TIER_PRICING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription tier",
        )

    price = TIER_PRICING[request.tier][request.billing_period_days]

    # Cancel existing subscription if any
    existing = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .first()
    )

    if existing:
        existing.status = SubscriptionStatus.CANCELLED
        existing.cancelled_at = datetime.utcnow()

    # Create subscription (pending payment)
    expires_at = datetime.utcnow() + timedelta(days=request.billing_period_days)

    subscription = Subscription(
        user_id=user.id,
        workspace_id=workspace_id,
        tier=request.tier,
        status=SubscriptionStatus.PENDING,  # Pending until payment confirmed
        started_at=datetime.utcnow(),
        expires_at=expires_at,
        price_period=price,
        billing_period_days=request.billing_period_days,
        auto_renew=True,
    )

    db.add(subscription)
    db.flush()

    # Create Bitcoin payment charge
    if request.payment_method == "bitcoin":
        try:
            from core.bitcoin_payments import get_bitcoin_processor

            processor = get_bitcoin_processor()

            charge = await processor.create_charge(
                amount=price,
                currency="USD",
                name=f"{request.tier.value.title()} Subscription",
                description=f"{request.tier.value.title()} subscription - {request.billing_period_days} days",
                metadata={
                    "user_id": user.id,
                    "subscription_id": subscription.id,
                    "tier": request.tier.value,
                    "period_days": request.billing_period_days,
                },
            )

            # Create pending payment record
            payment = Payment(
                user_id=user.id,
                subscription_id=subscription.id,
                workspace_id=workspace_id,
                amount=price,
                currency="USD",
                status=PaymentStatus.PENDING,
                payment_provider="bitcoin",
                provider_payment_id=charge["charge_id"],
                description=f"{request.tier.value.title()} subscription - {request.billing_period_days} days (Bitcoin)",
                metadata_json=json.dumps(charge),
            )

            db.add(payment)
            db.commit()
            db.refresh(subscription)

            await processor.close()

            return {
                "status": "pending_payment",
                "subscription_id": subscription.id,
                "payment_url": charge["payment_url"],
                "charge_id": charge["charge_id"],
                "amount_usd": price,
                "crypto_amount": charge.get("crypto_amount"),
                "crypto_currency": charge.get("crypto_currency", "BTC"),
                "expires_at": charge.get("expires_at"),
                "message": "Please complete Bitcoin payment to activate subscription",
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Bitcoin payment creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create Bitcoin payment: {str(e)}",
            )

    else:
        # Internal/testing payment (for development)
        payment = Payment(
            user_id=user.id,
            subscription_id=subscription.id,
            workspace_id=workspace_id,
            amount=price,
            currency="USD",
            status=PaymentStatus.COMPLETED,
            payment_provider="internal",
            description=f"{request.tier.value.title()} subscription - {request.billing_period_days} days",
            completed_at=datetime.utcnow(),
        )

        subscription.status = SubscriptionStatus.ACTIVE

        db.add(payment)
        db.commit()
        db.refresh(subscription)

        return SubscriptionResponse(
            id=subscription.id,
            tier=subscription.tier.value,
            status=subscription.status.value,
            started_at=subscription.started_at,
            expires_at=subscription.expires_at,
            auto_renew=subscription.auto_renew,
            days_remaining=subscription.days_remaining(),
            is_active=subscription.is_active(),
        )


@router.post("/cancel")
async def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel current subscription (no refund, expires at end of period)."""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found",
        )

    subscription.auto_renew = False
    subscription.cancelled_at = datetime.utcnow()
    # Status remains ACTIVE until expires_at

    db.commit()

    return {
        "status": "success",
        "message": "Subscription cancelled. Access continues until expiration.",
        "expires_at": subscription.expires_at.isoformat(),
    }


@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's payment history."""
    payments = (
        db.query(Payment)
        .filter(
            Payment.user_id == user.id,
        )
        .order_by(Payment.created_at.desc())
        .limit(50)
        .all()
    )

    return [PaymentResponse.model_validate(p) for p in payments]


@router.get("/pricing")
async def get_pricing():
    """Get subscription pricing information."""
    return {
        "tiers": {
            "basic": {
                "name": "Basic",
                "description": "Access to standard content library",
                "pricing": {
                    "7": TIER_PRICING[SubscriptionTier.BASIC][7],
                    "30": TIER_PRICING[SubscriptionTier.BASIC][30],
                    "90": TIER_PRICING[SubscriptionTier.BASIC][90],
                    "365": TIER_PRICING[SubscriptionTier.BASIC][365],
                },
            },
            "premium": {
                "name": "Premium",
                "description": "Full access to premium content and features",
                "pricing": {
                    "7": TIER_PRICING[SubscriptionTier.PREMIUM][7],
                    "30": TIER_PRICING[SubscriptionTier.PREMIUM][30],
                    "90": TIER_PRICING[SubscriptionTier.PREMIUM][90],
                    "365": TIER_PRICING[SubscriptionTier.PREMIUM][365],
                },
            },
            "vip": {
                "name": "VIP",
                "description": "Ultimate access with exclusive content",
                "pricing": {
                    "7": TIER_PRICING[SubscriptionTier.VIP][7],
                    "30": TIER_PRICING[SubscriptionTier.VIP][30],
                    "90": TIER_PRICING[SubscriptionTier.VIP][90],
                    "365": TIER_PRICING[SubscriptionTier.VIP][365],
                },
            },
        },
    }
