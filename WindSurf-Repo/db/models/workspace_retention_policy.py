"""Workspace retention policy model for data management."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class RetentionPolicyType(str, Enum):
    """Types of retention policies."""
    USER_DATA = "user_data"
    AUDIT_LOGS = "audit_logs"
    TRANSCRIPTS = "transcripts"
    EXPORTS = "exports"
    ANALYTICS = "analytics"
    CHAT_MESSAGES = "chat_messages"
    UPLOADS = "uploads"


class RetentionAction(str, Enum):
    """Actions to take when retention period expires."""
    DELETE = "delete"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"


class WorkspaceRetentionPolicy(Base):
    """Workspace retention policy for automated data management."""
    
    __tablename__ = "workspace_retention_policies"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # Policy configuration
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    policy_type = Column(String(50), nullable=False, index=True)
    
    # Retention settings
    retention_days = Column(Integer, nullable=False)
    retention_action = Column(String(20), default=RetentionAction.DELETE, nullable=False)
    
    # Advanced settings
    conditions = Column(Text, nullable=True)  # JSON string for retention conditions
    exceptions = Column(Text, nullable=True)  # JSON string for exceptions
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_default = Column(Boolean, default=False, nullable=False)
    
    # Execution tracking
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0, nullable=False)
    
    # Statistics
    total_processed = Column(Integer, default=0, nullable=False)
    total_deleted = Column(Integer, default=0, nullable=False)
    total_archived = Column(Integer, default=0, nullable=False)
    total_anonymized = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="retention_policies")
    
    def __repr__(self):
        return f"<WorkspaceRetentionPolicy {self.name} ({self.policy_type})>"
