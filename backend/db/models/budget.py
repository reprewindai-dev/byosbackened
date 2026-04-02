"""Budget model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class Budget(Base):
    """Budget configuration and tracking."""

    __tablename__ = "budgets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # Budget configuration
    budget_type = Column(String, nullable=False)  # "daily", "monthly", "project", "client"
    amount = Column(Numeric(10, 2), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Current state (updated atomically)
    current_spend = Column(Numeric(10, 6), nullable=False, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Forecasts
    forecast_exhaustion_date = Column(DateTime, nullable=True)
    forecast_updated_at = Column(DateTime, nullable=True)
    
    # Alerts
    alerts_sent = Column(JSON, nullable=True)  # List of thresholds alerted: ["50", "80", "95"]
    last_alert_at = Column(DateTime, nullable=True)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="budgets")
