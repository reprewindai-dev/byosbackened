"""Workspace membership and role models for RBAC."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class WorkspaceRole(str, Enum):
    """Workspace roles with hierarchical permissions."""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class MembershipStatus(str, Enum):
    """Membership status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class WorkspaceMembership(Base):
    """Workspace membership model linking users to workspaces with roles."""
    
    __tablename__ = "workspace_memberships"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # Role and permissions
    role = Column(String, default=WorkspaceRole.MEMBER, nullable=False)
    permissions = Column(Text, nullable=True)  # JSON string for custom permissions
    
    # Status and metadata
    status = Column(String, default=MembershipStatus.ACTIVE, nullable=False)
    invited_by = Column(String, ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime, nullable=True)
    
    # Configuration
    preferences = Column(Text, nullable=True)  # JSON string for user preferences
    notifications = Column(Text, nullable=True)  # JSON string for notification settings
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="workspace_memberships", foreign_keys=[user_id])
    workspace = relationship("Workspace", back_populates="memberships")
    inviter = relationship("User", foreign_keys=[invited_by])
    
    # Unique constraint to prevent duplicate memberships
    __table_args__ = (
        {"schema": None},
    )
    
    def __repr__(self):
        return f"<WorkspaceMembership {self.user_id}@{self.workspace_id} ({self.role})>"
