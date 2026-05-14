"""Signup lead capture for owner-only acquisition analytics."""
from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from db.session import Base


class SignupLead(Base):
    """Signup capture record tied to the created user/workspace."""

    __tablename__ = "signup_leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    workspace_name = Column(String, nullable=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    signup_type = Column(String, nullable=False, default="general", index=True)
    source = Column(String, nullable=False, default="password_register", index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    referer = Column(Text, nullable=True)
    utm_source = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)
    landing_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
