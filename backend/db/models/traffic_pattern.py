"""Traffic pattern model - store traffic patterns and predictions."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class TrafficPattern(Base):
    """Traffic pattern and prediction per workspace."""
    
    __tablename__ = "traffic_patterns"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # Pattern metadata
    pattern_type = Column(String, nullable=False)  # "daily", "weekly", "seasonal"
    operation_type = Column(String, nullable=True)  # Optional: specific operation type
    
    # Pattern data
    pattern_data = Column(JSON, nullable=False)  # {hour: count, day: count, etc.}
    avg_requests_per_hour = Column(Numeric(10, 2), nullable=True)
    peak_hour = Column(Integer, nullable=True)  # Hour of day (0-23)
    peak_day = Column(Integer, nullable=True)   # Day of week (0-6)
    
    # Prediction
    predicted_spike_time = Column(DateTime, nullable=True)
    predicted_spike_multiplier = Column(Numeric(5, 2), nullable=True)  # e.g., 2.5x normal
    predicted_requests = Column(Integer, nullable=True)
    
    # Learning metadata
    samples_used = Column(Integer, nullable=False, default=0)
    confidence_score = Column(Numeric(5, 4), nullable=True)  # 0-1
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="traffic_patterns")
