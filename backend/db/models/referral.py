"""Referral tracking model."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db.session import Base


class ReferralStatus(str, enum.Enum):
    PENDING = "pending"
    CONVERTED = "converted"
    EXPIRED = "expired"


class RewardType(str, enum.Enum):
    FREE_MONTH = "free_month"
    CREDIT = "credit"
    TOKENS = "tokens"


class Referral(Base):
    """Tracks referral relationships between users."""

    __tablename__ = "referrals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    referred_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    referral_code = Column(String(32), unique=True, nullable=False, index=True)
    status = Column(
        SAEnum(ReferralStatus),
        default=ReferralStatus.PENDING,
        nullable=False,
        index=True,
    )
    reward_type = Column(
        SAEnum(RewardType), default=RewardType.FREE_MONTH, nullable=False
    )
    reward_value = Column(Integer, default=1, nullable=False)
    converted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    referrer = relationship("User", foreign_keys=[referrer_id])
    referred = relationship("User", foreign_keys=[referred_id])
