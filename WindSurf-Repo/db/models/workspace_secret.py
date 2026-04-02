"""Workspace secret model - encrypted BYOK credentials per workspace."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class WorkspaceSecret(Base):
    """Encrypted secret stored per workspace."""

    __tablename__ = "workspace_secrets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "provider", "secret_name", name="uq_workspace_provider_secret"
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    provider = Column(String, nullable=False, index=True)  # e.g. openai, huggingface, serpapi
    secret_name = Column(String, nullable=False)  # e.g. api_key
    encrypted_value = Column(String, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="secrets")
