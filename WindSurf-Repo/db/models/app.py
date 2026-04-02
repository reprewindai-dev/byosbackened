"""App model (represents applications like TrapMaster Pro, ClipCrafter)."""

from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class App(Base):
    """App model - represents an application (TrapMaster Pro, ClipCrafter, etc.)."""

    __tablename__ = "apps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # e.g., "TrapMaster Pro"
    slug = Column(String, unique=True, nullable=False, index=True)  # e.g., "trapmaster-pro"
    description = Column(String, nullable=True)
    icon_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    config = Column(JSON, nullable=True)  # App-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    app_workspaces = relationship(
        "AppWorkspace", back_populates="app", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<App(id={self.id}, name={self.name}, slug={self.slug})>"
