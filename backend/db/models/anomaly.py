"""Anomaly model - store detected anomalies."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class AnomalySeverity(str, enum.Enum):
    """Anomaly severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, enum.Enum):
    """Anomaly types."""
    
    COST_SPIKE = "cost_spike"
    TRAFFIC_SPIKE = "traffic_spike"
    QUALITY_DEGRADATION = "quality_degradation"
    LATENCY_SPIKE = "latency_spike"
    FAILURE_RATE_INCREASE = "failure_rate_increase"
    UNUSUAL_PATTERN = "unusual_pattern"


class AnomalyStatus(str, enum.Enum):
    """Anomaly status."""
    
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    REMEDIATED = "remediated"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


class Anomaly(Base):
    """Detected anomaly record."""
    
    __tablename__ = "anomalies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)  # Nullable for system-wide anomalies
    
    # Anomaly details
    anomaly_type = Column(SQLEnum(AnomalyType), nullable=False)
    severity = Column(SQLEnum(AnomalySeverity), nullable=False)
    status = Column(SQLEnum(AnomalyStatus), default=AnomalyStatus.DETECTED, nullable=False)
    
    # Detection metadata
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    detected_by = Column(String, nullable=False, default="anomaly_detector")  # ML model or system
    confidence_score = Column(String, nullable=True)  # ML confidence (0-1)
    
    # Anomaly data
    description = Column(Text, nullable=False)
    anomaly_metadata = Column(JSON, nullable=True)  # Additional context data (renamed from metadata - SQLAlchemy reserved word)
    
    # Metrics
    baseline_value = Column(String, nullable=True)  # Normal value
    actual_value = Column(String, nullable=True)    # Anomalous value
    deviation_percent = Column(String, nullable=True)  # How much deviation
    
    # Remediation
    remediated_at = Column(DateTime, nullable=True)
    remediation_action = Column(Text, nullable=True)
    remediation_result = Column(Text, nullable=True)
    
    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)  # User or system
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="anomalies")
