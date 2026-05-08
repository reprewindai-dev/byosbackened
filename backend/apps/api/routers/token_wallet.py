"""Operating reserve router - balance, transactions, and reserve funding."""
import json
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from apps.api.deps import get_current_user, get_current_workspace_id
from core.config import get_settings
from db.session import get_db
from db.models import Subscription, SubscriptionStatus, TokenWallet, TokenTransaction, User
from core.redis_pool import get_redis

settings = get_settings()
router = APIRouter(prefix="/wallet", tags=["wallet"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

RESERVE_UNITS_PER_USD = 1000


class WalletBalanceResponse(BaseModel):
    workspace_id: str
    reserve_balance_units: int
    reserve_balance_usd: str
    # Deprecated compatibility fields. The public product language is Operating Reserve, not credits.
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
    metadata: Optional[dict[str, Any]] = None
    created_at: str


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    limit: int
    offset: int


class TopupOption(BaseModel):
    pack_name: str
    price_cents: int
    reserve_units: int
    reserve_usd: str
    credits: int
    bonus_percent: int


class TopupOptionsResponse(BaseModel):
    options: list[TopupOption]


class CreateCheckoutRequest(BaseModel):
    pack_name: str  # founding, standard, regulated
    success_url: str
    cancel_url: str


class CreateCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


# ─── Operating Reserve Definitions ────────────────────────────────────────────

RESERVE_PACKS = {
    "founding": {
        "name": "Founding Reserve",
        "price_cents": 15_000,  # $150 minimum reserve
        "reserve_units": 150_000,
        "bonus_percent": 0,
    },
    "standard": {
        "name": "Standard Reserve",
        "price_cents": 30_000,  # $300 minimum reserve
        "reserve_units": 300_000,
        "bonus_percent": 0,
    },
    "regulated": {
        "name": "Regulated Reserve",
        "price_cents": 250_000,  # $2,500 minimum reserve
        "reserve_units": 2_500_000,
        "bonus_percent": 0,
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


def _has_active_paid_subscription(db: Session, workspace_id: str) -> bool:
    """Operating Reserve is cash-backed only after paid activation."""
    return (
        db.query(Subscription)
        .filter(
            Subscription.workspace_id == workspace_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .first()
        is not None
    )


def _parse_transaction_metadata(raw: Optional[str]) -> Optional[dict[str, Any]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/balance", response_model=WalletBalanceResponse)
async def get_balance(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get current operating reserve balance and stats."""
    # Try cache first
    cached = _get_cached_balance(workspace_id)
    
    wallet = _get_or_create_wallet(db, workspace_id)
    paid_active = _has_active_paid_subscription(db, workspace_id)
    effective_balance = wallet.balance if paid_active else 0
    effective_purchased = wallet.total_credits_purchased if paid_active else 0
    effective_used = wallet.total_credits_used if paid_active else 0
    
    # Update cache if different
    if cached != effective_balance:
        _cache_balance(workspace_id, effective_balance)
    
    return WalletBalanceResponse(
        workspace_id=wallet.workspace_id,
        reserve_balance_units=effective_balance,
        reserve_balance_usd=f"{effective_balance / RESERVE_UNITS_PER_USD:.2f}",
        balance=effective_balance,
        monthly_credits_included=wallet.monthly_credits_included if paid_active else 0,
        monthly_credits_used=wallet.monthly_credits_used if paid_active else 0,
        monthly_period_start=wallet.monthly_period_start.isoformat() if wallet.monthly_period_start else None,
        monthly_period_end=wallet.monthly_period_end.isoformat() if wallet.monthly_period_end else None,
        total_credits_purchased=effective_purchased or 0,
        total_credits_used=effective_used or 0,
    )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get operating reserve transaction history."""
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
                metadata=_parse_transaction_metadata(t.metadata_json),
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
    """Get available operating reserve funding options."""
    return TopupOptionsResponse(
        options=[
            TopupOption(
                pack_name=pack_id,
                price_cents=pack["price_cents"],
                reserve_units=pack["reserve_units"],
                reserve_usd=f"{pack['reserve_units'] / RESERVE_UNITS_PER_USD:.2f}",
                credits=pack["reserve_units"],
                bonus_percent=pack["bonus_percent"],
            )
            for pack_id, pack in RESERVE_PACKS.items()
        ]
    )


@router.post("/topup/checkout", response_model=CreateCheckoutResponse)
async def create_topup_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create Stripe checkout session for operating reserve funding."""
    import stripe
    
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    stripe.api_key = settings.stripe_secret_key
    stripe.api_version = settings.stripe_api_version
    
    # Validate pack
    pack = RESERVE_PACKS.get(request.pack_name)
    if not pack:
        raise HTTPException(status_code=400, detail="Invalid reserve pack")
    
    workspace_id = current_user.workspace_id
    active_subscription = db.query(Subscription).filter(
        Subscription.workspace_id == workspace_id,
        Subscription.status == SubscriptionStatus.ACTIVE,
    ).first()
    if not active_subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Activate the workspace before adding operating reserve.",
        )
    
    success_separator = "&" if "?" in request.success_url else "?"

    # Create checkout session
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"Veklom Operating Reserve - {pack['name']}",
                    "description": f"${pack['reserve_units'] / RESERVE_UNITS_PER_USD:,.2f} operating reserve for governed execution",
                },
                "unit_amount": pack["price_cents"],
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.success_url + f"{success_separator}session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=request.cancel_url,
        metadata={
            "workspace_id": workspace_id,
            "pack_name": request.pack_name,
            "reserve_units": str(pack["reserve_units"]),
            "credits": str(pack["reserve_units"]),
            "type": "operating_reserve",
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
    """Get operating reserve usage statistics."""
    from datetime import timedelta
    from sqlalchemy import func
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get usage stats
    usage_stats = db.query(
        func.sum(TokenTransaction.amount).label("total_reserve_units"),
        func.count(TokenTransaction.id).label("transaction_count"),
    ).filter(
        TokenTransaction.workspace_id == workspace_id,
        TokenTransaction.transaction_type == "usage",
        TokenTransaction.created_at >= since,
    ).first()
    
    # Get top endpoints
    top_endpoints = db.query(
        TokenTransaction.endpoint_path,
        func.sum(-TokenTransaction.amount).label("reserve_units_used"),
        func.count(TokenTransaction.id).label("call_count"),
    ).filter(
        TokenTransaction.workspace_id == workspace_id,
        TokenTransaction.transaction_type == "usage",
        TokenTransaction.created_at >= since,
    ).group_by(
        TokenTransaction.endpoint_path
    ).order_by(
        desc("reserve_units_used")
    ).limit(10).all()
    
    return {
        "period_days": days,
        "total_reserve_units_used": abs(int(usage_stats.total_reserve_units or 0)),
        "total_reserve_usd_used": f"{abs(int(usage_stats.total_reserve_units or 0)) / RESERVE_UNITS_PER_USD:.2f}",
        "total_credits_used": abs(int(usage_stats.total_reserve_units or 0)),
        "transaction_count": int(usage_stats.transaction_count or 0),
        "top_endpoints": [
            {
                "endpoint": ep.endpoint_path,
                "reserve_units_used": int(ep.reserve_units_used or 0),
                "reserve_usd_used": f"{int(ep.reserve_units_used or 0) / RESERVE_UNITS_PER_USD:.2f}",
                "credits_used": int(ep.reserve_units_used or 0),
                "call_count": int(ep.call_count or 0),
            }
            for ep in top_endpoints
        ],
    }
