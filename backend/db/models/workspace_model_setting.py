"""Workspace model enablement and billing metadata."""
from sqlalchemy import Column, String, DateTime, Boolean, Numeric, ForeignKey
from datetime import datetime
from db.session import Base
import uuid


class WorkspaceModelSetting(Base):
    """Per-workspace AI model configuration."""

    __tablename__ = "workspace_model_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    model_slug = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    bedrock_model_id = Column(String, nullable=False)
    provider = Column(String, nullable=False, default="bedrock")
    enabled = Column(Boolean, default=True, nullable=False)
    connected = Column(Boolean, default=True, nullable=False)
    input_cost_per_1m_tokens = Column(Numeric(10, 6), nullable=False, default=0)
    output_cost_per_1m_tokens = Column(Numeric(10, 6), nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
