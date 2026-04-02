"""Bitcoin payment webhook handler."""

from fastapi import APIRouter, Request, HTTPException, status, Header, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.user import User
from db.models.subscription import Subscription, SubscriptionStatus
from db.models.subscription import Payment, PaymentStatus
from apps.api.deps import get_current_user
from core.bitcoin_payments import get_bitcoin_processor
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bitcoin", tags=["bitcoin"])


@router.post("/webhook")
async def bitcoin_webhook(
    request: Request,
    x_cc_webhook_signature: str = Header(None, alias="X-CC-Webhook-Signature"),
    db: Session = Depends(get_db),
):
    """
    Handle Bitcoin payment webhook from Coinbase Commerce.

    This endpoint receives payment confirmations and updates subscriptions.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        payload_str = body.decode("utf-8")
        payload = json.loads(payload_str)

        # Verify webhook signature
        processor = get_bitcoin_processor()
        if not processor.verify_webhook(payload_str, x_cc_webhook_signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # Process webhook event
        event_data = await processor.process_webhook(payload)

        if not event_data:
            return {"status": "ignored"}

        charge_id = event_data.get("charge_id")
        event_status = event_data.get("status")
        metadata = event_data.get("metadata", {})

        # Find payment by charge_id
        payment = (
            db.query(Payment)
            .filter(
                Payment.provider_payment_id == charge_id,
                Payment.payment_provider == "bitcoin",
            )
            .first()
        )

        if not payment:
            logger.warning(f"Payment not found for charge_id: {charge_id}")
            return {"status": "payment_not_found"}

        # Update payment status
        if event_status == "completed":
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.utcnow()

            # Activate subscription
            if payment.subscription_id:
                subscription = (
                    db.query(Subscription)
                    .filter(Subscription.id == payment.subscription_id)
                    .first()
                )

                if subscription:
                    subscription.status = SubscriptionStatus.ACTIVE
                    logger.info(f"Subscription {subscription.id} activated via Bitcoin payment")

        elif event_status == "failed":
            payment.status = PaymentStatus.FAILED

        db.commit()

        return {"status": "processed", "event": event_status}

    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}",
        )


@router.get("/check-payment/{charge_id}")
async def check_payment_status(
    charge_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check Bitcoin payment status."""
    # Find payment
    payment = (
        db.query(Payment)
        .filter(
            Payment.provider_payment_id == charge_id,
            Payment.user_id == user.id,
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    # Check with Coinbase Commerce
    processor = get_bitcoin_processor()
    try:
        charge = await processor.get_charge(charge_id)

        if charge and charge.get("status") == "COMPLETED":
            # Update payment if needed
            if payment.status != PaymentStatus.COMPLETED:
                payment.status = PaymentStatus.COMPLETED
                payment.completed_at = datetime.utcnow()

                # Activate subscription
                if payment.subscription_id:
                    subscription = (
                        db.query(Subscription)
                        .filter(Subscription.id == payment.subscription_id)
                        .first()
                    )
                    if subscription:
                        subscription.status = SubscriptionStatus.ACTIVE

                db.commit()

        await processor.close()

        return {
            "charge_id": charge_id,
            "status": payment.status.value,
            "charge_status": charge.get("status") if charge else "unknown",
            "payment_url": charge.get("payment_url") if charge else None,
        }
    except Exception as e:
        logger.error(f"Payment check error: {e}")
        return {
            "charge_id": charge_id,
            "status": payment.status.value,
            "error": str(e),
        }
