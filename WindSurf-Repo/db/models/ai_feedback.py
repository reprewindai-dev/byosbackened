"""AI feedback model - human/automated labels for quality flywheel."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class AIFeedback(Base):
    """Feedback for an AI operation."""

    __tablename__ = "ai_feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)

    # Optional linkage
    audit_log_id = Column(String, ForeignKey("ai_audit_logs.id"), nullable=True, index=True)
    operation_id = Column(String, nullable=True, index=True)  # job/operation correlation id

    # Label source
    source = Column(String, nullable=False, default="user")  # user, admin, automated

    # Ratings / labels
    rating = Column(Integer, nullable=True)  # e.g. 1-5
    quality_score = Column(
        Numeric(5, 2), nullable=True
    )  # normalized 0-1 or 0-100 (workspace-defined)
    is_correct = Column(Integer, nullable=True)  # 1/0 (use int for DB portability)

    # Freeform + structured feedback
    feedback_text = Column(Text, nullable=True)
    feedback_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    workspace = relationship("Workspace", back_populates="ai_feedback")
    audit_log = relationship("AIAuditLog")
