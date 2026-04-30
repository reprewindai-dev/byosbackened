"""Vendor model for marketplace sellers."""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    display_name = Column(String, nullable=False)
    plan = Column(String, nullable=False, default="verified", index=True)  # verified|sovereign
    subscription_status = Column(String, nullable=False, default="inactive", index=True)  # active|inactive|past_due|canceled
    stripe_account_id = Column(String, nullable=True, index=True)
    is_onboarded = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
    workspace = relationship("Workspace")
    listings = relationship("Listing", back_populates="vendor", cascade="all, delete-orphan")
