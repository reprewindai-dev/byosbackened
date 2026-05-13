"""Workspace model (multi-tenant)."""
from sqlalchemy import Column, String, DateTime, Boolean, Text
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

    license_key_id = Column(String, nullable=True, index=True)
    license_key_prefix = Column(String, nullable=True)
    license_tier = Column(String, nullable=True)
    license_issued_at = Column(DateTime, nullable=True)
    license_expires_at = Column(DateTime, nullable=True)
    license_download_url = Column(String, nullable=True)
    industry = Column(String, nullable=False, default="generic", index=True)
    playground_profile = Column(String, nullable=False, default="generic")
    risk_tier = Column(String, nullable=False, default="generic")
    default_policy_pack = Column(String, nullable=True)
    default_demo_scenarios = Column(Text, nullable=True)
    default_evidence_requirements = Column(Text, nullable=True)
    default_blocking_rules = Column(Text, nullable=True)

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
    pipelines = relationship("Pipeline", cascade="all, delete-orphan", foreign_keys="Pipeline.workspace_id")
    pipeline_runs = relationship("PipelineRun", cascade="all, delete-orphan", foreign_keys="PipelineRun.workspace_id")
    invites = relationship(
        "WorkspaceInvite",
        back_populates="workspace",
        cascade="all, delete-orphan",
        foreign_keys="WorkspaceInvite.workspace_id",
    )
    github_repo_selections = relationship(
        "WorkspaceGithubRepoSelection",
        back_populates="workspace",
        cascade="all, delete-orphan",
        foreign_keys="WorkspaceGithubRepoSelection.workspace_id",
    )
