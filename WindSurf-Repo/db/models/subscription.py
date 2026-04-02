"""Subscription and payment models."""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    Float,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from db.session import Base
import uuid
import enum


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration."""

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enumeration."""

    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"
    TRIAL = "trial"
    CANCELED = "canceled"  # Stripe spelling


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Subscription(Base):
    """User subscription model."""

    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    tier = Column(
        SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False, index=True
    )
    status = Column(
        SQLEnum(SubscriptionStatus), default=SubscriptionStatus.PENDING, nullable=False, index=True
    )

    # Dates
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Billing
    price_period = Column(Float, nullable=False, default=0.0)  # Price per billing period
    billing_period_days = Column(Integer, default=30, nullable=False)  # 7, 30, 90, 365
    auto_renew = Column(Boolean, default=True, nullable=False)

    # Payment provider info
    payment_provider = Column(String, nullable=True)  # stripe, paypal, etc.
    payment_provider_subscription_id = Column(String, nullable=True)

    # Stripe-specific fields
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    workspace = relationship("Workspace", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")

    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True

    def days_remaining(self) -> int:
        """Get days remaining in subscription."""
        if not self.expires_at:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)


class Payment(Base):
    """Payment transaction model."""

    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    # Amount and currency
    amount = Column(Float, nullable=False)  # In USD
    currency = Column(String, default="USD", nullable=False)

    # Status
    status = Column(
        SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True
    )

    # Description
    description = Column(String, nullable=True)

    # Payment provider
    payment_provider = Column(String, nullable=False)  # stripe, paypal, bitcoin, etc.
    stripe_payment_intent_id = Column(String, nullable=True, index=True)
    stripe_charge_id = Column(String, nullable=True, index=True)

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="payments")
    user = relationship("User")
    workspace = relationship("Workspace")
