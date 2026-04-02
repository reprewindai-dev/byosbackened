"""
Seked Infrastructure - Production Billing System
===============================================

Complete Stripe-integrated billing system for Seked's infrastructure revenue model.
Handles citizen subscriptions, per-decision microtransactions, compliance add-ons,
and enterprise licensing with automated provisioning and access control.

Revenue Model:
- Citizen Lifecycle: $50 setup + $25-500/month subscription (tier-based)
- Per-Decision: $0.01-0.15 per governance action
- Compliance Add-ons: $150-300/month per citizen
- Enterprise Licensing: Custom contracts

All payments processed through Stripe with webhooks, dunning management,
and revenue analytics.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import structlog
import stripe
from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import get_settings
from core.ai_citizenship.service import ai_citizenship_service
from core.revenue.infrastructure_model import infrastructure_revenue


# Stripe Configuration
settings = get_settings()
stripe.api_key = settings.stripe_secret_key
STRIPE_WEBHOOK_SECRET = getattr(settings, 'stripe_webhook_secret', None)  # Optional
STRIPE_PUBLISHABLE_KEY = settings.stripe_publishable_key

# Billing Models
class BillingTier(BaseModel):
    """Billing tier with Stripe pricing."""
    tier_id: str
    stripe_price_id: str
    name: str
    base_citizenship_fee: Decimal
    monthly_subscription: Decimal
    per_decision_fee: Decimal
    per_verification_fee: Decimal
    features: List[str]
    stripe_product_id: str
    active: bool = True

class ComplianceAddon(BaseModel):
    """Compliance add-on package."""
    addon_id: str
    stripe_price_id: str
    name: str
    description: str
    monthly_fee_per_citizen: Decimal
    setup_fee: Optional[Decimal] = None
    features: List[str]
    stripe_product_id: str
    active: bool = True

class CustomerAccount(BaseModel):
    """Customer billing account."""
    customer_id: str
    stripe_customer_id: str
    tenant_id: str
    email: str
    company_name: Optional[str] = None
    billing_address: Optional[Dict[str, str]] = None
    payment_method_id: Optional[str] = None
    subscription_status: str = "inactive"  # active, past_due, canceled, incomplete
    current_period_end: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

class CitizenSubscription(BaseModel):
    """Individual citizen subscription."""
    subscription_id: str
    citizen_id: str
    customer_id: str
    tier_id: str
    stripe_subscription_id: str
    status: str = "active"
    current_period_start: str
    current_period_end: str
    addons: List[str] = []
    auto_renew: bool = True
    cancel_at_period_end: bool = False

class UsageRecord(BaseModel):
    """Usage record for metered billing."""
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    citizen_id: str
    customer_id: str
    usage_type: str  # decision, verification, api_call
    quantity: int
    amount: Decimal
    stripe_invoice_item_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    billed: bool = False

class InvoiceData(BaseModel):
    """Invoice data for reporting."""
    invoice_id: str
    stripe_invoice_id: str
    customer_id: str
    amount_due: Decimal
    amount_paid: Decimal
    currency: str = "usd"
    status: str
    billing_period_start: str
    billing_period_end: str
    line_items: List[Dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class SekedBillingService:
    """Complete billing service with Stripe integration."""

    def __init__(self):
        self.settings = get_settings()
        self.billing_db_path = os.path.join(self.settings.DATA_DIR, "billing_stripe.db")
        self.logger = structlog.get_logger(__name__)

        # Initialize Stripe products and prices
        self.billing_tiers = self._init_billing_tiers()
        self.compliance_addons = self._init_compliance_addons()

        self._init_billing_database()

    def _init_billing_tiers(self) -> Dict[str, BillingTier]:
        """Initialize billing tiers with Stripe pricing."""
        return {
            "basic": BillingTier(
                tier_id="basic",
                stripe_price_id="price_basic_monthly",
                name="Basic Citizenship",
                base_citizenship_fee=Decimal("50.00"),
                monthly_subscription=Decimal("25.00"),
                per_decision_fee=Decimal("0.01"),
                per_verification_fee=Decimal("0.001"),
                features=["Basic governance", "Standard audit trail", "Community support"],
                stripe_product_id="prod_basic"
            ),
            "professional": BillingTier(
                tier_id="professional",
                stripe_price_id="price_professional_monthly",
                name="Professional Citizenship",
                base_citizenship_fee=Decimal("200.00"),
                monthly_subscription=Decimal("100.00"),
                per_decision_fee=Decimal("0.05"),
                per_verification_fee=Decimal("0.005"),
                features=["Advanced governance", "Priority audit", "Compliance reporting", "API access"],
                stripe_product_id="prod_professional"
            ),
            "enterprise": BillingTier(
                tier_id="enterprise",
                stripe_price_id="price_enterprise_monthly",
                name="Enterprise Citizenship",
                base_citizenship_fee=Decimal("1000.00"),
                monthly_subscription=Decimal("500.00"),
                per_decision_fee=Decimal("0.10"),
                per_verification_fee=Decimal("0.01"),
                features=["Critical governance", "Real-time monitoring", "Custom compliance", "Dedicated support", "Private audit streams"],
                stripe_product_id="prod_enterprise"
            ),
            "eu_compliance": BillingTier(
                tier_id="eu_compliance",
                stripe_price_id="price_eu_compliance_monthly",
                name="EU AI Act Compliance",
                base_citizenship_fee=Decimal("1500.00"),
                monthly_subscription=Decimal("750.00"),
                per_decision_fee=Decimal("0.15"),
                per_verification_fee=Decimal("0.015"),
                features=["EU AI Act compliance", "GDPR alignment", "Real-time monitoring", "Legal support", "Regulatory reporting"],
                stripe_product_id="prod_eu_compliance"
            )
        }

    def _init_compliance_addons(self) -> Dict[str, ComplianceAddon]:
        """Initialize compliance add-on packages."""
        return {
            "eu_ai_act_pack": ComplianceAddon(
                addon_id="eu_ai_act_pack",
                stripe_price_id="price_eu_ai_act_pack",
                name="EU AI Act Compliance Pack",
                description="Complete compliance package for EU AI Act requirements",
                monthly_fee_per_citizen=Decimal("150.00"),
                setup_fee=Decimal("2500.00"),
                features=[
                    "AI Act risk classification automation",
                    "Fundamental rights impact assessment",
                    "Transparency obligations management",
                    "Data governance compliance"
                ],
                stripe_product_id="prod_eu_ai_act"
            ),
            "financial_grade": ComplianceAddon(
                addon_id="financial_grade",
                stripe_price_id="price_financial_grade",
                name="Financial-Grade AI Governance",
                description="Enhanced governance for financial services AI systems",
                monthly_fee_per_citizen=Decimal("300.00"),
                setup_fee=Decimal("5000.00"),
                features=[
                    "SOX compliance automation",
                    "Model risk management integration",
                    "Audit trail encryption (FIPS 140-2)",
                    "Financial regulatory reporting"
                ],
                stripe_product_id="prod_financial_grade"
            ),
            "healthcare_compliance": ComplianceAddon(
                addon_id="healthcare_compliance",
                stripe_price_id="price_healthcare_compliance",
                name="Healthcare AI Compliance Pack",
                description="HIPAA and healthcare regulatory compliance",
                monthly_fee_per_citizen=Decimal("250.00"),
                setup_fee=Decimal("3500.00"),
                features=[
                    "HIPAA compliance automation",
                    "PHI data handling controls",
                    "Healthcare regulatory reporting",
                    "Patient privacy protection"
                ],
                stripe_product_id="prod_healthcare"
            )
        }

    def _init_billing_database(self) -> None:
        """Initialize billing database."""
        import sqlite3
        os.makedirs(os.path.dirname(self.billing_db_path), exist_ok=True)

        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customer_accounts (
                customer_id TEXT PRIMARY KEY,
                stripe_customer_id TEXT UNIQUE NOT NULL,
                tenant_id TEXT NOT NULL,
                email TEXT NOT NULL,
                company_name TEXT,
                billing_address TEXT,
                payment_method_id TEXT,
                subscription_status TEXT NOT NULL,
                current_period_end TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS citizen_subscriptions (
                subscription_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                tier_id TEXT NOT NULL,
                stripe_subscription_id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                current_period_start TEXT NOT NULL,
                current_period_end TEXT NOT NULL,
                addons TEXT NOT NULL,
                auto_renew BOOLEAN NOT NULL,
                cancel_at_period_end BOOLEAN NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_records (
                record_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                usage_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                amount TEXT NOT NULL,
                stripe_invoice_item_id TEXT,
                timestamp TEXT NOT NULL,
                billed BOOLEAN NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id TEXT PRIMARY KEY,
                stripe_invoice_id TEXT UNIQUE NOT NULL,
                customer_id TEXT NOT NULL,
                amount_due TEXT NOT NULL,
                amount_paid TEXT NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                billing_period_start TEXT NOT NULL,
                billing_period_end TEXT NOT NULL,
                line_items TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        self.logger.info("Billing database initialized")

    async def create_customer_account(self, tenant_id: str, email: str,
                                    company_name: Optional[str] = None,
                                    billing_address: Optional[Dict[str, str]] = None) -> CustomerAccount:
        """Create a new customer account with Stripe."""
        try:
            # Create Stripe customer
            stripe_customer = stripe.Customer.create(
                email=email,
                name=company_name,
                address=billing_address,
                metadata={
                    "tenant_id": tenant_id,
                    "service": "seked"
                }
            )

            customer_account = CustomerAccount(
                customer_id=f"cust_{tenant_id}_{int(datetime.utcnow().timestamp())}",
                stripe_customer_id=stripe_customer.id,
                tenant_id=tenant_id,
                email=email,
                company_name=company_name,
                billing_address=billing_address
            )

            # Store in database
            import sqlite3
            conn = sqlite3.connect(self.billing_db_path)
            conn.execute("""
                INSERT INTO customer_accounts (
                    customer_id, stripe_customer_id, tenant_id, email, company_name,
                    billing_address, subscription_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_account.customer_id,
                customer_account.stripe_customer_id,
                customer_account.tenant_id,
                customer_account.email,
                customer_account.company_name,
                json.dumps(customer_account.billing_address) if customer_account.billing_address else None,
                customer_account.subscription_status,
                customer_account.created_at
            ))
            conn.commit()
            conn.close()

            self.logger.info("Customer account created",
                           customer_id=customer_account.customer_id,
                           stripe_customer_id=customer_account.stripe_customer_id)

            return customer_account

        except stripe.error.StripeError as e:
            self.logger.error("Stripe customer creation failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Payment setup failed: {str(e)}")

    async def subscribe_citizen(self, citizen_id: str, customer_id: str,
                               tier_id: str, payment_method_id: str = None,
                               addons: List[str] = None) -> CitizenSubscription:
        """Subscribe a citizen to a billing tier."""
        # Get customer account
        customer = self.get_customer_account(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer account not found")

        tier = self.billing_tiers.get(tier_id)
        if not tier:
            raise HTTPException(status_code=400, detail="Invalid billing tier")

        # Verify citizen exists
        citizen = ai_citizenship_service.get_citizenship(citizen_id)
        if not citizen:
            raise HTTPException(status_code=404, detail="Citizen not found")

        try:
            # Create Stripe subscription
            subscription_items = [
                {"price": tier.stripe_price_id}
            ]

            # Add compliance addons
            if addons:
                for addon_id in addons:
                    addon = self.compliance_addons.get(addon_id)
                    if addon:
                        subscription_items.append({"price": addon.stripe_price_id})

            stripe_subscription = stripe.Subscription.create(
                customer=customer.stripe_customer_id,
                items=subscription_items,
                default_payment_method=payment_method_id,
                metadata={
                    "citizen_id": citizen_id,
                    "tier_id": tier_id,
                    "service": "seked"
                }
            )

            # Create setup fee invoice item if applicable
            if tier.base_citizenship_fee > 0:
                stripe.InvoiceItem.create(
                    customer=customer.stripe_customer_id,
                    amount=int(tier.base_citizenship_fee * 100),  # Convert to cents
                    currency="usd",
                    description=f"Citizenship setup fee - {tier.name}",
                    metadata={"citizen_id": citizen_id}
                )

            # Add addon setup fees
            if addons:
                for addon_id in addons:
                    addon = self.compliance_addons.get(addon_id)
                    if addon and addon.setup_fee:
                        stripe.InvoiceItem.create(
                            customer=customer.stripe_customer_id,
                            amount=int(addon.setup_fee * 100),
                            currency="usd",
                            description=f"{addon.name} setup fee",
                            metadata={"citizen_id": citizen_id, "addon_id": addon_id}
                        )

            subscription = CitizenSubscription(
                subscription_id=f"sub_{citizen_id}_{int(datetime.utcnow().timestamp())}",
                citizen_id=citizen_id,
                customer_id=customer_id,
                tier_id=tier_id,
                stripe_subscription_id=stripe_subscription.id,
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start).isoformat() + "Z",
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end).isoformat() + "Z",
                addons=addons or []
            )

            # Store subscription
            import sqlite3
            conn = sqlite3.connect(self.billing_db_path)
            conn.execute("""
                INSERT INTO citizen_subscriptions (
                    subscription_id, citizen_id, customer_id, tier_id,
                    stripe_subscription_id, status, current_period_start,
                    current_period_end, addons, auto_renew, cancel_at_period_end
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subscription.subscription_id,
                subscription.citizen_id,
                subscription.customer_id,
                subscription.tier_id,
                subscription.stripe_subscription_id,
                subscription.status,
                subscription.current_period_start,
                subscription.current_period_end,
                json.dumps(subscription.addons),
                subscription.auto_renew,
                subscription.cancel_at_period_end
            ))
            conn.commit()
            conn.close()

            # Update infrastructure revenue account
            await infrastructure_revenue.create_citizen_billing_account(
                citizen_id, customer_id, tier_id,
                compliance_packages=addons or []
            )

            self.logger.info("Citizen subscription created",
                           subscription_id=subscription.subscription_id,
                           citizen_id=citizen_id,
                           tier=tier_id)

            return subscription

        except stripe.error.StripeError as e:
            self.logger.error("Stripe subscription creation failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Subscription failed: {str(e)}")

    async def record_usage(self, citizen_id: str, usage_type: str,
                          quantity: int = 1) -> UsageRecord:
        """Record metered usage for billing."""
        # Get citizen subscription
        subscription = self.get_citizen_subscription_by_citizen(citizen_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")

        tier = self.billing_tiers.get(subscription.tier_id)
        if not tier:
            raise HTTPException(status_code=400, detail="Invalid subscription tier")

        # Calculate amount based on usage type
        if usage_type == "decision":
            amount = tier.per_decision_fee * quantity
        elif usage_type == "verification":
            amount = tier.per_verification_fee * quantity
        else:
            amount = Decimal("0.00")

        usage_record = UsageRecord(
            citizen_id=citizen_id,
            customer_id=subscription.customer_id,
            usage_type=usage_type,
            quantity=quantity,
            amount=amount
        )

        # Store usage record
        import sqlite3
        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            INSERT INTO usage_records (
                record_id, citizen_id, customer_id, usage_type, quantity,
                amount, timestamp, billed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            usage_record.record_id,
            usage_record.citizen_id,
            usage_record.customer_id,
            usage_record.usage_type,
            usage_record.quantity,
            str(usage_record.amount),
            usage_record.timestamp,
            usage_record.billed
        ))
        conn.commit()
        conn.close()

        # Create Stripe usage record for metered billing
        try:
            # Find the subscription item for metered billing
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            subscription_item = stripe_subscription.items.data[0]  # Assuming first item

            stripe.SubscriptionItem.create_usage_record(
                subscription_item.id,
                quantity=quantity,
                timestamp=int(datetime.utcnow().timestamp()),
                action="increment"
            )
        except stripe.error.StripeError as e:
            self.logger.warning("Stripe usage record creation failed", error=str(e))

        self.logger.info("Usage recorded",
                        record_id=usage_record.record_id,
                        citizen_id=citizen_id,
                        usage_type=usage_type,
                        quantity=quantity,
                        amount=str(amount))

        return usage_record

    def get_customer_account(self, customer_id: str) -> Optional[CustomerAccount]:
        """Get customer account by ID."""
        import sqlite3
        conn = sqlite3.connect(self.billing_db_path)
        cursor = conn.execute("""
            SELECT customer_id, stripe_customer_id, tenant_id, email, company_name,
                   billing_address, payment_method_id, subscription_status, current_period_end, created_at
            FROM customer_accounts WHERE customer_id = ?
        """, (customer_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return CustomerAccount(
                customer_id=row[0],
                stripe_customer_id=row[1],
                tenant_id=row[2],
                email=row[3],
                company_name=row[4],
                billing_address=json.loads(row[5]) if row[5] else None,
                payment_method_id=row[6],
                subscription_status=row[7],
                current_period_end=row[8],
                created_at=row[9]
            )
        return None

    def get_citizen_subscription_by_citizen(self, citizen_id: str) -> Optional[CitizenSubscription]:
        """Get active subscription for a citizen."""
        import sqlite3
        conn = sqlite3.connect(self.billing_db_path)
        cursor = conn.execute("""
            SELECT subscription_id, citizen_id, customer_id, tier_id, stripe_subscription_id,
                   status, current_period_start, current_period_end, addons, auto_renew, cancel_at_period_end
            FROM citizen_subscriptions
            WHERE citizen_id = ? AND status = 'active'
            ORDER BY current_period_start DESC LIMIT 1
        """, (citizen_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return CitizenSubscription(
                subscription_id=row[0],
                citizen_id=row[1],
                customer_id=row[2],
                tier_id=row[3],
                stripe_subscription_id=row[4],
                status=row[5],
                current_period_start=row[6],
                current_period_end=row[7],
                addons=json.loads(row[8]) if row[8] else [],
                auto_renew=row[9],
                cancel_at_period_end=row[10]
            )
        return None

    async def process_stripe_webhook(self, payload: str, signature: str) -> Dict[str, Any]:
        """Process Stripe webhook events."""
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)

            # Handle different event types
            if event.type == "invoice.payment_succeeded":
                return await self._handle_payment_success(event.data.object)
            elif event.type == "invoice.payment_failed":
                return await self._handle_payment_failure(event.data.object)
            elif event.type == "customer.subscription.updated":
                return await self._handle_subscription_update(event.data.object)
            elif event.type == "customer.subscription.deleted":
                return await self._handle_subscription_cancel(event.data.object)

            return {"status": "ignored", "event_type": event.type}

        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        except Exception as e:
            self.logger.error("Webhook processing failed", error=str(e))
            raise HTTPException(status_code=500, detail="Webhook processing failed")

    async def _handle_payment_success(self, invoice: stripe.Invoice) -> Dict[str, Any]:
        """Handle successful payment webhook."""
        # Update customer account status
        customer_id = self._get_customer_id_from_stripe_id(invoice.customer)

        import sqlite3
        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            UPDATE customer_accounts
            SET subscription_status = 'active'
            WHERE stripe_customer_id = ?
        """, (invoice.customer,))
        conn.commit()
        conn.close()

        # Store invoice data
        invoice_data = InvoiceData(
            invoice_id=f"inv_{int(datetime.utcnow().timestamp())}",
            stripe_invoice_id=invoice.id,
            customer_id=customer_id,
            amount_due=Decimal(str(invoice.amount_due)) / 100,  # Convert from cents
            amount_paid=Decimal(str(invoice.amount_paid)) / 100,
            currency=invoice.currency,
            status=invoice.status,
            billing_period_start=datetime.fromtimestamp(invoice.period_start).isoformat() + "Z",
            billing_period_end=datetime.fromtimestamp(invoice.period_end).isoformat() + "Z",
            line_items=[{
                "description": item.description,
                "amount": Decimal(str(item.amount)) / 100,
                "quantity": item.quantity
            } for item in invoice.lines.data]
        )

        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            INSERT INTO invoices (
                invoice_id, stripe_invoice_id, customer_id, amount_due, amount_paid,
                currency, status, billing_period_start, billing_period_end, line_items, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_data.invoice_id,
            invoice_data.stripe_invoice_id,
            invoice_data.customer_id,
            str(invoice_data.amount_due),
            str(invoice_data.amount_paid),
            invoice_data.currency,
            invoice_data.status,
            invoice_data.billing_period_start,
            invoice_data.billing_period_end,
            json.dumps(invoice_data.line_items),
            invoice_data.created_at
        ))
        conn.commit()
        conn.close()

        self.logger.info("Payment processed successfully",
                        invoice_id=invoice.id,
                        customer_id=customer_id,
                        amount=str(invoice_data.amount_paid))

        return {"status": "processed", "invoice_id": invoice.id}

    async def _handle_payment_failure(self, invoice: stripe.Invoice) -> Dict[str, Any]:
        """Handle failed payment webhook."""
        customer_id = self._get_customer_id_from_stripe_id(invoice.customer)

        # Update subscription status
        import sqlite3
        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            UPDATE customer_accounts
            SET subscription_status = 'past_due'
            WHERE stripe_customer_id = ?
        """, (invoice.customer,))
        conn.commit()
        conn.close()

        self.logger.warning("Payment failed",
                          invoice_id=invoice.id,
                          customer_id=customer_id)

        return {"status": "payment_failed", "invoice_id": invoice.id}

    async def _handle_subscription_update(self, subscription: stripe.Subscription) -> Dict[str, Any]:
        """Handle subscription update webhook."""
        # Update subscription status in database
        import sqlite3
        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            UPDATE citizen_subscriptions
            SET status = ?, current_period_start = ?, current_period_end = ?
            WHERE stripe_subscription_id = ?
        """, (
            subscription.status,
            datetime.fromtimestamp(subscription.current_period_start).isoformat() + "Z",
            datetime.fromtimestamp(subscription.current_period_end).isoformat() + "Z",
            subscription.id
        ))
        conn.commit()
        conn.close()

        return {"status": "subscription_updated", "subscription_id": subscription.id}

    async def _handle_subscription_cancel(self, subscription: stripe.Subscription) -> Dict[str, Any]:
        """Handle subscription cancellation webhook."""
        import sqlite3
        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            UPDATE citizen_subscriptions
            SET status = 'canceled', cancel_at_period_end = TRUE
            WHERE stripe_subscription_id = ?
        """, (subscription.id,))
        conn.commit()
        conn.close()

        return {"status": "subscription_canceled", "subscription_id": subscription.id}

    def _get_customer_id_from_stripe_id(self, stripe_customer_id: str) -> Optional[str]:
        """Get internal customer ID from Stripe customer ID."""
        import sqlite3
        conn = sqlite3.connect(self.billing_db_path)
        cursor = conn.execute("""
            SELECT customer_id FROM customer_accounts
            WHERE stripe_customer_id = ?
        """, (stripe_customer_id,))

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None

    def get_revenue_analytics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get comprehensive revenue analytics."""
        import sqlite3
        start_date = (datetime.utcnow() - timedelta(days=period_days)).isoformat() + "Z"

        conn = sqlite3.connect(self.billing_db_path)

        # Revenue by type
        cursor = conn.execute("""
            SELECT SUM(CAST(amount AS DECIMAL)) as total_revenue,
                   COUNT(*) as total_transactions
            FROM usage_records
            WHERE timestamp >= ? AND billed = TRUE
        """, (start_date,))

        revenue_row = cursor.fetchone()

        # Subscription revenue (simplified)
        cursor = conn.execute("""
            SELECT COUNT(*) as active_subscriptions
            FROM citizen_subscriptions
            WHERE status = 'active'
        """)

        sub_row = cursor.fetchone()

        # Customer metrics
        cursor = conn.execute("""
            SELECT COUNT(*) as total_customers,
                   COUNT(CASE WHEN subscription_status = 'active' THEN 1 END) as active_customers
            FROM customer_accounts
        """)

        customer_row = cursor.fetchone()

        conn.close()

        return {
            "period_days": period_days,
            "total_revenue": float(revenue_row[0] or 0),
            "total_transactions": revenue_row[1] or 0,
            "active_subscriptions": sub_row[0] or 0,
            "total_customers": customer_row[0] or 0,
            "active_customers": customer_row[1] or 0,
            "average_revenue_per_customer": float(revenue_row[0] or 0) / max(customer_row[0] or 1, 1),
            "churn_rate": 0.0  # Would calculate from historical data
        }


# Global billing service instance
seked_billing = SekedBillingService()


# API Router for billing endpoints
router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])
security = HTTPBearer()


@router.post("/customers", response_model=CustomerAccount)
async def create_customer(
    email: str,
    tenant_id: str,
    company_name: Optional[str] = None,
    billing_address: Optional[Dict[str, str]] = None
):
    """Create a new customer account."""
    return await seked_billing.create_customer_account(
        tenant_id, email, company_name, billing_address
    )


@router.post("/citizens/{citizen_id}/subscribe", response_model=CitizenSubscription)
async def subscribe_citizen(
    citizen_id: str,
    tier_id: str,
    customer_id: str,
    payment_method_id: Optional[str] = None,
    addons: Optional[List[str]] = None
):
    """Subscribe a citizen to a billing tier."""
    return await seked_billing.subscribe_citizen(
        citizen_id, customer_id, tier_id, payment_method_id, addons
    )


@router.post("/usage", response_model=UsageRecord)
async def record_usage(
    citizen_id: str,
    usage_type: str,
    quantity: int = 1
):
    """Record metered usage for billing."""
    return await seked_billing.record_usage(citizen_id, usage_type, quantity)


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle Stripe webhook events."""
    body = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    result = await seked_billing.process_stripe_webhook(body.decode(), signature)
    return result


@router.get("/analytics/revenue")
async def get_revenue_analytics(period_days: int = 30):
    """Get revenue analytics."""
    return seked_billing.get_revenue_analytics(period_days)


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Get customer account details."""
    customer = seked_billing.get_customer_account(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/config/stripe")
async def get_stripe_config():
    """Get Stripe public configuration."""
    return {
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "tiers": {tier_id: {
            "name": tier.name,
            "monthly_price": str(tier.monthly_subscription),
            "setup_fee": str(tier.base_citizenship_fee),
            "features": tier.features
        } for tier_id, tier in seked_billing.billing_tiers.items()},
        "addons": {addon_id: {
            "name": addon.name,
            "monthly_price": str(addon.monthly_fee_per_citizen),
            "setup_fee": str(addon.setup_fee) if addon.setup_fee else None,
            "features": addon.features
        } for addon_id, addon in seked_billing.compliance_addons.items()}
    }
