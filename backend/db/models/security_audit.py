"""Security audit log model."""
from sqlalchemy import Column, String, DateTime, Text, Boolean
from datetime import datetime
from db.session import Base
import uuid


class SecurityAuditLog(Base):
    """Security audit log - logs all security events."""

    __tablename__ = "security_audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, nullable=True, index=True)  # Nullable for system events
    user_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # login, logout, permission_change, etc.
    event_category = Column(String, nullable=False)  # authentication, authorization, data_access, etc.
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    failure_reason = Column(String, nullable=True)
    details = Column(Text, nullable=True)  # JSON string for additional details
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
