"""Marketplace listing model."""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class Listing(Base):
    __tablename__ = "listings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, nullable=False, default="usd")
    status = Column(String, nullable=False, default="draft", index=True)  # draft|active|disabled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="listings")
    workspace = relationship("Workspace")
    files = relationship("MarketplaceFile", back_populates="listing", cascade="all, delete-orphan")
    evidence_packages = relationship("EvidencePackage", back_populates="listing", cascade="all, delete-orphan")
