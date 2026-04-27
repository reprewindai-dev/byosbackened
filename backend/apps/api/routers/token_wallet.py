"""Token wallet router - balance, transactions, and credit purchase."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from apps.api.deps import get_current_user, get_current_workspace_id
from core.config import get_settings
from db.session import get_db
from db.models import TokenWallet, TokenTransaction, User
from core.redis_pool import get_redis

settings = get_settings()
router = APIRouter(prefix="/wallet", tags=["wallet"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class WalletBalanceResponse(BaseModel):
    workspace_id: str
    balance: int
    monthly_credits_included: int
    monthly_credits_used: int
    monthly_period_start: Optional[str]
    monthly_period_end: Optional[str]
    total_credits_purchased: int
    total_credits_used: int


class TransactionResponse(BaseModel):
    id: str
    transaction_type: str
    amount: int
    balance_before: int
    balance_after: int
    endpoint_path: Optional[str]
    endpoint_method: Optional[str]
    request_id: Optional[str]
    description: Optional[str]
    created_at: str


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    limit: int
    offset: int


class TopupOption(BaseModel):
    pack_name: str
    price_cents: int
    credits: int
    bonus_percent: int


class TopupOptionsResponse(BaseModel):
    options: list[TopupOption]


class CreateCheckoutRequest(BaseModel):
    pack_name: str  # starter, growth, team, enterprise
    success_url: str
    cancel_url: str


class CreateCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


# ─── Token Pack Definitions ───────────────────────────────────────────────────

TOKEN_PACKS = {
    "starter": {
        "name": "Starter Pack",
        "price_cents": 2500,  # $25
        "credits": 2_500_000,
        "bonus_percent": 0,
    },
    "growth": {
        "name": "Growth Pack",
        "price_cents": 10000,  # $100
        "credits": 12_000_000,
        "bonus_percent": 20,
    },
    "team": {
        "name": "Team Pack",
        "price_cents": 50000,  # $500
        "credits": 75_000_000,
        "bonus_percent": 50,
    },
    "enterprise": {
        "name": "Enterprise Pack",
        "price_cents": 200000,  # $2,000
        "credits": 350_000_000,
        "bonus_percent": 75,
    },
}


# ─── Helper Functions ───────────────────────────────────────────────────────

def _get_or_create_wallet(db: Session, workspace_id: str) -> TokenWallet:
    """Get or create wallet for workspace."""
    wallet = db.query(TokenWallet).filter(
        TokenWallet.workspace_id == workspace_id
    ).first()
    
    if not wallet:
        wallet = TokenWallet(
            workspace_id=workspace_id,
            balance=0
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    return wallet


def _get_cached_balance(workspace_id: str) -> Optional[int]:
    """Get cached balance from Redis."""
    try:
        redis = get_redis()
        key = f"wallet:balance:{workspace_id}"
        balance = redis.get(key)
        if balance:
            return int(balance)
    except Exception:
        pass
    return None


def _cache_balance(workspace_id: str, balance: int, ttl: int = 300):
    """Cache balance in Redis."""
    try:
        redis = get_redis()
        key = f"wallet:balance:{workspace_id}"
        redis.setex(key, ttl, str(balance))
    except Exception:
        pass


def _invalidate_balance_cache(workspace_id: str):
    """Invalidate cached balance."""
    try:
        redis = get_redis()
        key = f"wallet:balance:{workspace_id}"
        redis.delete(key)
    except Exception:
        pass


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/balance", response_model=WalletBalanceResponse)
async def get_balance(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get current token wallet balance and stats."""
    # Try cache first
    cached = _get_cached_balance(workspace_id)
    
    wallet = _get_or_create_wallet(db, workspace_id)
    
    # Update cache if different
    if cached != wallet.balance:
        _cache_balance(workspace_id, wallet.balance)
    
    return WalletBalanceResponse(
        workspace_id=wallet.workspace_id,
        balance=wallet.balance,
        monthly_credits_included=wallet.monthly_credits_included or 0,
        monthly_credits_used=wallet.monthly_credits_used or 0,
        monthly_period_start=wallet.monthly_period_start.isoformat() if wallet.monthly_period_start else None,
        monthly_period_end=wallet.monthly_period_end.isoformat() if wallet.monthly_period_end else None,
        total_credits_purchased=wallet.total_credits_purchased or 0,
        total_credits_used=wallet.total_credits_used or 0,
    )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get token transaction history."""
    query = db.query(TokenTransaction).filter(
        TokenTransaction.workspace_id == workspace_id
    )
    
    if transaction_type:
        query = query.filter(TokenTransaction.transaction_type == transaction_type)
    
    total = query.count()
    
    transactions = query.order_by(
        desc(TokenTransaction.created_at)
    ).offset(offset).limit(limit).all()
    
    return TransactionListResponse(
        transactions=[
            TransactionResponse(
                id=t.id,
                transaction_type=t.transaction_type,
                amount=t.amount,
                balance_before=t.balance_before,
                balance_after=t.balance_after,
                endpoint_path=t.endpoint_path,
                endpoint_method=t.endpoint_method,
                request_id=t.request_id,
                description=t.description,
                created_at=t.created_at.isoformat() if t.created_at else None,
            )
            for t in transactions
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/topup/options", response_model=TopupOptionsResponse)
async def get_topup_options():
    """Get available token pack options."""
    return TopupOptionsResponse(
        options=[
            TopupOption(
                pack_name=pack_id,
                price_cents=pack["price_cents"],
                credits=pack["credits"],
                bonus_percent=pack["bonus_percent"],
            )
            for pack_id, pack in TOKEN_PACKS.items()
        ]
    )


@router.post("/topup/checkout", response_model=CreateCheckoutResponse)
async def create_topup_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create Stripe checkout session for token pack purchase."""
    import stripe
    
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    stripe.api_key = settings.stripe_secret_key
    
    # Validate pack
    pack = TOKEN_PACKS.get(request.pack_name)
    if not pack:
        raise HTTPException(status_code=400, detail="Invalid token pack")
    
    workspace_id = current_user.workspace_id
    
    # Create checkout session
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"Veklom Token Pack - {pack['name']}",
                    "description": f"{pack['credits']:,} API credits ({pack['bonus_percent']}% bonus)",
                },
                "unit_amount": pack["price_cents"],
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.cancel_url,
        metadata={
            "workspace_id": workspace_id,
            "pack_name": request.pack_name,
            "credits": str(pack["credits"]),
            "type": "token_pack",
        },
    )
    
    return CreateCheckoutResponse(
        checkout_url=session.url,
        session_id=session.id,
    )


@router.get("/stats/usage")
async def get_usage_stats(
    days: int = 30,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get usage statistics for the wallet."""
    from datetime import timedelta
    from sqlalchemy import func
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get usage stats
    usage_stats = db.query(
        func.sum(TokenTransaction.amount).label("total_credits"),
        func.count(TokenTransaction.id).label("transaction_count"),
    ).filter(
        TokenTransaction.workspace_id == workspace_id,
        TokenTransaction.transaction_type == "usage",
        TokenTransaction.created_at >= since,
    ).first()
    
    # Get top endpoints
    top_endpoints = db.query(
        TokenTransaction.endpoint_path,
        func.sum(-TokenTransaction.amount).label("credits_used"),
        func.count(TokenTransaction.id).label("call_count"),
    ).filter(
        TokenTransaction.workspace_id == workspace_id,
        TokenTransaction.transaction_type == "usage",
        TokenTransaction.created_at >= since,
    ).group_by(
        TokenTransaction.endpoint_path
    ).order_by(
        desc("credits_used")
    ).limit(10).all()
    
    return {
        "period_days": days,
        "total_credits_used": abs(int(usage_stats.total_credits or 0)),
        "transaction_count": int(usage_stats.transaction_count or 0),
        "top_endpoints": [
            {
                "endpoint": ep.endpoint_path,
                "credits_used": int(ep.credits_used or 0),
                "call_count": int(ep.call_count or 0),
            }
            for ep in top_endpoints
        ],
    }
