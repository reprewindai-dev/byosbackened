"""ML model metadata storage."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Numeric, Integer, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class MLModel(Base):
    """ML model metadata and versioning."""

    __tablename__ = "ml_models"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    model_type = Column(String, nullable=False)  # "cost_predictor", "routing_optimizer", etc.
    model_version = Column(String, nullable=False)
    
    # Model metrics
    training_samples = Column(Integer, nullable=False)
    test_samples = Column(Integer, nullable=True)
    mape = Column(Numeric(5, 4), nullable=True)  # Mean Absolute Percentage Error
    accuracy = Column(Numeric(5, 4), nullable=True)
    
    # Model storage
    s3_key = Column(String, nullable=False)  # Where model is stored (non-portable)
    feature_list = Column(JSON, nullable=True)  # List of features used
    
    # Training metadata
    trained_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    training_duration_seconds = Column(Integer, nullable=True)
    
    # Model status
    is_active = Column(Boolean, default=True, nullable=False)
    is_production = Column(Boolean, default=False, nullable=False)  # A/B testing
    
    # Relationships
    workspace = relationship("Workspace", back_populates="ml_models")
