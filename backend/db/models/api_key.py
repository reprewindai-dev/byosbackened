"""API key model for programmatic access and client authentication."""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class APIKey(Base):
    """API key model for workspace-scoped programmatic access."""

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String, nullable=False)
    key_hash = Column(String, unique=True, nullable=False, index=True)
    key_prefix = Column(String, nullable=False)

    scopes = Column(JSON, default=list, nullable=False)
    rate_limit_per_minute = Column(String, default="60", nullable=False)
    allowed_ips = Column(JSON, default=list, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="api_keys")
    user = relationship("User", back_populates="api_keys")
