"""Referral system — generate links, track conversions, claim rewards."""
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, get_current_workspace_id
from db.models.referral import Referral, ReferralStatus, RewardType
from db.models.user import User
from db.models.token_wallet import TokenWallet, TokenTransaction
from db.session import get_db

router = APIRouter(prefix="/referrals", tags=["referrals"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ReferralLinkOut(BaseModel):
    referral_code: str
    referral_url: str


class ReferralStatsOut(BaseModel):
    total_invited: int
    total_converted: int
    total_pending: int
    rewards_earned: int
    referral_code: str
    referral_url: str


class ReferralOut(BaseModel):
    id: str
    referral_code: str
    status: str
    reward_type: str
    reward_value: int
    referred_email: Optional[str] = None
    converted_at: Optional[str] = None
    created_at: str


class ClaimResult(BaseModel):
    success: bool
    reward_type: str
    reward_value: int
    message: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_or_create_referral_code(user_id: str, db: Session) -> Referral:
    """Return the user's existing referral record or create a new one."""
    existing = (
        db.query(Referral)
        .filter(Referral.referrer_id == user_id, Referral.referred_id.is_(None))
        .first()
    )
    if existing:
        return existing

    code = secrets.token_urlsafe(8)
    ref = Referral(
        referrer_id=user_id,
        referral_code=code,
        status=ReferralStatus.PENDING,
        reward_type=RewardType.FREE_MONTH,
        reward_value=1,
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


_REFERRAL_BASE_URL = "https://veklom.com/register?ref="


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=ReferralLinkOut)
async def generate_referral_link(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate or retrieve the caller's unique referral link."""
    ref = _get_or_create_referral_code(current_user.id, db)
    return ReferralLinkOut(
        referral_code=ref.referral_code,
        referral_url=f"{_REFERRAL_BASE_URL}{ref.referral_code}",
    )


@router.get("/dashboard", response_model=ReferralStatsOut)
async def referral_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return referral stats for the current user."""
    all_refs = (
        db.query(Referral)
        .filter(Referral.referrer_id == current_user.id)
        .all()
    )
    converted = [r for r in all_refs if r.status == ReferralStatus.CONVERTED]
    pending = [r for r in all_refs if r.status == ReferralStatus.PENDING and r.referred_id is not None]
    rewards = sum(r.reward_value for r in converted)

    # Ensure the user has a referral code
    ref = _get_or_create_referral_code(current_user.id, db)

    return ReferralStatsOut(
        total_invited=len([r for r in all_refs if r.referred_id is not None]),
        total_converted=len(converted),
        total_pending=len(pending),
        rewards_earned=rewards,
        referral_code=ref.referral_code,
        referral_url=f"{_REFERRAL_BASE_URL}{ref.referral_code}",
    )


@router.get("/history", response_model=list[ReferralOut])
async def referral_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List the caller's referrals with pagination."""
    refs = (
        db.query(Referral)
        .filter(Referral.referrer_id == current_user.id, Referral.referred_id.isnot(None))
        .order_by(Referral.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    out: list[ReferralOut] = []
    for r in refs:
        referred_user = db.query(User).filter(User.id == r.referred_id).first() if r.referred_id else None
        out.append(
            ReferralOut(
                id=r.id,
                referral_code=r.referral_code,
                status=r.status.value if hasattr(r.status, "value") else str(r.status),
                reward_type=r.reward_type.value if hasattr(r.reward_type, "value") else str(r.reward_type),
                reward_value=r.reward_value,
                referred_email=referred_user.email if referred_user else None,
                converted_at=r.converted_at.isoformat() if r.converted_at else None,
                created_at=r.created_at.isoformat(),
            )
        )
    return out


@router.post("/claim", response_model=ClaimResult)
async def claim_referral_reward(
    referred_user_id: str = Query(..., description="ID of the referred user who just paid"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a referral as converted and credit the referrer's wallet."""
    ref = (
        db.query(Referral)
        .filter(
            Referral.referrer_id == current_user.id,
            Referral.referred_id == referred_user_id,
            Referral.status == ReferralStatus.PENDING,
        )
        .first()
    )
    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending referral found for this user",
        )

    ref.status = ReferralStatus.CONVERTED
    ref.converted_at = datetime.utcnow()

    # Credit the referrer's workspace token wallet
    wallet = (
        db.query(TokenWallet)
        .filter(TokenWallet.workspace_id == current_user.workspace_id)
        .first()
    )
    credit_amount = 1000  # tokens equivalent to 1 month free
    if wallet:
        balance_before = wallet.balance
        wallet.balance += credit_amount
    else:
        balance_before = 0
        wallet = TokenWallet(workspace_id=current_user.workspace_id, balance=credit_amount)
        db.add(wallet)
        db.flush()

    txn = TokenTransaction(
        wallet_id=wallet.id,
        workspace_id=current_user.workspace_id,
        amount=credit_amount,
        balance_before=balance_before,
        balance_after=balance_before + credit_amount,
        description=f"Referral reward — {ref.referred_id} converted",
        transaction_type="referral_reward",
    )
    db.add(txn)
    db.commit()

    return ClaimResult(
        success=True,
        reward_type=ref.reward_type.value if hasattr(ref.reward_type, "value") else str(ref.reward_type),
        reward_value=ref.reward_value,
        message=f"Referral converted! {credit_amount} tokens credited to your wallet.",
    )


@router.post("/track")
async def track_referral_signup(
    referral_code: str = Query(..., description="Referral code from signup URL"),
    referred_user_id: str = Query(..., description="ID of the new user who signed up"),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Called during registration to link a new user to their referrer."""
    # Find the referral code's owner
    template = (
        db.query(Referral)
        .filter(Referral.referral_code == referral_code)
        .first()
    )
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid referral code",
        )

    # Don't allow self-referral
    if template.referrer_id == referred_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-referral not allowed",
        )

    # Check if this user was already referred
    existing = (
        db.query(Referral)
        .filter(Referral.referred_id == referred_user_id)
        .first()
    )
    if existing:
        return {"status": "already_tracked", "referral_id": existing.id}

    # Create a new referral record linking referrer to referred
    new_ref = Referral(
        referrer_id=template.referrer_id,
        referred_id=referred_user_id,
        referral_code=secrets.token_urlsafe(8),
        status=ReferralStatus.PENDING,
        reward_type=RewardType.FREE_MONTH,
        reward_value=1,
    )
    db.add(new_ref)
    db.commit()
    db.refresh(new_ref)

    return {"status": "tracked", "referral_id": new_ref.id}
