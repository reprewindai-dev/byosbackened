"""License key model for server-side entitlement control."""
from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from db.session import Base
from license.tier import LicenseTier


class LicenseKey(Base):
    """Encrypted license record with workspace, tier, and activation binding."""

    __tablename__ = "license_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key_hash = Column(String, unique=True, nullable=False, index=True)
    encrypted_key = Column(Text, nullable=False)
    key_prefix = Column(String, nullable=False, index=True)

    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    tier = Column(SAEnum(LicenseTier), nullable=False, index=True)

    machine_fingerprint = Column(String, nullable=True, index=True)
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)

    active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    grace_until = Column(DateTime, nullable=True, index=True)
    revoked_reason = Column(String, nullable=True)

    activated_at = Column(DateTime, nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    last_verified_at = Column(DateTime, nullable=True)

    license_metadata = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace")
