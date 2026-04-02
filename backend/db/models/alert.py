"""System alert model for security and operational notifications."""
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """System and security alerts."""

    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.MEDIUM, nullable=False, index=True)
    alert_type = Column(String, nullable=False, index=True)

    status = Column(String, default="open", nullable=False, index=True)
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)

    source = Column(String, nullable=True)
    details = Column(JSON, default=dict, nullable=False)
    resolution = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
