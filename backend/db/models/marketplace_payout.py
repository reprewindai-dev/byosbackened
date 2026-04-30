"""Marketplace payout records."""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class MarketplacePayout(Base):
    __tablename__ = "marketplace_payouts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    order_id = Column(String, ForeignKey("marketplace_orders.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False, default=0)
    stripe_transfer_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending|paid|failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor")
    order = relationship("MarketplaceOrder")
    workspace = relationship("Workspace")
