"""WorkspaceInvite model — pending team-member invitations."""
from __future__ import annotations

import enum
import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import relationship

from db.session import Base


class InviteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


def _gen_token() -> str:
    return secrets.token_urlsafe(32)


def _default_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=7)


class WorkspaceInvite(Base):
    """An invite for a user to join a workspace at a given role."""

    __tablename__ = "workspace_invites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, default="user")
    token = Column(String, nullable=False, unique=True, default=_gen_token, index=True)
    status = Column(
        SAEnum(InviteStatus),
        default=InviteStatus.PENDING,
        nullable=False,
        index=True,
    )
    invited_by = Column(String, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime, default=_default_expiry, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    workspace = relationship("Workspace", back_populates="invites")
