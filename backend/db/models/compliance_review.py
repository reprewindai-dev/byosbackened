"""Compliance review ledger for vendor/listing approvals."""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class ComplianceReview(Base):
    __tablename__ = "compliance_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True, index=True)
    listing_id = Column(String, ForeignKey("listings.id"), nullable=True, index=True)
    reviewer_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    review_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    findings_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    vendor = relationship("Vendor")
    listing = relationship("Listing")
    reviewer = relationship("User")
    workspace = relationship("Workspace")
