"""Transcript model."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class Transcript(Base):
    """Transcript model."""

    __tablename__ = "transcripts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    asset_id = Column(String, ForeignKey("assets.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    language = Column(String, nullable=True)  # e.g., "en", "es"
    provider = Column(String, nullable=False)  # e.g., "local_whisper", "huggingface", "openai"
    metadata_json = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="transcripts")
    asset = relationship("Asset", back_populates="transcripts")
