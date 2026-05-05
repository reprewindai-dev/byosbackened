"""Public status page update subscriptions."""
from sqlalchemy import Column, String, DateTime, Text, Integer
from datetime import datetime
from db.session import Base
import uuid


class StatusSubscription(Base):
    """Subscriber target for public Veklom status updates."""

    __tablename__ = "status_subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    channel = Column(String, nullable=False, index=True)
    target_hash = Column(String, unique=True, nullable=False, index=True)
    target_encrypted = Column(Text, nullable=False)
    target_label = Column(String, nullable=False)

    status = Column(String, default="active", nullable=False, index=True)
    verification_status = Column(String, default="pending", nullable=False, index=True)
    last_delivery_status = Column(String, nullable=True)
    last_delivery_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0, nullable=False)

    source_ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
