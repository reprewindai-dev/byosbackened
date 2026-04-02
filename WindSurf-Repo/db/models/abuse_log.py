"""Abuse log model."""

from sqlalchemy import Column, String, DateTime, Text, Boolean
from datetime import datetime
from db.session import Base
import uuid


class AbuseLog(Base):
    """Abuse attempt log."""

    __tablename__ = "abuse_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True, index=True)
    abuse_type = Column(String, nullable=False)  # "rate_limit", "content_filter", "anomaly"
    severity = Column(String, nullable=False)  # "low", "medium", "high"
    reason = Column(Text, nullable=False)
    blocked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
