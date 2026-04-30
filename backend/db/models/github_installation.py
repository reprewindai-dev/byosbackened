"""GitHub app installations per vendor."""
from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class GithubInstallation(Base):
    __tablename__ = "github_installations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    github_installation_id = Column(BigInteger, nullable=False, unique=True, index=True)
    github_account_login = Column(String, nullable=True)
    github_account_type = Column(String, nullable=True)
    installed_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    permissions_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor")
    workspace = relationship("Workspace")
    installed_by = relationship("User")
    repos = relationship("GithubRepo", back_populates="installation", cascade="all, delete-orphan")


class GithubRepo(Base):
    __tablename__ = "github_repos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    installation_id = Column(String, ForeignKey("github_installations.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    github_repo_id = Column(BigInteger, nullable=False, unique=True, index=True)
    owner_login = Column(String, nullable=True)
    repo_name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    private = Column(String, nullable=True)
    default_branch = Column(String, nullable=True)
    html_url = Column(String, nullable=True)
    selected_for_marketplace = Column(String, nullable=True, default="false")
    last_synced_at = Column(DateTime, nullable=True)
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor")
    installation = relationship("GithubInstallation", back_populates="repos")
    workspace = relationship("Workspace")
