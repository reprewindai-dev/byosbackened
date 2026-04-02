"""
Stripe Polling Service - Monitors subscriptions without webhooks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import stripe
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.subscription import Subscription, SubscriptionStatus, Payment, PaymentStatus
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

class StripePollingService:
    """Polls Stripe for subscription updates instead of using webhooks."""
    
    def __init__(self):
        self.poll_interval_minutes = 15  # Check every 15 minutes
        self.running = False
        
    async def start_polling(self):
        """Start the background polling service."""
        if self.running:
            logger.warning("Stripe polling service already running")
            return
            
        self.running = True
        logger.info("Starting Stripe polling service (no webhooks)")
        
        while self.running:
            try:
                await self.poll_subscriptions()
                await asyncio.sleep(self.poll_interval_minutes * 60)
            except Exception as e:
                logger.error(f"Error in Stripe polling: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def stop_polling(self):
        """Stop the polling service."""
        self.running = False
        logger.info("Stopped Stripe polling service")
    
    async def poll_subscriptions(self):
        """Poll Stripe for subscription updates."""
        db = SessionLocal()
        try:
            # Get all active subscriptions from our database
            subscriptions = db.query(Subscription).filter(
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING])
            ).all()
            
            for subscription in subscriptions:
                await self.update_subscription_status(db, subscription)
                
            db.commit()
            logger.info(f"Polled {len(subscriptions)} subscriptions")
            
        except Exception as e:
            logger.error(f"Error polling subscriptions: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def update_subscription_status(self, db: Session, subscription: Subscription):
        """Update subscription status from Stripe."""
        try:
            if not subscription.stripe_subscription_id:
                return
                
            # Get subscription from Stripe
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            
            # Update status based on Stripe
            old_status = subscription.status
            new_status = self.map_stripe_status(stripe_sub.status)
            
            if old_status != new_status:
                subscription.status = new_status
                subscription.updated_at = datetime.utcnow()
                
                # Log status change
                logger.info(f"Subscription {subscription.id} status changed: {old_status} -> {new_status}")
                
                # Handle payment events
                if stripe_sub.latest_invoice:
                    await self.process_payment(db, subscription, stripe_sub.latest_invoice)
                    
        except stripe.error.StripeError as e:
            logger.error(f"Error updating subscription {subscription.id}: {e}")
    
    def map_stripe_status(self, stripe_status: str) -> SubscriptionStatus:
        """Map Stripe status to our SubscriptionStatus enum."""
        mapping = {
            "trialing": SubscriptionStatus.TRIAL,
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELLED,
            "unpaid": SubscriptionStatus.UNPAID,
            "incomplete": SubscriptionStatus.PENDING,
            "incomplete_expired": SubscriptionStatus.CANCELLED,
        }
        return mapping.get(stripe_status, SubscriptionStatus.PENDING)
    
    async def process_payment(self, db: Session, subscription: Subscription, invoice):
        """Process payment from Stripe invoice."""
        try:
            # Check if we already processed this invoice
            existing_payment = db.query(Payment).filter(
                Payment.stripe_invoice_id == invoice.id
            ).first()
            
            if existing_payment:
                return
                
            # Create payment record
            payment = Payment(
                subscription_id=subscription.id,
                stripe_invoice_id=invoice.id,
                amount=invoice.amount_paid / 100,  # Convert from cents
                currency=invoice.currency.upper(),
                status=self.map_payment_status(invoice.status),
                created_at=datetime.fromtimestamp(invoice.created),
                updated_at=datetime.utcnow()
            )
            
            db.add(payment)
            logger.info(f"Processed payment {invoice.id} for subscription {subscription.id}")
            
        except Exception as e:
            logger.error(f"Error processing payment {invoice.id}: {e}")
    
    def map_payment_status(self, stripe_status: str) -> PaymentStatus:
        """Map Stripe invoice status to our PaymentStatus enum."""
        mapping = {
            "draft": PaymentStatus.PENDING,
            "open": PaymentStatus.PENDING,
            "paid": PaymentStatus.COMPLETED,
            "void": PaymentStatus.FAILED,
            "uncollectible": PaymentStatus.FAILED,
        }
        return mapping.get(stripe_status, PaymentStatus.PENDING)

# Global polling service instance
stripe_polling_service = StripePollingService()

async def start_stripe_polling():
    """Start the Stripe polling service (call this on app startup)."""
    if settings.stripe_secret_key:
        asyncio.create_task(stripe_polling_service.start_polling())
    else:
        logger.warning("Stripe not configured - polling service not started")

def stop_stripe_polling():
    """Stop the Stripe polling service (call this on app shutdown)."""
    stripe_polling_service.stop_polling()
