"""Subscription and premium access dependencies."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.user import User
from db.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from apps.api.deps import get_current_user
from datetime import datetime, timedelta
from typing import Optional


class AdminSubscription:
    """Virtual subscription for admin users."""

    def __init__(self, user: User):
        self.user_id = user.id
        self.tier = SubscriptionTier.VIP
        self.status = SubscriptionStatus.ACTIVE
        self.expires_at = datetime.utcnow() + timedelta(days=365 * 100)  # 100 years
        self.created_at = datetime.utcnow()
        self.is_admin = True

    def is_active(self) -> bool:
        """Admin subscriptions are always active."""
        return True


async def require_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Subscription:
    """Require an active subscription to access premium content.

    ADMIN USERS (is_superuser=True) have FULL ACCESS without subscription.
    All other users MUST pay/subscribe to access content.
    """
    # ADMIN BYPASS: Full access for superusers
    if user.is_superuser and user.is_active:
        return AdminSubscription(user)

    # Get user's active subscription
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not subscription or not subscription.is_active():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required to access this content. Admin users have full access.",
        )

    return subscription


async def require_premium_tier(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Subscription:
    """Require premium or VIP tier subscription.

    ADMIN USERS (is_superuser=True) have FULL ACCESS without subscription.
    """
    # ADMIN BYPASS: Full access for superusers
    if user.is_superuser and user.is_active:
        return AdminSubscription(user)

    subscription = await require_subscription(user, db)

    if subscription.tier not in [SubscriptionTier.PREMIUM, SubscriptionTier.VIP]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium or VIP subscription required",
        )

    return subscription


async def get_user_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[Subscription]:
    """Get user's subscription (if any), doesn't require active subscription.

    ADMIN USERS (is_superuser=True) get virtual VIP subscription for full access.
    """
    # ADMIN BYPASS: Return virtual VIP subscription for admins
    if user.is_superuser and user.is_active:
        return AdminSubscription(user)

    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )
