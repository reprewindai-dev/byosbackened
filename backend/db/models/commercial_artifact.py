"""Founder-review-gated commercial artifacts derived from workspace scenarios."""
from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from db.session import Base


class CommercialArtifact(Base):
    """Draft commercial artifact ledger for community awareness and vertical packaging."""

    __tablename__ = "commercial_artifacts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    artifact_type = Column(String, nullable=False, default="community_awareness_run", index=True)
    title = Column(String, nullable=False)
    source_type = Column(String, nullable=False, default="vertical_playground", index=True)
    source_scenario_id = Column(String, nullable=True, index=True)
    handoff_json = Column(Text, nullable=False)
    artifact_json = Column(Text, nullable=False)
    founder_review_status = Column(String, nullable=False, default="pending_founder_review", index=True)
    spam_risk = Column(String, nullable=False, default="medium")
    regulated_claim_risk = Column(String, nullable=False, default="high")
    competitor_claim_risk = Column(String, nullable=False, default="medium")
    archive_record_id = Column(String, nullable=True, index=True)
    outcome = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
