"""Content filtering and age verification model for privacy-first content platforms."""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Float, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class ContentCategory(str, enum.Enum):
    SAFE = "safe"
    ADULT = "adult"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"


class AgeVerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ContentFilterLog(Base):
    """Log of content filter decisions for audit and compliance."""

    __tablename__ = "content_filter_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    asset_id = Column(String, nullable=True, index=True)
    content_hash = Column(String, nullable=True, index=True)

    category = Column(SAEnum(ContentCategory), nullable=False, default=ContentCategory.SAFE)
    confidence = Column(Float, nullable=True)

    flags = Column(JSON, default=list, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)

    action_taken = Column(String, nullable=False, default="allow")
    blocked_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AgeVerification(Base):
    """Age verification records — privacy-preserving (no raw ID storage)."""

    __tablename__ = "age_verifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    status = Column(SAEnum(AgeVerificationStatus), default=AgeVerificationStatus.UNVERIFIED, nullable=False, index=True)

    verification_method = Column(String, nullable=True)
    verification_token = Column(String, unique=True, nullable=True, index=True)

    verified_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
