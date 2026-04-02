"""AppWorkspace junction model (links apps to workspaces)."""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class AppWorkspace(Base):
    """AppWorkspace junction model - links apps to workspaces (many-to-many)."""

    __tablename__ = "app_workspaces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active = Column(Boolean, default=True, nullable=False)
    config = Column(JSON, nullable=True)  # Workspace-specific app configuration
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    app = relationship("App", back_populates="app_workspaces")
    workspace = relationship("Workspace", back_populates="app_workspaces")

    # Unique constraint: a workspace can only have one record per app
    __table_args__ = (UniqueConstraint("app_id", "workspace_id", name="uq_app_workspace"),)

    def __repr__(self):
        return (
            f"<AppWorkspace(id={self.id}, app_id={self.app_id}, workspace_id={self.workspace_id})>"
        )
