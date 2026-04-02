"""Incident log model."""

from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum
from datetime import datetime
from db.session import Base
import uuid
import enum


class IncidentStatus(str, enum.Enum):
    """Incident status."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(str, enum.Enum):
    """Incident severity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentLog(Base):
    """Incident tracking."""

    __tablename__ = "incident_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, nullable=True, index=True)  # Nullable for system-wide incidents
    incident_type = Column(String, nullable=False)  # "security", "system", "compliance"
    severity = Column(SQLEnum(IncidentSeverity), nullable=False)
    status = Column(SQLEnum(IncidentStatus), default=IncidentStatus.OPEN, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
