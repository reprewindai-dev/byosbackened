"""Workspace-scoped GitHub repo selections for governed repo context."""
from datetime import datetime
import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class WorkspaceGithubRepoSelection(Base):
    __tablename__ = "workspace_github_repo_selections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    github_account_id = Column(String, nullable=True, index=True)
    connected_account_id = Column(String, nullable=True, index=True)
    repo_full_name = Column(String, nullable=False, index=True)
    repo_id = Column(BigInteger, nullable=True, index=True)
    default_branch = Column(String, nullable=True)
    permissions_json = Column(Text, nullable=True)
    visibility = Column(String, nullable=True)
    repo_context_scope = Column(String, nullable=False, default="metadata_only")
    allowed_repo_actions_json = Column(Text, nullable=True)
    restricted_repo_actions_json = Column(Text, nullable=True)
    selected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    selected_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="github_repo_selections")
    user = relationship("User")
