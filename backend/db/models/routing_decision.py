"""Routing decision model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text, Integer, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class RoutingDecision(Base):
    """Routing decision log."""

    __tablename__ = "routing_decisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    operation_id = Column(String, nullable=True, index=True)  # Links to job/operation
    
    # Input
    operation_type = Column(String, nullable=False)
    constraints_json = Column(Text, nullable=True)  # JSON string
    
    # Decision
    selected_provider = Column(String, nullable=False)
    reasoning = Column(Text, nullable=False)
    expected_cost = Column(Numeric(10, 6), nullable=False)
    expected_quality = Column(Numeric(5, 2), nullable=True)
    expected_latency_ms = Column(Integer, nullable=True)
    
    # Alternatives
    alternatives_json = Column(Text, nullable=True)  # JSON string
    
    # Outcome (recorded after operation)
    actual_cost = Column(Numeric(10, 6), nullable=True)
    actual_quality = Column(Numeric(5, 2), nullable=True)
    actual_latency_ms = Column(Integer, nullable=True)
    
    # Validation
    cost_saved_vs_default = Column(Numeric(10, 6), nullable=True)
    quality_met_threshold = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    actualized_at = Column(DateTime, nullable=True)
