"""Cost prediction model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class CostPrediction(Base):
    """Cost prediction with actual cost tracking."""

    __tablename__ = "cost_predictions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    operation_type = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=True)
    
    # Input metrics (precise)
    input_tokens = Column(Integer, nullable=False)
    estimated_output_tokens = Column(Integer, nullable=False)
    input_size_bytes = Column(Integer, nullable=True)
    
    # Prediction (precise - 6 decimal places)
    predicted_cost = Column(Numeric(10, 6), nullable=False)
    confidence_lower = Column(Numeric(10, 6), nullable=False)
    confidence_upper = Column(Numeric(10, 6), nullable=False)
    
    # Actual (recorded after operation)
    actual_cost = Column(Numeric(10, 6), nullable=True)
    actual_input_tokens = Column(Integer, nullable=True)
    actual_output_tokens = Column(Integer, nullable=True)
    
    # Accuracy metrics
    prediction_error_percent = Column(Numeric(5, 2), nullable=True)
    was_within_confidence = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    actualized_at = Column(DateTime, nullable=True)
