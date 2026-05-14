"""Stripe subscription state model."""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class PlanTier(str, enum.Enum):
    STARTER = "starter"
    PRO = "pro"
    SOVEREIGN = "sovereign"
    ENTERPRISE = "enterprise"

    @property
    def display_name(self) -> str:
        """Public-facing plan name matching veklom.com/pricing."""
        return PLAN_DISPLAY_NAMES.get(self.value, self.value)


PLAN_DISPLAY_NAMES: dict[str, str] = {
    "starter": "Founding",
    "pro": "Standard",
    "sovereign": "Regulated",
    "enterprise": "Enterprise",
}

PLAN_HIERARCHY = ["starter", "pro", "sovereign", "enterprise"]


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    PAUSED = "paused"


class Subscription(Base):
    """Stripe subscription state per workspace."""

    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)

    stripe_customer_id = Column(String, unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String, unique=True, nullable=True, index=True)
    stripe_product_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)

    plan = Column(SAEnum(PlanTier), default=PlanTier.STARTER, nullable=False)
    status = Column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.TRIALING, nullable=False, index=True)

    billing_cycle = Column(String, default="monthly", nullable=False)
    # Default 0 cents — amount_cents is set from checkout/webhook lifecycle.
    # Pricing source of truth lives in apps/api/routers/subscriptions.py.
    amount_cents = Column(String, default="0", nullable=False)
    currency = Column(String, default="usd", nullable=False)
    monthly_credits_included = Column(String, default="0", nullable=False)

    trial_end = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)

    features = Column(JSON, default=dict, nullable=False)
    subscription_metadata = Column(JSON, default=dict, nullable=False)  # Renamed from metadata (SQLAlchemy reserved)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="subscription")
