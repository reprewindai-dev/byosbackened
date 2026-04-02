"""User model."""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    # Gamification
    gems = Column(Integer, default=0, nullable=False)  # Gems earned from going live, etc.
    total_live_sessions = Column(Integer, default=0, nullable=False)  # Total times gone live
    total_live_minutes = Column(Integer, default=0, nullable=False)  # Total minutes streamed
    total_live_viewers = Column(
        Integer, default=0, nullable=False
    )  # Total viewers across all streams
    monthly_live_score = Column(
        Integer, default=0, nullable=False, index=True
    )  # Score for monthly leaderboard
    last_month_rank = Column(Integer, nullable=True)  # Last month's leaderboard rank
    free_month_earned = Column(
        Boolean, default=False, nullable=False
    )  # Earned free month from leaderboard

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="users")
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    workspace_memberships = relationship("WorkspaceMembership", back_populates="user", foreign_keys="WorkspaceMembership.user_id")
    identities = relationship("UserIdentity", back_populates="user")
    scim_group_memberships = relationship("SCIMGroupMember", back_populates="user")
