"""Privacy-safe product usage telemetry."""
from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from db.session import Base


class ProductUsageEvent(Base):
    """Behavioral product analytics without storing customer workspace content."""

    __tablename__ = "product_usage_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    surface = Column(String, nullable=True, index=True)
    route = Column(String, nullable=True, index=True)
    feature = Column(String, nullable=True, index=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    metadata_json = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
