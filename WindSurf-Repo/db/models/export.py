"""Export model."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class ExportFormat(str, enum.Enum):
    """Export format enum."""

    JSON = "json"
    CSV = "csv"
    ZIP = "zip"


class Export(Base):
    """Export model."""

    __tablename__ = "exports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True, index=True)
    format = Column(SQLEnum(ExportFormat), nullable=False)
    s3_key = Column(String, nullable=False, unique=True)  # S3 object key
    s3_bucket = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="exports")
