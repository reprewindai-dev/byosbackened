"""Live streaming models."""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class LiveStreamStatus(str, enum.Enum):
    """Live stream status."""

    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


class LiveStream(Base):
    """Live streaming session."""

    __tablename__ = "live_streams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    content_id = Column(String, ForeignKey("content.id"), nullable=True)  # Associated content

    # Stream info
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String, nullable=True)

    # Stream URLs
    rtmp_url = Column(String, nullable=True)  # RTMP ingest URL
    stream_key = Column(String, nullable=True)  # Stream key
    playback_url = Column(String, nullable=True)  # HLS/DASH playback URL

    # Status
    status = Column(String, default=LiveStreamStatus.SCHEDULED, nullable=False, index=True)

    # Metrics
    peak_viewers = Column(Integer, default=0, nullable=False)
    current_viewers = Column(Integer, default=0, nullable=False)
    total_views = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    gifts_received = Column(Integer, default=0, nullable=False)  # Virtual gifts
    gems_earned = Column(Integer, default=0, nullable=False)  # Gems earned from this stream

    # Timing
    scheduled_start = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0, nullable=False)

    # Settings
    chat_enabled = Column(Boolean, default=True, nullable=False)
    comments_enabled = Column(Boolean, default=True, nullable=False)
    gifts_enabled = Column(Boolean, default=True, nullable=False)

    # Metadata
    tags_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="live_streams")
    workspace = relationship("Workspace", backref="live_streams")


class LiveStreamViewer(Base):
    """Track live stream viewers."""

    __tablename__ = "live_stream_viewers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    stream_id = Column(String, ForeignKey("live_streams.id"), nullable=False, index=True)
    viewer_user_id = Column(
        String, ForeignKey("users.id"), nullable=True, index=True
    )  # Null for anonymous
    viewer_ip = Column(String, nullable=True)

    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)
    watch_duration_seconds = Column(Integer, default=0, nullable=False)

    # Relationships
    stream = relationship("LiveStream", backref="viewers")
    viewer = relationship("User", backref="viewed_streams")


class LiveStreamGift(Base):
    """Virtual gifts sent during live streams."""

    __tablename__ = "live_stream_gifts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    stream_id = Column(String, ForeignKey("live_streams.id"), nullable=False, index=True)
    sender_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    gift_type = Column(String, nullable=False)  # "rose", "diamond", "crown", etc.
    gift_value = Column(Integer, nullable=False)  # Value in gems
    message = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    stream = relationship("LiveStream", backref="gifts")
    sender = relationship("User", backref="sent_gifts")


class MonthlyLeaderboard(Base):
    """Monthly leaderboard for live streaming."""

    __tablename__ = "monthly_leaderboards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    # Period
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)  # 1-12

    # Scores
    total_score = Column(Integer, default=0, nullable=False, index=True)
    live_sessions_count = Column(Integer, default=0, nullable=False)
    total_live_minutes = Column(Integer, default=0, nullable=False)
    total_viewers = Column(Integer, default=0, nullable=False)
    total_gems_earned = Column(Integer, default=0, nullable=False)
    total_gifts_received = Column(Integer, default=0, nullable=False)

    # Ranking
    rank = Column(Integer, nullable=True, index=True)  # 1, 2, 3, etc.
    reward_claimed = Column(Boolean, default=False, nullable=False)  # Free month claimed

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="leaderboard_entries")
    workspace = relationship("Workspace", backref="leaderboard_entries")

    __table_args__ = ({"extend_existing": True},)
