"""SCIM models for user provisioning and synchronization."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class SCIMToken(Base):
    """SCIM bearer tokens for external system authentication."""
    
    __tablename__ = "scim_tokens"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # Token information
    name = Column(String(255), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    
    # Configuration
    allowed_operations = Column(Text, nullable=True)  # JSON string for allowed operations
    allowed_attributes = Column(Text, nullable=True)  # JSON string for allowed attributes
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="scim_tokens")
    
    def __repr__(self):
        return f"<SCIMToken {self.name}>"


class SCIMGroup(Base):
    """SCIM groups for role-based synchronization."""
    
    __tablename__ = "scim_groups"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # Group information
    external_id = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # SCIM metadata
    scim_resource_type = Column(String(50), default="Group", nullable=False)
    scim_schema = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="scim_groups")
    members = relationship("SCIMGroupMember", back_populates="group", cascade="all, delete-orphan")
    workspace_roles = relationship("SCIMGroupWorkspaceRole", back_populates="group", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SCIMGroup {self.display_name}>"


class SCIMGroupMember(Base):
    """Membership linking SCIM groups to users."""
    
    __tablename__ = "scim_group_members"

    id = Column(String, primary_key=True, index=True)
    group_id = Column(String, ForeignKey("scim_groups.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Membership information
    external_user_id = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    group = relationship("SCIMGroup", back_populates="members")
    user = relationship("User", back_populates="scim_group_memberships")
    
    def __repr__(self):
        return f"<SCIMGroupMember {self.user_id} in {self.group_id}>"


class SCIMGroupWorkspaceRole(Base):
    """Mapping between SCIM groups and workspace roles."""
    
    __tablename__ = "scim_group_workspace_roles"

    id = Column(String, primary_key=True, index=True)
    group_id = Column(String, ForeignKey("scim_groups.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # Role mapping
    workspace_role = Column(String(50), nullable=False)
    
    # Configuration
    auto_assign = Column(Boolean, default=True, nullable=False)
    auto_remove = Column(Boolean, default=True, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    group = relationship("SCIMGroup", back_populates="workspace_roles")
    workspace = relationship("Workspace")
    
    def __repr__(self):
        return f"<SCIMGroupWorkspaceRole {self.group_id} -> {self.workspace_role}>"
