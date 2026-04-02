"""Content models for premium platform."""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    Text,
    Float,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class ContentType(str, enum.Enum):
    """Content type enumeration."""

    VIDEO = "video"
    LIVE = "live"
    PHOTO = "photo"


class ContentStatus(str, enum.Enum):
    """Content status enumeration."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    PROCESSING = "processing"


class Content(Base):
    """Content (video) model."""

    __tablename__ = "content"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    # Basic info
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    video_url = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=True)

    # Metadata
    content_type = Column(SQLEnum(ContentType), default=ContentType.VIDEO, nullable=False)
    status = Column(SQLEnum(ContentStatus), default=ContentStatus.DRAFT, nullable=False, index=True)

    # Categories and tags
    category_id = Column(String, ForeignKey("categories.id"), nullable=True, index=True)

    # Source tracking
    source_api = Column(String, nullable=True)  # Which API this came from
    source_id = Column(String, nullable=True)  # Original ID from source
    source_url = Column(String, nullable=True)  # Original URL

    # Engagement metrics
    view_count = Column(Integer, default=0, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)
    favorite_count = Column(Integer, default=0, nullable=False)

    # Quality and metadata
    quality = Column(String, nullable=True)  # HD, 4K, etc.
    tags_json = Column(JSON, nullable=True)  # Array of tag strings
    performers_json = Column(JSON, nullable=True)  # Array of performer names

    # User upload tracking
    uploaded_by_user_id = Column(
        String, ForeignKey("users.id"), nullable=True, index=True
    )  # User who uploaded
    approved_by_admin_id = Column(
        String, ForeignKey("users.id"), nullable=True
    )  # Admin who approved/rejected
    approval_notes = Column(Text, nullable=True)  # Admin notes for approval/rejection
    approval_date = Column(DateTime, nullable=True)  # When approved/rejected

    # Live streaming
    is_live = Column(Boolean, default=False, nullable=False, index=True)
    live_viewers_count = Column(Integer, default=0, nullable=False)
    live_started_at = Column(DateTime, nullable=True)
    live_ended_at = Column(DateTime, nullable=True)
    live_stream_url = Column(String, nullable=True)  # RTMP/WebRTC stream URL
    live_chat_enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    published_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="content")
    category = relationship("Category", back_populates="content")
    tags = relationship("Tag", secondary="content_tags", back_populates="content")
    uploaded_by = relationship(
        "User", foreign_keys=[uploaded_by_user_id], backref="uploaded_content"
    )
    approved_by = relationship(
        "User", foreign_keys=[approved_by_admin_id], backref="approved_content"
    )


class Category(Base):
    """Category model."""

    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    name = Column(String, nullable=False, index=True)
    slug = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(String, ForeignKey("categories.id"), nullable=True)  # For subcategories
    icon = Column(String, nullable=True)
    order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="categories")
    parent = relationship("Category", remote_side=[id], backref="children")
    content = relationship("Content", back_populates="category")


class Tag(Base):
    """Tag model."""

    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    name = Column(String, nullable=False, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    usage_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="tags")
    content = relationship("Content", secondary="content_tags", back_populates="tags")


# Association table for many-to-many relationship
from sqlalchemy import Table

content_tags = Table(
    "content_tags",
    Base.metadata,
    Column("content_id", String, ForeignKey("content.id"), primary_key=True),
    Column("tag_id", String, ForeignKey("tags.id"), primary_key=True),
)
