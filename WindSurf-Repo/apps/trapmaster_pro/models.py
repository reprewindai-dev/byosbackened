"""TrapMaster Pro database models."""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class TrapMasterProject(Base):
    """TrapMaster Pro project model."""

    __tablename__ = "trapmaster_projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    bpm = Column(Integer, nullable=True)  # Beats per minute
    key = Column(String, nullable=True)  # Musical key (e.g., "C", "Am")
    time_signature = Column(String, nullable=True)  # e.g., "4/4", "3/4"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tracks = relationship("TrapMasterTrack", back_populates="project", cascade="all, delete-orphan")
    samples = relationship(
        "TrapMasterSample", back_populates="project", cascade="all, delete-orphan"
    )
    exports = relationship(
        "TrapMasterExport", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TrapMasterProject(id={self.id}, name={self.name})>"


class TrapMasterTrack(Base):
    """TrapMaster Pro track model."""

    __tablename__ = "trapmaster_tracks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = Column(
        String, ForeignKey("trapmaster_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    track_type = Column(String, nullable=False)  # "audio", "midi", "instrument"
    file_path = Column(String, nullable=True)  # Path to audio file in storage
    file_size = Column(Integer, nullable=True)  # File size in bytes
    duration = Column(Numeric(10, 2), nullable=True)  # Duration in seconds
    volume = Column(Numeric(5, 2), default=100.0, nullable=False)  # Volume level (0-100)
    pan = Column(Numeric(5, 2), default=0.0, nullable=False)  # Pan position (-100 to 100)
    is_muted = Column(Boolean, default=False, nullable=False)
    is_solo = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)  # Track order in project
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("TrapMasterProject", back_populates="tracks")

    def __repr__(self):
        return f"<TrapMasterTrack(id={self.id}, name={self.name}, type={self.track_type})>"


class TrapMasterSample(Base):
    """TrapMaster Pro sample model."""

    __tablename__ = "trapmaster_samples"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = Column(
        String, ForeignKey("trapmaster_projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)  # "kick", "snare", "hihat", "bass", "melody", etc.
    file_path = Column(String, nullable=False)  # Path to sample file in storage
    file_size = Column(Integer, nullable=True)  # File size in bytes
    duration = Column(Numeric(10, 2), nullable=True)  # Duration in seconds
    bpm = Column(Integer, nullable=True)  # Sample BPM
    key = Column(String, nullable=True)  # Sample key
    tags = Column(Text, nullable=True)  # Comma-separated tags
    is_favorite = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("TrapMasterProject", back_populates="samples")

    def __repr__(self):
        return f"<TrapMasterSample(id={self.id}, name={self.name}, category={self.category})>"


class TrapMasterExport(Base):
    """TrapMaster Pro export model."""

    __tablename__ = "trapmaster_exports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = Column(
        String, ForeignKey("trapmaster_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=True)  # Path to exported file in storage
    file_size = Column(Integer, nullable=True)  # File size in bytes
    format = Column(String, nullable=False)  # "wav", "mp3", "flac", "aac"
    quality = Column(String, nullable=True)  # "low", "medium", "high", "lossless"
    status = Column(
        String, default="pending", nullable=False
    )  # "pending", "processing", "completed", "failed"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("TrapMasterProject", back_populates="exports")

    def __repr__(self):
        return f"<TrapMasterExport(id={self.id}, name={self.name}, status={self.status})>"
