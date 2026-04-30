"""Marketplace order and order items."""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class MarketplaceOrder(Base):
    __tablename__ = "marketplace_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending|paid|failed|fulfilled
    total_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, nullable=False, default="usd")
    stripe_payment_intent = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    buyer = relationship("User")
    workspace = relationship("Workspace")
    items = relationship("MarketplaceOrderItem", back_populates="order", cascade="all, delete-orphan")


class MarketplaceOrderItem(Base):
    __tablename__ = "marketplace_order_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("marketplace_orders.id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("listings.id"), nullable=False, index=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False, index=True)
    price_cents = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="pending", index=True)  # pending|accepted|rejected

    order = relationship("MarketplaceOrder", back_populates="items")
    listing = relationship("Listing")
    vendor = relationship("Vendor")
