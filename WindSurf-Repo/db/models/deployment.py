"""Deployment model - track multi-region deployments."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class DeploymentStatus(str, enum.Enum):
    """Deployment status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class Deployment(Base):
    """Multi-region deployment tracking."""

    __tablename__ = "deployments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    region = Column(String, nullable=False, index=True)  # "us-east", "eu-west", "asia-pacific"
    service_type = Column(String, nullable=False)  # "api", "worker"
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.ACTIVE, nullable=False)
    deployed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_health_check = Column(DateTime, nullable=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="deployments")
