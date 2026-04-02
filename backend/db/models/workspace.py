"""Workspace model (multi-tenant)."""
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class Workspace(Base):
    """Workspace (tenant) model."""

    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="workspace", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="workspace", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="workspace", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="workspace", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="workspace", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="workspace", cascade="all, delete-orphan")
    ai_audit_logs = relationship("AIAuditLog", back_populates="workspace", cascade="all, delete-orphan")
    routing_policy = relationship("RoutingPolicy", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    ml_models = relationship("MLModel", back_populates="workspace", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="workspace", cascade="all, delete-orphan")
    routing_strategies = relationship("RoutingStrategy", back_populates="workspace", cascade="all, delete-orphan")
    traffic_patterns = relationship("TrafficPattern", back_populates="workspace", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="workspace", cascade="all, delete-orphan")
    savings_reports = relationship("SavingsReport", back_populates="workspace", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="workspace", cascade="all, delete-orphan")
