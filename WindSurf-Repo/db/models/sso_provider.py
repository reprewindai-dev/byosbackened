"""SSO provider models for organization authentication."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class SSOProviderType(str, Enum):
    """SSO provider types."""
    OIDC = "oidc"
    SAML = "saml"
    LDAP = "ldap"
    OAUTH2 = "oauth2"


class SSOProviderStatus(str, Enum):
    """SSO provider status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"


class OrganizationSSOProvider(Base):
    """SSO provider configuration for organizations."""
    
    __tablename__ = "organization_sso_providers"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Provider information
    name = Column(String(255), nullable=False)
    provider_type = Column(String, default=SSOProviderType.OIDC, nullable=False)
    
    # Configuration
    client_id = Column(String(500), nullable=False)
    client_secret = Column(Text, nullable=False)  # Encrypted
    issuer_url = Column(String(500), nullable=True)
    authorization_endpoint = Column(String(500), nullable=True)
    token_endpoint = Column(String(500), nullable=True)
    userinfo_endpoint = Column(String(500), nullable=True)
    jwks_uri = Column(String(500), nullable=True)
    
    # SAML specific fields
    saml_entity_id = Column(String(500), nullable=True)
    saml_metadata_url = Column(String(500), nullable=True)
    saml_certificate = Column(Text, nullable=True)
    
    # Mapping configuration
    attribute_mapping = Column(Text, nullable=True)  # JSON string for attribute mapping
    role_mapping = Column(Text, nullable=True)  # JSON string for role mapping
    
    # Status and metadata
    status = Column(String, default=SSOProviderStatus.ACTIVE, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    auto_provision = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="sso_providers")
    user_identities = relationship("UserIdentity", back_populates="sso_provider", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OrganizationSSOProvider {self.name} ({self.provider_type})>"


class UserIdentity(Base):
    """User identity linking external SSO accounts to internal users."""
    
    __tablename__ = "user_identities"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    sso_provider_id = Column(String, ForeignKey("organization_sso_providers.id"), nullable=False, index=True)
    
    # External identity information
    external_id = Column(String(500), nullable=False, index=True)
    external_email = Column(String(255), nullable=True)
    external_username = Column(String(255), nullable=True)
    external_name = Column(String(500), nullable=True)
    
    # Metadata
    attributes = Column(Text, nullable=True)  # JSON string for additional attributes
    last_authenticated_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="identities")
    sso_provider = relationship("OrganizationSSOProvider", back_populates="user_identities")
    
    def __repr__(self):
        return f"<UserIdentity {self.external_id} -> {self.user_id}>"
