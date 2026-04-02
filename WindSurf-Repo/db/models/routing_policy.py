"""Routing policy model."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class RoutingPolicy(Base):
    """Routing policy per workspace."""

    __tablename__ = "routing_policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(
        String, ForeignKey("workspaces.id"), nullable=False, unique=True, index=True
    )
    strategy = Column(
        String, nullable=False
    )  # "cost_optimized", "quality_optimized", "speed_optimized", "hybrid"
    constraints_json = Column(Text, nullable=True)  # JSON string
    enabled = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="routing_policy")
