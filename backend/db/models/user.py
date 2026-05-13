"""User model."""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid
import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    USER = "user"
    READONLY = "readonly"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(SAEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    github_id = Column(String, nullable=True, index=True)
    github_username = Column(String, nullable=True)
    github_access_token = Column(String, nullable=True)

    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String, nullable=True)
    mfa_recovery_codes_json = Column(Text, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="users")
    sessions = relationship("UserSession", back_populates="user", foreign_keys="UserSession.user_id", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
