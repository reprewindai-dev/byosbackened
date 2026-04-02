"""Savings report model - store savings reports."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class SavingsReport(Base):
    """Savings report per workspace."""
    
    __tablename__ = "savings_reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # Report period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    report_type = Column(String, nullable=False, default="monthly")  # monthly, weekly, custom
    
    # Savings metrics
    total_savings = Column(Numeric(10, 6), nullable=False)
    baseline_cost = Column(Numeric(10, 6), nullable=False)
    actual_cost = Column(Numeric(10, 6), nullable=False)
    savings_percent = Column(Numeric(5, 2), nullable=False)
    
    # Performance improvements
    latency_reduction_ms = Column(Integer, nullable=True)
    cache_hit_rate_improvement = Column(Numeric(5, 4), nullable=True)
    operations_count = Column(Integer, nullable=False)
    
    # Breakdown by operation type
    breakdown_by_operation = Column(JSON, nullable=True)  # {operation_type: {savings, count}}
    
    # Breakdown by provider
    breakdown_by_provider = Column(JSON, nullable=True)  # {provider: {cost, savings}}
    
    # Projections
    projected_next_month_savings = Column(Numeric(10, 6), nullable=True)
    
    # Report metadata
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    generated_by = Column(String, nullable=False, default="savings_calculator")
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="savings_reports")
