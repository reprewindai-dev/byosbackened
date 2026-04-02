"""AI audit log model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text, Boolean, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class AIAuditLog(Base):
    """AI audit log - immutable, cryptographically verifiable."""

    __tablename__ = "ai_audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Operation details
    operation_type = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    model = Column(String, nullable=True)
    
    # Data (hashed for integrity)
    input_hash = Column(String, nullable=False)  # SHA-256
    output_hash = Column(String, nullable=False)  # SHA-256
    input_preview = Column(Text, nullable=True)  # First 500 chars (for search)
    output_preview = Column(Text, nullable=True)  # First 500 chars
    
    # Cost (precise)
    cost = Column(Numeric(10, 6), nullable=False)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    
    # Routing
    routing_decision_id = Column(String, ForeignKey("routing_decisions.id"), nullable=True)
    routing_reasoning = Column(Text, nullable=True)
    
    # Compliance
    pii_detected = Column(Boolean, default=False, nullable=False)
    pii_types = Column(JSON, nullable=True)  # List of PII types detected
    sensitive_data_flags = Column(JSON, nullable=True)
    
    # Integrity
    log_hash = Column(String, nullable=False)  # HMAC-SHA256 of entire entry
    previous_log_hash = Column(String, nullable=True)  # Chain logs together
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="ai_audit_logs")
    routing_decision = relationship("RoutingDecision", foreign_keys=[routing_decision_id])
