"""Security event and threat tracking model."""
from sqlalchemy import Column, String, DateTime, Text, JSON, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class ThreatType(str, enum.Enum):
    MALWARE = "malware"
    PHISHING = "phishing"
    DDOS = "ddos"
    INTRUSION = "intrusion"
    DATA_BREACH = "data_breach"
    ANOMALY = "anomaly"
    BRUTE_FORCE = "brute_force"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CONTENT_VIOLATION = "content_violation"
    API_ABUSE = "api_abuse"


class SecurityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent(Base):
    """Security threat and event model."""

    __tablename__ = "security_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    event_type = Column(String, nullable=False, index=True)
    threat_type = Column(SAEnum(ThreatType), nullable=True, index=True)
    security_level = Column(SAEnum(SecurityLevel), default=SecurityLevel.MEDIUM, nullable=False)

    description = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)

    ai_confidence = Column(Float, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    ai_recommendations = Column(JSON, nullable=True)

    status = Column(String, default="open", nullable=False, index=True)
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    resolution = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
