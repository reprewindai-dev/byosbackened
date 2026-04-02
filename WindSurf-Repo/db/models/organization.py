"""Organization model for multi-tenant support."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class OrganizationStatus(str, Enum):
    """Organization status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Organization(Base):
    """Organization model for multi-tenant architecture."""
    
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Billing information
    billing_email = Column(String(255), nullable=True)
    billing_address = Column(Text, nullable=True)
    tax_id = Column(String(50), nullable=True)
    
    # Configuration
    max_workspaces = Column(String, nullable=True)  # JSON string for config
    max_users = Column(String, nullable=True)  # JSON string for config
    feature_flags = Column(Text, nullable=True)  # JSON string for features
    
    # Status and timestamps
    status = Column(String, default=OrganizationStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    sso_providers = relationship("OrganizationSSOProvider", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Organization {self.name}>"
