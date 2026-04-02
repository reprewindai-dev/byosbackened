"""Admin endpoints for managing payments and receiving Bitcoin."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from db.session import get_db
from db.models.user import User
from db.models.subscription import Payment, PaymentStatus
from db.models.subscription import Subscription, SubscriptionStatus
from apps.api.deps import get_current_workspace_id
from apps.api.routers.admin import require_full_admin
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import json

router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])


class PaymentStatsResponse(BaseModel):
    total_payments: int
    total_revenue: float
    completed_payments: int
    pending_payments: int
    bitcoin_payments: int
    total_bitcoin_revenue: float
    recent_payments: List[dict]


@router.get("/stats")
async def get_payment_stats(
    admin: User = Depends(require_full_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get payment statistics for admin."""
    # Get all payments in workspace
    payments = (
        db.query(Payment)
        .filter(
            Payment.workspace_id == workspace_id,
        )
        .all()
    )

    total_payments = len(payments)
    total_revenue = sum(p.amount for p in payments if p.status == PaymentStatus.COMPLETED)
    completed_payments = len([p for p in payments if p.status == PaymentStatus.COMPLETED])
    pending_payments = len([p for p in payments if p.status == PaymentStatus.PENDING])
    bitcoin_payments = len([p for p in payments if p.payment_provider == "bitcoin"])
    bitcoin_revenue = sum(
        p.amount
        for p in payments
        if p.payment_provider == "bitcoin" and p.status == PaymentStatus.COMPLETED
    )

    # Recent payments (last 10)
    recent = (
        db.query(Payment)
        .filter(
            Payment.workspace_id == workspace_id,
        )
        .order_by(desc(Payment.created_at))
        .limit(10)
        .all()
    )

    recent_data = [
        {
            "id": p.id,
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status.value,
            "provider": p.payment_provider,
            "created_at": p.created_at.isoformat(),
            "user_id": p.user_id,
        }
        for p in recent
    ]

    return PaymentStatsResponse(
        total_payments=total_payments,
        total_revenue=total_revenue,
        completed_payments=completed_payments,
        pending_payments=pending_payments,
        bitcoin_payments=bitcoin_payments,
        total_bitcoin_revenue=bitcoin_revenue,
        recent_payments=recent_data,
    )


@router.get("/all")
async def get_all_payments(
    admin: User = Depends(require_full_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    status_filter: Optional[str] = Query(None),
    provider_filter: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all payments (admin only)."""
    query = db.query(Payment).filter(
        Payment.workspace_id == workspace_id,
    )

    if status_filter:
        query = query.filter(Payment.status == status_filter)

    if provider_filter:
        query = query.filter(Payment.payment_provider == provider_filter)

    payments = query.order_by(desc(Payment.created_at)).limit(limit).all()

    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "subscription_id": p.subscription_id,
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status.value,
            "provider": p.payment_provider,
            "provider_payment_id": p.provider_payment_id,
            "description": p.description,
            "created_at": p.created_at.isoformat(),
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        }
        for p in payments
    ]


@router.get("/bitcoin/status")
async def get_bitcoin_status(
    admin: User = Depends(require_full_admin),
):
    """Check Bitcoin payment receiving status."""
    from core.config import get_settings

    settings = get_settings()

    has_api_key = bool(settings.coinbase_commerce_api_key)
    has_webhook_secret = bool(settings.coinbase_commerce_webhook_secret)

    return {
        "configured": has_api_key and has_webhook_secret,
        "api_key_set": has_api_key,
        "webhook_secret_set": has_webhook_secret,
        "network": settings.bitcoin_network,
        "wallet_address": settings.bitcoin_wallet_address
        or "Not set (Coinbase Commerce handles payments)",
        "message": (
            "Bitcoin payments ready!"
            if (has_api_key and has_webhook_secret)
            else "Run SETUP_BITCOIN.bat to configure"
        ),
    }


@router.get("/revenue")
async def get_revenue_stats(
    admin: User = Depends(require_full_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get revenue statistics."""
    since = datetime.utcnow() - timedelta(days=days)

    payments = (
        db.query(Payment)
        .filter(
            Payment.workspace_id == workspace_id,
            Payment.status == PaymentStatus.COMPLETED,
            Payment.created_at >= since,
        )
        .all()
    )

    total_revenue = sum(p.amount for p in payments)

    by_provider = {}
    for p in payments:
        provider = p.payment_provider
        if provider not in by_provider:
            by_provider[provider] = {"count": 0, "revenue": 0.0}
        by_provider[provider]["count"] += 1
        by_provider[provider]["revenue"] += p.amount

    return {
        "period_days": days,
        "total_revenue": total_revenue,
        "total_payments": len(payments),
        "by_provider": by_provider,
        "average_payment": total_revenue / len(payments) if payments else 0,
    }
