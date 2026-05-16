"""Stripe Connect endpoints for vendor onboarding and marketplace payments."""
import logging
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from db.session import get_db

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing/connect", tags=["stripe-connect"])

DEFAULT_PLATFORM_FEE_PERCENT = 15


def _configure_stripe() -> None:
    stripe.api_key = settings.stripe_secret_key
    stripe.api_version = settings.stripe_api_version


# --- Schemas ------------------------------------------------------------------

class OnboardRequest(BaseModel):
    refresh_url: str = Field("https://veklom.com/marketplace/onboard/refresh")
    return_url: str = Field("https://veklom.com/marketplace/onboard/complete")


class OnboardResponse(BaseModel):
    account_id: str
    onboarding_url: str


class ConnectStatusResponse(BaseModel):
    vendor_id: str
    stripe_account_id: Optional[str]
    is_onboarded: bool
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool


class MarketplaceChargeRequest(BaseModel):
    listing_id: str
    amount_cents: int = Field(..., ge=50, description="Total charge in cents (min $0.50)")
    currency: str = Field("usd", max_length=3)
    platform_fee_percent: int = Field(DEFAULT_PLATFORM_FEE_PERCENT, ge=1, le=50)


class MarketplaceChargeResponse(BaseModel):
    payment_intent_id: str
    client_secret: str
    amount_cents: int
    platform_fee_cents: int
    vendor_payout_cents: int
    currency: str


# --- Routes -------------------------------------------------------------------

@router.post("/onboard", response_model=OnboardResponse)
async def onboard_vendor(
    payload: OnboardRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or retrieve a Stripe Connect Express account and return the onboarding URL."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    _configure_stripe()

    from db.models.vendor import Vendor

    vendor = (
        db.query(Vendor)
        .filter(Vendor.user_id == current_user.id)
        .first()
    )

    if not vendor:
        vendor = Vendor(
            user_id=current_user.id,
            workspace_id=current_user.workspace_id,
            display_name=current_user.email,
            plan="verified",
            subscription_status="inactive",
        )
        db.add(vendor)
        db.flush()

    if not vendor.stripe_account_id:
        account = stripe.Account.create(
            type="express",
            email=current_user.email,
            metadata={
                "vendor_id": vendor.id,
                "workspace_id": current_user.workspace_id,
            },
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        )
        vendor.stripe_account_id = account.id
        db.commit()

    link = stripe.AccountLink.create(
        account=vendor.stripe_account_id,
        refresh_url=payload.refresh_url,
        return_url=payload.return_url,
        type="account_onboarding",
    )

    return OnboardResponse(
        account_id=vendor.stripe_account_id,
        onboarding_url=link.url,
    )


@router.get("/status/{vendor_id}", response_model=ConnectStatusResponse)
async def connect_status(
    vendor_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the Stripe Connect onboarding status for a vendor."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    _configure_stripe()

    from db.models.vendor import Vendor

    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    charges_enabled = False
    payouts_enabled = False
    details_submitted = False

    if vendor.stripe_account_id:
        acct = stripe.Account.retrieve(vendor.stripe_account_id)
        charges_enabled = bool(acct.charges_enabled)
        payouts_enabled = bool(acct.payouts_enabled)
        details_submitted = bool(acct.details_submitted)

        if charges_enabled and not vendor.is_onboarded:
            vendor.is_onboarded = True
            vendor.subscription_status = "active"
            db.commit()

    return ConnectStatusResponse(
        vendor_id=vendor.id,
        stripe_account_id=vendor.stripe_account_id,
        is_onboarded=vendor.is_onboarded,
        charges_enabled=charges_enabled,
        payouts_enabled=payouts_enabled,
        details_submitted=details_submitted,
    )


@router.post("/charge", response_model=MarketplaceChargeResponse)
async def marketplace_charge(
    payload: MarketplaceChargeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a destination charge splitting payment between vendor and platform."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    _configure_stripe()

    from db.models.vendor import Vendor
    from db.models.listing import Listing

    listing = (
        db.query(Listing)
        .filter(Listing.id == payload.listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()
    if not vendor or not vendor.stripe_account_id or not vendor.is_onboarded:
        raise HTTPException(status_code=400, detail="Vendor not onboarded to Stripe Connect")

    platform_fee_cents = (payload.amount_cents * payload.platform_fee_percent) // 100
    vendor_payout_cents = payload.amount_cents - platform_fee_cents

    intent = stripe.PaymentIntent.create(
        amount=payload.amount_cents,
        currency=payload.currency,
        application_fee_amount=platform_fee_cents,
        transfer_data={"destination": vendor.stripe_account_id},
        metadata={
            "listing_id": payload.listing_id,
            "vendor_id": vendor.id,
            "buyer_id": current_user.id,
            "workspace_id": current_user.workspace_id,
            "platform_fee_percent": str(payload.platform_fee_percent),
        },
    )

    return MarketplaceChargeResponse(
        payment_intent_id=intent.id,
        client_secret=intent.client_secret,
        amount_cents=payload.amount_cents,
        platform_fee_cents=platform_fee_cents,
        vendor_payout_cents=vendor_payout_cents,
        currency=payload.currency,
    )


@router.post("/webhook")
async def connect_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe Connect webhook events."""
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    _configure_stripe()

    try:
        event = stripe.Webhook.construct_event(body, sig, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    from db.models.vendor import Vendor

    if event.type == "account.updated":
        acct = event.data.object
        vendor = (
            db.query(Vendor)
            .filter(Vendor.stripe_account_id == acct.id)
            .first()
        )
        if vendor:
            was_onboarded = vendor.is_onboarded
            vendor.is_onboarded = bool(acct.get("charges_enabled"))
            if vendor.is_onboarded and not was_onboarded:
                vendor.subscription_status = "active"
                logger.info("Vendor %s completed Stripe Connect onboarding", vendor.id)
            db.commit()

    elif event.type == "payment_intent.succeeded":
        pi = event.data.object
        vendor_id = (pi.get("metadata") or {}).get("vendor_id")
        if vendor_id:
            logger.info(
                "Payment succeeded for vendor %s: %s %s",
                vendor_id,
                pi.get("amount"),
                pi.get("currency"),
            )

    elif event.type == "payout.paid":
        payout = event.data.object
        logger.info("Payout paid: %s %s", payout.get("amount"), payout.get("currency"))

    return {"received": True}
