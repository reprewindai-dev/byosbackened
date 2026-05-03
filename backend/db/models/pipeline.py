"""Pipeline + PipelineVersion + PipelineRun models — governed multi-step LLM workflows."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from db.session import Base


class PipelineStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED_POLICY = "blocked_policy"


class Pipeline(Base):
    """A versioned, governed execution pipeline (DAG of prompt/tool/condition nodes)."""

    __tablename__ = "pipelines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    slug = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(PipelineStatus), default=PipelineStatus.DRAFT, nullable=False, index=True)
    current_version = Column(Integer, default=1, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    versions = relationship(
        "PipelineVersion",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="PipelineVersion.version.desc()",
    )
    runs = relationship(
        "PipelineRun",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="PipelineRun.created_at.desc()",
    )


class PipelineVersion(Base):
    """An immutable version of a pipeline definition (DAG)."""

    __tablename__ = "pipeline_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(String, ForeignKey("pipelines.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    # graph: {"nodes": [{"id","type","model","prompt","tool","policy"}], "edges": [{"from","to"}]}
    graph = Column(JSON, nullable=False)
    # policy refs applied to all runs of this version
    policy_refs = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    pipeline = relationship("Pipeline", back_populates="versions")


class PipelineRun(Base):
    """A single execution of a pipeline version."""

    __tablename__ = "pipeline_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(String, ForeignKey("pipelines.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    triggered_by = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(
        SAEnum(PipelineRunStatus),
        default=PipelineRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    inputs = Column(JSON, nullable=True)
    outputs = Column(JSON, nullable=True)
    # per-step trace: [{"node_id","provider","model","latency_ms","tokens","cost_usd","status"}]
    step_trace = Column(JSON, nullable=True)
    total_cost_usd = Column(String, nullable=True)  # decimal-as-string for SQLite portability
    total_latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    pipeline = relationship("Pipeline", back_populates="runs")
