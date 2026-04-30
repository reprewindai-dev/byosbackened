"""Unified workspace request log for dashboard observability."""
from sqlalchemy import Column, String, DateTime, Integer, Numeric, Text, ForeignKey
from datetime import datetime
from db.session import Base
import uuid


class WorkspaceRequestLog(Base):
    """Normalized request log for AI gateway and programmatic API usage."""

    __tablename__ = "workspace_request_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    api_key_id = Column(String, nullable=True, index=True)

    source_table = Column(String, nullable=False, default="workspace_request_logs", index=True)
    source_id = Column(String, nullable=False, index=True)
    request_kind = Column(String, nullable=False, index=True)  # ai.complete | exec
    request_path = Column(String, nullable=False, index=True)

    model = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="success", index=True)

    prompt_preview = Column(Text, nullable=True)
    response_preview = Column(Text, nullable=True)
    request_json = Column(Text, nullable=True)
    response_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    tokens_in = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Numeric(10, 6), nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
