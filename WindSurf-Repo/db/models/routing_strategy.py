"""Routing strategy model - store learned routing strategies per workspace."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Numeric, Integer, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class RoutingStrategy(Base):
    """Learned routing strategy per workspace/operation."""

    __tablename__ = "routing_strategies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    operation_type = Column(String, nullable=False, index=True)

    # Learned strategy
    preferred_provider = Column(String, nullable=True)  # Best provider learned
    provider_weights = Column(JSON, nullable=True)  # {provider: weight} for weighted selection
    exploration_rate = Column(
        Numeric(5, 4), nullable=True, default=0.1
    )  # Exploration vs exploitation

    # Strategy metadata
    strategy_type = Column(
        String, nullable=False, default="cost_optimized"
    )  # cost_optimized, quality_optimized, speed_optimized, hybrid
    constraints_json = Column(Text, nullable=True)  # JSON string of constraints

    # Learning metrics
    total_samples = Column(Integer, nullable=False, default=0)
    learning_samples = Column(Integer, nullable=False, default=0)
    best_provider_reward = Column(Numeric(10, 6), nullable=True)

    # Performance metrics
    avg_cost_saved = Column(Numeric(10, 6), nullable=True)
    avg_quality_improvement = Column(Numeric(5, 4), nullable=True)
    avg_latency_reduction_ms = Column(Integer, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="routing_strategies")
