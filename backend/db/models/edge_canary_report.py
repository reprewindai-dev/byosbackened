"""Persisted live protocol canary report."""
from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, JSON, String

from db.session import Base


class EdgeCanaryReport(Base):
    """Latest/archived protocol canary results for public proof rendering."""

    __tablename__ = "edge_canary_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, nullable=False, index=True)
    generated_at = Column(DateTime, nullable=False, index=True)
    report_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
