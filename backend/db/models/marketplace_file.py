"""Marketplace file metadata (S3-backed objects)."""
from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class MarketplaceFile(Base):
    __tablename__ = "marketplace_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = Column(String, ForeignKey("listings.id"), nullable=False, index=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    s3_key = Column(String, nullable=False, unique=True, index=True)
    file_type = Column(String, nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    checksum = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    listing = relationship("Listing", back_populates="files")
    vendor = relationship("Vendor")
    workspace = relationship("Workspace")
