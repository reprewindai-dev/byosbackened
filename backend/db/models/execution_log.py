"""ExecutionLog — tenant-isolated record of every /v1/exec call."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, Index
from db.session import Base


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), nullable=True, index=True)

    # Request
    prompt = Column(Text, nullable=False)
    model = Column(String(128), nullable=False)

    # Response
    response = Column(Text, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)

    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Cost tracking in USD-equivalent workspace billing terms.
    cost_usd = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_execution_logs_tenant_created", "tenant_id", "created_at"),
    )
