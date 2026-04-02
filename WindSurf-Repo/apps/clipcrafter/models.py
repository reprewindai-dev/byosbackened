"""ClipCrafter database models."""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Numeric, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class ClipCrafterProject(Base):
    """ClipCrafter project model."""

    __tablename__ = "clipcrafter_projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    aspect_ratio = Column(String, nullable=True)  # "16:9", "9:16", "1:1", "4:5"
    resolution = Column(String, nullable=True)  # "1080p", "720p", "4K", etc.
    frame_rate = Column(Integer, nullable=True)  # 24, 30, 60 fps
    duration = Column(Numeric(10, 2), nullable=True)  # Duration in seconds
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    clips = relationship("ClipCrafterClip", back_populates="project", cascade="all, delete-orphan")
    templates = relationship(
        "ClipCrafterTemplate", back_populates="project", cascade="all, delete-orphan"
    )
    renders = relationship(
        "ClipCrafterRender", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ClipCrafterProject(id={self.id}, name={self.name})>"


class ClipCrafterClip(Base):
    """ClipCrafter clip model."""

    __tablename__ = "clipcrafter_clips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = Column(
        String,
        ForeignKey("clipcrafter_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    clip_type = Column(String, nullable=False)  # "video", "image", "text", "audio", "transition"
    file_path = Column(String, nullable=True)  # Path to video/image file in storage
    file_size = Column(Integer, nullable=True)  # File size in bytes
    duration = Column(Numeric(10, 2), nullable=True)  # Duration in seconds
    start_time = Column(Numeric(10, 2), nullable=True)  # Start time in timeline (seconds)
    end_time = Column(Numeric(10, 2), nullable=True)  # End time in timeline (seconds)
    position_x = Column(Integer, nullable=True)  # X position on canvas
    position_y = Column(Integer, nullable=True)  # Y position on canvas
    width = Column(Integer, nullable=True)  # Clip width
    height = Column(Integer, nullable=True)  # Clip height
    opacity = Column(Numeric(5, 2), default=100.0, nullable=False)  # Opacity (0-100)
    volume = Column(Numeric(5, 2), default=100.0, nullable=False)  # Volume (0-100)
    effects = Column(JSON, nullable=True)  # JSON array of effects applied
    transitions = Column(JSON, nullable=True)  # JSON array of transitions
    order = Column(Integer, default=0, nullable=False)  # Clip order in timeline
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("ClipCrafterProject", back_populates="clips")

    def __repr__(self):
        return f"<ClipCrafterClip(id={self.id}, name={self.name}, type={self.clip_type})>"


class ClipCrafterTemplate(Base):
    """ClipCrafter template model."""

    __tablename__ = "clipcrafter_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = Column(
        String, ForeignKey("clipcrafter_projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        String, nullable=True
    )  # "social", "promo", "intro", "outro", "transition", etc.
    thumbnail_path = Column(String, nullable=True)  # Path to thumbnail image
    template_data = Column(JSON, nullable=False)  # JSON structure defining the template
    aspect_ratio = Column(String, nullable=True)  # "16:9", "9:16", "1:1", "4:5"
    duration = Column(Numeric(10, 2), nullable=True)  # Template duration in seconds
    is_public = Column(
        Boolean, default=False, nullable=False
    )  # Public templates available to all workspaces
    is_favorite = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)  # How many times template was used
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("ClipCrafterProject", back_populates="templates")

    def __repr__(self):
        return f"<ClipCrafterTemplate(id={self.id}, name={self.name}, category={self.category})>"


class ClipCrafterRender(Base):
    """ClipCrafter render model."""

    __tablename__ = "clipcrafter_renders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = Column(
        String,
        ForeignKey("clipcrafter_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=True)  # Path to rendered video file in storage
    file_size = Column(Integer, nullable=True)  # File size in bytes
    format = Column(String, nullable=False)  # "mp4", "mov", "webm", "gif"
    resolution = Column(String, nullable=False)  # "1080p", "720p", "4K", etc.
    frame_rate = Column(Integer, nullable=True)  # 24, 30, 60 fps
    quality = Column(String, nullable=True)  # "low", "medium", "high", "ultra"
    status = Column(
        String, default="pending", nullable=False
    )  # "pending", "processing", "completed", "failed"
    progress = Column(Integer, default=0, nullable=False)  # Progress percentage (0-100)
    error_message = Column(Text, nullable=True)
    render_settings = Column(JSON, nullable=True)  # Additional render settings
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("ClipCrafterProject", back_populates="renders")

    def __repr__(self):
        return f"<ClipCrafterRender(id={self.id}, name={self.name}, status={self.status})>"
