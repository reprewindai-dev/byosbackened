"""Marketplace usage metering events."""
from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.id"), nullable=False, index=True)
    order_id = Column(String, ForeignKey("marketplace_orders.id"), nullable=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    usage_units = Column(BigInteger, nullable=False, default=0)
    unit_label = Column(String, nullable=True)
    billable = Column(String, nullable=False, default="true")
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    vendor = relationship("Vendor")
    listing = relationship("Listing")
    order = relationship("MarketplaceOrder")
    workspace = relationship("Workspace")
