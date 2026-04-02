"""Audit event model for comprehensive audit logging."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class AuditEventType(str, Enum):
    """Types of audit events."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    
    WORKSPACE_CREATED = "workspace_created"
    WORKSPACE_UPDATED = "workspace_updated"
    WORKSPACE_DELETED = "workspace_deleted"
    
    APP_ENABLED = "app_enabled"
    APP_DISABLED = "app_disabled"
    APP_CONFIG_UPDATED = "app_config_updated"
    
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    
    SSO_CONFIG_UPDATED = "sso_config_updated"
    SSO_LOGIN = "sso_login"
    
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    
    SECURITY_EVENT = "security_event"
    SYSTEM_EVENT = "system_event"


class AuditEventSeverity(str, Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEvent(Base):
    """Comprehensive audit event logging model."""
    
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, index=True)
    
    # Event information
    event_type = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    
    # Actor information
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    actor_type = Column(String(50), nullable=True)  # user, system, api_key
    actor_ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    actor_user_agent = Column(Text, nullable=True)
    
    # Context information
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)
    
    # Event details
    description = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON string for detailed event data
    old_values = Column(Text, nullable=True)  # JSON string for previous state
    new_values = Column(Text, nullable=True)  # JSON string for new state
    
    # Outcome
    success = Column(Boolean, nullable=False)
    status_code = Column(String(10), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Security classification
    severity = Column(String(20), default=AuditEventSeverity.LOW, nullable=False)
    is_sensitive = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    actor_user = relationship("User", foreign_keys=[actor_user_id])
    organization = relationship("Organization")
    workspace = relationship("Workspace")
    
    def __repr__(self):
        return f"<AuditEvent {self.event_type}: {self.action} by {self.actor_user_id}>"
