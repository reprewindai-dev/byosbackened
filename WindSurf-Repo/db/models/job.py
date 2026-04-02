"""Job model (for async tasks)."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class JobStatus(str, enum.Enum):
    """Job status enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, enum.Enum):
    """Job type enum."""

    TRANSCRIBE = "transcribe"
    EXPORT = "export"


class Job(Base):
    """Job model for async tasks."""

    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    input_data = Column(String, nullable=True)  # JSON string
    output_data = Column(String, nullable=True)  # JSON string
    error_message = Column(String, nullable=True)

    # Policy enforcement audit fields (BYOS moat)
    requested_provider = Column(String, nullable=True)
    resolved_provider = Column(String, nullable=True)
    policy_id = Column(String, nullable=True)
    policy_version = Column(String, nullable=True)
    policy_enforcement = Column(String, nullable=True)  # strict|fallback
    policy_reason = Column(String, nullable=True)
    was_fallback = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="jobs")
