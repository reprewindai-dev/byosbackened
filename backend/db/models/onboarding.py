"""Workspace onboarding progress model."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from db.session import Base


class OnboardingStep(str, enum.Enum):
    CHOOSE_USE_CASE = "choose_use_case"
    CONNECT_MODEL = "connect_model"
    RUN_DEMO = "run_demo"
    INVITE_TEAMMATE = "invite_teammate"


class WorkspaceOnboarding(Base):
    """Tracks onboarding progress per workspace."""

    __tablename__ = "workspace_onboarding"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    use_case = Column(String, nullable=True)
    step_choose_use_case = Column(Boolean, default=False, nullable=False)
    step_connect_model = Column(Boolean, default=False, nullable=False)
    step_run_demo = Column(Boolean, default=False, nullable=False)
    step_invite_teammate = Column(Boolean, default=False, nullable=False)
    completed = Column(Boolean, default=False, nullable=False, index=True)

    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    user = relationship("User", foreign_keys=[user_id])
