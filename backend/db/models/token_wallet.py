"""Token wallet model for credit-based usage metering."""
from sqlalchemy import Column, String, DateTime, BigInteger, Index, text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base
import uuid


class TokenWallet(Base):
    """Token wallet for workspace-scoped credit balance."""

    __tablename__ = "token_wallets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, unique=True, nullable=False, index=True)
    
    # Running balance - source of truth
    balance = Column(BigInteger, default=0, nullable=False)
    
    # Monthly allotment tracking
    monthly_credits_included = Column(BigInteger, default=0, nullable=False)
    monthly_credits_used = Column(BigInteger, default=0, nullable=False)
    monthly_period_start = Column(DateTime, nullable=True)
    monthly_period_end = Column(DateTime, nullable=True)
    
    # Lifetime stats
    total_credits_purchased = Column(BigInteger, default=0, nullable=False)
    total_credits_used = Column(BigInteger, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transactions = relationship("TokenTransaction", back_populates="wallet", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TokenWallet(workspace_id={self.workspace_id}, balance={self.balance})>"


class TokenTransaction(Base):
    """Token transaction ledger for audit trail."""

    __tablename__ = "token_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String, nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    
    # Transaction type: 'monthly_allotment', 'purchase', 'usage', 'refund', 'adjustment'
    transaction_type = Column(String, nullable=False, index=True)
    
    # Amount (positive for credits, negative for debits)
    amount = Column(BigInteger, nullable=False)
    
    # Running balance snapshot
    balance_before = Column(BigInteger, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    
    # For usage transactions
    endpoint_path = Column(String, nullable=True, index=True)
    endpoint_method = Column(String, nullable=True)
    request_id = Column(String, nullable=True, index=True)
    
    # For purchase transactions
    stripe_payment_intent_id = Column(String, nullable=True, index=True)
    stripe_checkout_session_id = Column(String, nullable=True)
    
    # Metadata
    description = Column(String, nullable=True)
    metadata_json = Column(String, nullable=True)  # JSON string for flexibility
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    wallet = relationship("TokenWallet", foreign_keys=[wallet_id], primaryjoin="TokenTransaction.wallet_id == TokenWallet.id")

    def __repr__(self):
        return f"<TokenTransaction(type={self.transaction_type}, amount={self.amount}, workspace_id={self.workspace_id})>"


# Create indexes for common queries
Index("idx_token_transactions_workspace_created", TokenTransaction.workspace_id, TokenTransaction.created_at.desc())
Index("idx_token_transactions_type_created", TokenTransaction.transaction_type, TokenTransaction.created_at.desc())
