"""Cost allocation model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class CostAllocation(Base):
    """Cost allocation - precise to the cent."""

    __tablename__ = "cost_allocations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    operation_id = Column(String, nullable=False, index=True)
    
    # Allocation target
    project_id = Column(String, nullable=True, index=True)
    client_id = Column(String, nullable=True, index=True)
    
    # Cost (precise - 6 decimal places)
    allocated_cost = Column(Numeric(10, 6), nullable=False)
    base_cost = Column(Numeric(10, 6), nullable=False)  # Before markup
    markup_percent = Column(Numeric(5, 2), nullable=False, default=0)
    final_cost = Column(Numeric(10, 6), nullable=False)  # After markup
    
    # Allocation method
    allocation_method = Column(String, nullable=False)  # "percentage", "fixed", "usage"
    allocation_rule_id = Column(String, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String, nullable=True)  # User who created allocation
