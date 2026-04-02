"""System performance metrics model."""
from sqlalchemy import Column, String, DateTime, Float, JSON
from datetime import datetime
from db.session import Base
import uuid


class SystemMetrics(Base):
    """System performance metrics time-series storage."""

    __tablename__ = "system_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String, nullable=True)

    service = Column(String, nullable=True, index=True)
    environment = Column(String, nullable=True)
    region = Column(String, nullable=True)

    tags = Column(JSON, default=dict, nullable=False)
    metadata = Column(JSON, default=dict, nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
