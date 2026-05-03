"""Deployment model — multi-region, model-version, canary deployments."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from db.session import Base


class DeploymentStatus(str, enum.Enum):
    """Deployment status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    PROMOTING = "promoting"
    ROLLING_BACK = "rolling_back"


class DeploymentStrategy(str, enum.Enum):
    DIRECT = "direct"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"


class Deployment(Base):
    """Multi-region, versioned model deployment with canary + rollback support."""

    __tablename__ = "deployments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    # Original schema (kept for back-compat).
    region = Column(String, nullable=False, index=True)
    service_type = Column(String, nullable=False)
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.ACTIVE, nullable=False)
    deployed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_health_check = Column(DateTime, nullable=True)

    # Orchestration extensions (added in migration 009).
    name = Column(String, nullable=True)
    slug = Column(String, nullable=True, index=True)
    model_slug = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=True)
    version = Column(String, nullable=True)
    previous_version = Column(String, nullable=True)
    strategy = Column(
        SQLEnum(DeploymentStrategy),
        default=DeploymentStrategy.DIRECT,
        nullable=True,
    )
    traffic_percent = Column(Integer, default=100, nullable=True)
    is_primary = Column(Boolean, default=True, nullable=True)
    health_metrics = Column(JSON, nullable=True)  # {"p95_ms":..,"error_rate":..,"qps":..}
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    promoted_at = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    workspace = relationship("Workspace", back_populates="deployments")
