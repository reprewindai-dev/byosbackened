"""Evidence package model for compliance attachments."""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class EvidencePackage(Base):
    __tablename__ = "evidence_packages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = Column(String, ForeignKey("listings.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    metadata_json = Column(String, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    listing = relationship("Listing", back_populates="evidence_packages")
    workspace = relationship("Workspace")
