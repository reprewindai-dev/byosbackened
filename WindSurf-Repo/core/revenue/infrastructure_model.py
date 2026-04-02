"""
Infrastructure Revenue Model
============================

This module implements Seked's infrastructure revenue model - moving from SaaS pricing
to "rails-pricing" where Seked becomes the critical infrastructure that every AI
transaction flows through.

Revenue primitives:
- Per-citizen lifecycle: Issue/revoke/upgrade credits
- Per-decision/verification: Every enforcement consumes credits
- Private clusters: Licensed deployments for national/sectoral use
- Compliance add-ons: EU AI Act Pack, Financial-Grade Pack, etc.

This creates the trillion-dollar network effect where Seked is the "only practical
passport" for AI systems to exist and communicate.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from decimal import Decimal
import structlog

from core.config import get_settings


class PricingTier(BaseModel):
    """Pricing tier for different trust levels and jurisdictions."""
    tier_id: str
    name: str
    trust_level: str
    jurisdiction: str
    base_citizenship_fee: Decimal  # One-time fee for citizenship
    monthly_subscription: Decimal  # Monthly fee per citizen
    per_decision_fee: Decimal  # Fee per governance decision
    per_verification_fee: Decimal  # Fee per certificate verification
    compliance_addon_multiplier: Decimal = Decimal("1.0")  # Multiplier for add-ons
    features: List[str] = []  # Included features


class CompliancePackage(BaseModel):
    """Compliance add-on package."""
    package_id: str
    name: str
    description: str
    regulatory_framework: str  # "eu_ai_act", "nist_ai_rmf", "iso_42001", etc.
    monthly_fee_per_citizen: Decimal
    setup_fee: Decimal
    features: List[str] = []
    jurisdictions: List[str] = []  # Applicable jurisdictions


class CitizenBillingAccount(BaseModel):
    """Billing account for AI citizen."""
    citizen_id: str
    tenant_id: str
    pricing_tier: str
    compliance_packages: List[str] = []
    credit_balance: Decimal = Decimal("0.00")
    auto_recharge_threshold: Decimal = Decimal("100.00")
    auto_recharge_amount: Decimal = Decimal("500.00")
    payment_method: Optional[str] = None  # Tokenized payment method
    billing_cycle_start: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: str = "active"  # active, suspended, terminated


class BillingTransaction(BaseModel):
    """Individual billing transaction."""
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    citizen_id: str
    tenant_id: str
    transaction_type: str  # citizenship_fee, decision_fee, verification_fee, subscription, addon
    amount: Decimal
    currency: str = "USD"
    description: str
    reference_id: Optional[str] = None  # Related event/decision ID
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: str = "completed"  # pending, completed, failed, refunded
    payment_intent_id: Optional[str] = None  # Payment processor reference


class RevenueAnalytics(BaseModel):
    """Revenue analytics for business intelligence."""
    period_start: str
    period_end: str
    total_revenue: Decimal
    revenue_by_type: Dict[str, Decimal]
    revenue_by_tier: Dict[str, Decimal]
    revenue_by_jurisdiction: Dict[str, Decimal]
    new_citizens: int
    active_citizens: int
    total_decisions: int
    average_revenue_per_citizen: Decimal
    churn_rate: Decimal
    growth_metrics: Dict[str, any] = {}


class InfrastructureRevenueEngine:
    """Revenue engine for Seked infrastructure business model."""

    def __init__(self):
        self.settings = get_settings()
        self.revenue_path = os.path.join(self.settings.DATA_DIR, "revenue")
        self.pricing_db_path = os.path.join(self.revenue_path, "pricing.db")
        self.billing_db_path = os.path.join(self.revenue_path, "billing.db")
        self.analytics_db_path = os.path.join(self.revenue_path, "analytics.db")
        self.logger = structlog.get_logger(__name__)

        # Initialize pricing tiers
        self.pricing_tiers = self._init_pricing_tiers()
        self.compliance_packages = self._init_compliance_packages()

        self._init_revenue_storage()

    def _init_revenue_storage(self) -> None:
        """Initialize revenue storage databases."""
        os.makedirs(self.revenue_path, exist_ok=True)

        # Initialize pricing database
        if not os.path.exists(self.pricing_db_path):
            self._init_pricing_db()

        # Initialize billing database
        if not os.path.exists(self.billing_db_path):
            self._init_billing_db()

        # Initialize analytics database
        if not os.path.exists(self.analytics_db_path):
            self._init_analytics_db()

        self.logger.info("Infrastructure revenue storage initialized")

    def _init_pricing_db(self) -> None:
        """Initialize pricing configuration database."""
        import sqlite3

        conn = sqlite3.connect(self.pricing_db_path)

        # Pricing tiers table
        conn.execute("""
            CREATE TABLE pricing_tiers (
                tier_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                trust_level TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                base_citizenship_fee TEXT NOT NULL,  -- Decimal as string
                monthly_subscription TEXT NOT NULL,
                per_decision_fee TEXT NOT NULL,
                per_verification_fee TEXT NOT NULL,
                compliance_addon_multiplier TEXT NOT NULL,
                features TEXT NOT NULL,  -- JSON array
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
        """)

        # Compliance packages table
        conn.execute("""
            CREATE TABLE compliance_packages (
                package_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                regulatory_framework TEXT NOT NULL,
                monthly_fee_per_citizen TEXT NOT NULL,
                setup_fee TEXT NOT NULL,
                features TEXT NOT NULL,  -- JSON array
                jurisdictions TEXT NOT NULL,  -- JSON array
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
        """)

        # Insert default pricing tiers
        for tier in self.pricing_tiers.values():
            conn.execute("""
                INSERT INTO pricing_tiers (
                    tier_id, name, trust_level, jurisdiction, base_citizenship_fee,
                    monthly_subscription, per_decision_fee, per_verification_fee,
                    compliance_addon_multiplier, features
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tier.tier_id, tier.name, tier.trust_level, tier.jurisdiction,
                str(tier.base_citizenship_fee), str(tier.monthly_subscription),
                str(tier.per_decision_fee), str(tier.per_verification_fee),
                str(tier.compliance_addon_multiplier), json.dumps(tier.features)
            ))

        # Insert compliance packages
        for package in self.compliance_packages.values():
            conn.execute("""
                INSERT INTO compliance_packages (
                    package_id, name, description, regulatory_framework,
                    monthly_fee_per_citizen, setup_fee, features, jurisdictions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                package.package_id, package.name, package.description,
                package.regulatory_framework, str(package.monthly_fee_per_citizen),
                str(package.setup_fee), json.dumps(package.features),
                json.dumps(package.jurisdictions)
            ))

        conn.commit()
        conn.close()

    def _init_billing_db(self) -> None:
        """Initialize billing and transactions database."""
        import sqlite3

        conn = sqlite3.connect(self.billing_db_path)

        # Citizen billing accounts
        conn.execute("""
            CREATE TABLE citizen_billing_accounts (
                citizen_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                pricing_tier TEXT NOT NULL,
                compliance_packages TEXT NOT NULL,  -- JSON array
                credit_balance TEXT NOT NULL,
                auto_recharge_threshold TEXT NOT NULL,
                auto_recharge_amount TEXT NOT NULL,
                payment_method TEXT,
                billing_cycle_start TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)

        # Billing transactions
        conn.execute("""
            CREATE TABLE billing_transactions (
                transaction_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                description TEXT NOT NULL,
                reference_id TEXT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                payment_intent_id TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _init_analytics_db(self) -> None:
        """Initialize analytics database."""
        import sqlite3

        conn = sqlite3.connect(self.analytics_db_path)

        # Revenue analytics
        conn.execute("""
            CREATE TABLE revenue_analytics (
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                total_revenue TEXT NOT NULL,
                revenue_by_type TEXT NOT NULL,  -- JSON
                revenue_by_tier TEXT NOT NULL,  -- JSON
                revenue_by_jurisdiction TEXT NOT NULL,  -- JSON
                new_citizens INTEGER NOT NULL,
                active_citizens INTEGER NOT NULL,
                total_decisions INTEGER NOT NULL,
                average_revenue_per_citizen TEXT NOT NULL,
                churn_rate TEXT NOT NULL,
                growth_metrics TEXT NOT NULL,  -- JSON
                created_at TEXT NOT NULL,
                PRIMARY KEY (period_start, period_end)
            )
        """)

        conn.commit()
        conn.close()

    def _init_pricing_tiers(self) -> Dict[str, PricingTier]:
        """Initialize default pricing tiers."""
        return {
            "basic_us": PricingTier(
                tier_id="basic_us",
                name="Basic Citizenship - US",
                trust_level="low",
                jurisdiction="us",
                base_citizenship_fee=Decimal("50.00"),
                monthly_subscription=Decimal("25.00"),
                per_decision_fee=Decimal("0.01"),
                per_verification_fee=Decimal("0.001"),
                features=["Basic governance", "Standard audit trail", "Community support"]
            ),
            "professional_us": PricingTier(
                tier_id="professional_us",
                name="Professional Citizenship - US",
                trust_level="medium",
                jurisdiction="us",
                base_citizenship_fee=Decimal("200.00"),
                monthly_subscription=Decimal("100.00"),
                per_decision_fee=Decimal("0.05"),
                per_verification_fee=Decimal("0.005"),
                features=["Advanced governance", "Priority audit", "Compliance reporting", "API access"]
            ),
            "enterprise_us": PricingTier(
                tier_id="enterprise_us",
                name="Enterprise Citizenship - US",
                trust_level="high",
                jurisdiction="us",
                base_citizenship_fee=Decimal("1000.00"),
                monthly_subscription=Decimal("500.00"),
                per_decision_fee=Decimal("0.10"),
                per_verification_fee=Decimal("0.01"),
                features=["Critical governance", "Real-time monitoring", "Custom compliance", "Dedicated support", "Private audit streams"]
            ),
            "eu_compliance": PricingTier(
                tier_id="eu_compliance",
                name="EU AI Act Compliance",
                trust_level="high",
                jurisdiction="eu",
                base_citizenship_fee=Decimal("1500.00"),
                monthly_subscription=Decimal("750.00"),
                per_decision_fee=Decimal("0.15"),
                per_verification_fee=Decimal("0.015"),
                compliance_addon_multiplier=Decimal("1.5"),
                features=["EU AI Act compliance", "GDPR alignment", "Real-time monitoring", "Legal support", "Regulatory reporting"]
            )
        }

    def _init_compliance_packages(self) -> Dict[str, CompliancePackage]:
        """Initialize compliance add-on packages."""
        return {
            "eu_ai_act_pack": CompliancePackage(
                package_id="eu_ai_act_pack",
                name="EU AI Act Compliance Pack",
                description="Complete compliance package for EU AI Act requirements",
                regulatory_framework="eu_ai_act",
                monthly_fee_per_citizen=Decimal("150.00"),
                setup_fee=Decimal("2500.00"),
                features=[
                    "AI Act risk classification automation",
                    "Fundamental rights impact assessment",
                    "Transparency obligations management",
                    "Data governance compliance",
                    "Regulatory reporting automation"
                ],
                jurisdictions=["eu", "eea"]
            ),
            "financial_grade": CompliancePackage(
                package_id="financial_grade",
                name="Financial-Grade AI Governance",
                description="Enhanced governance for financial services AI systems",
                regulatory_framework="financial_regulation",
                monthly_fee_per_citizen=Decimal("300.00"),
                setup_fee=Decimal("5000.00"),
                features=[
                    "SOX compliance automation",
                    "Model risk management integration",
                    "Audit trail encryption (FIPS 140-2)",
                    "Financial regulatory reporting",
                    "Business continuity planning"
                ],
                jurisdictions=["us", "eu", "global"]
            ),
            "healthcare_compliance": CompliancePackage(
                package_id="healthcare_compliance",
                name="Healthcare AI Compliance Pack",
                description="HIPAA and healthcare regulatory compliance",
                regulatory_framework="healthcare",
                monthly_fee_per_citizen=Decimal("250.00"),
                setup_fee=Decimal("3500.00"),
                features=[
                    "HIPAA compliance automation",
                    "PHI data handling controls",
                    "Healthcare regulatory reporting",
                    "Patient privacy protection",
                    "Medical device integration"
                ],
                jurisdictions=["us", "global"]
            )
        }

    def create_citizen_billing_account(self, citizen_id: str, tenant_id: str,
                                     pricing_tier: str, initial_credits: Decimal = Decimal("0.00"),
                                     compliance_packages: List[str] = None) -> CitizenBillingAccount:
        """
        Create a billing account for a new AI citizen.

        Args:
            citizen_id: The citizen identifier
            tenant_id: The tenant/organization identifier
            pricing_tier: The pricing tier to use
            initial_credits: Initial credit balance
            compliance_packages: List of compliance package IDs

        Returns:
            The created billing account
        """
        import sqlite3

        account = CitizenBillingAccount(
            citizen_id=citizen_id,
            tenant_id=tenant_id,
            pricing_tier=pricing_tier,
            compliance_packages=compliance_packages or [],
            credit_balance=initial_credits
        )

        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            INSERT INTO citizen_billing_accounts (
                citizen_id, tenant_id, pricing_tier, compliance_packages,
                credit_balance, auto_recharge_threshold, auto_recharge_amount,
                billing_cycle_start, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account.citizen_id, account.tenant_id, account.pricing_tier,
            json.dumps(account.compliance_packages), str(account.credit_balance),
            str(account.auto_recharge_threshold), str(account.auto_recharge_amount),
            account.billing_cycle_start, account.status
        ))
        conn.commit()
        conn.close()

        # Charge citizenship fee
        tier = self.pricing_tiers.get(pricing_tier)
        if tier:
            self._charge_transaction(citizen_id, tenant_id, "citizenship_fee",
                                   tier.base_citizenship_fee,
                                   f"Citizenship issuance fee - {tier.name}")

        self.logger.info("Citizen billing account created",
                        citizen_id=citizen_id,
                        tenant_id=tenant_id,
                        tier=pricing_tier,
                        initial_credits=str(initial_credits))

        return account

    def _charge_transaction(self, citizen_id: str, tenant_id: str, transaction_type: str,
                          amount: Decimal, description: str,
                          reference_id: Optional[str] = None) -> BillingTransaction:
        """Create and process a billing transaction."""
        import sqlite3

        transaction = BillingTransaction(
            citizen_id=citizen_id,
            tenant_id=tenant_id,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            reference_id=reference_id
        )

        # Deduct from credit balance
        conn = sqlite3.connect(self.billing_db_path)
        conn.execute("""
            UPDATE citizen_billing_accounts
            SET credit_balance = credit_balance - ?
            WHERE citizen_id = ?
        """, (str(amount), citizen_id))

        # Record transaction
        conn.execute("""
            INSERT INTO billing_transactions (
                transaction_id, citizen_id, tenant_id, transaction_type,
                amount, currency, description, reference_id, timestamp, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction.transaction_id, transaction.citizen_id, transaction.tenant_id,
            transaction.transaction_type, str(transaction.amount), transaction.currency,
            transaction.description, transaction.reference_id, transaction.timestamp,
            transaction.status
        ))

        conn.commit()
        conn.close()

        # Check if auto-recharge needed
        self._check_auto_recharge(citizen_id)

        return transaction

    def _check_auto_recharge(self, citizen_id: str) -> None:
        """Check if auto-recharge is needed for a citizen."""
        import sqlite3

        conn = sqlite3.connect(self.billing_db_path)
        cursor = conn.execute("""
            SELECT credit_balance, auto_recharge_threshold, auto_recharge_amount
            FROM citizen_billing_accounts
            WHERE citizen_id = ? AND status = 'active'
        """, (citizen_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            balance = Decimal(row[0])
            threshold = Decimal(row[1])
            recharge_amount = Decimal(row[2])

            if balance <= threshold:
                # Simulate payment processing
                self.logger.info("Auto-recharge triggered",
                               citizen_id=citizen_id,
                               balance=str(balance),
                               threshold=str(threshold),
                               recharge_amount=str(recharge_amount))

                # In production, this would integrate with payment processors
                # For now, just add credits
                conn = sqlite3.connect(self.billing_db_path)
                conn.execute("""
                    UPDATE citizen_billing_accounts
                    SET credit_balance = credit_balance + ?
                    WHERE citizen_id = ?
                """, (str(recharge_amount), citizen_id))

                # Record recharge transaction
                transaction_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO billing_transactions (
                        transaction_id, citizen_id, tenant_id, transaction_type,
                        amount, currency, description, timestamp, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction_id, citizen_id, citizen_id.split('_')[0],  # tenant from citizen_id
                    "credit_recharge", str(recharge_amount), "USD",
                    f"Auto-recharge - {recharge_amount} credits",
                    datetime.utcnow().isoformat() + "Z", "completed"
                ))

                conn.commit()
                conn.close()

    def charge_governance_decision(self, citizen_id: str, decision_type: str,
                                 reference_id: Optional[str] = None) -> bool:
        """
        Charge for a governance decision.

        Args:
            citizen_id: The citizen making the decision
            decision_type: Type of decision
            reference_id: Reference to the decision event

        Returns:
            True if charge successful, False if insufficient credits
        """
        # Get pricing tier
        account = self.get_citizen_billing_account(citizen_id)
        if not account:
            return False

        tier = self.pricing_tiers.get(account.pricing_tier)
        if not tier:
            return False

        # Calculate fee with compliance multiplier
        base_fee = tier.per_decision_fee
        multiplier = tier.compliance_addon_multiplier if account.compliance_packages else Decimal("1.0")
        fee = base_fee * multiplier

        # Check balance
        if account.credit_balance < fee:
            self.logger.warning("Insufficient credits for governance decision",
                              citizen_id=citizen_id,
                              balance=str(account.credit_balance),
                              required=str(fee))
            return False

        # Charge the fee
        self._charge_transaction(
            citizen_id, account.tenant_id, "decision_fee", fee,
            f"Governance decision fee - {decision_type}",
            reference_id
        )

        return True

    def charge_certificate_verification(self, citizen_id: str,
                                      verification_type: str,
                                      reference_id: Optional[str] = None) -> bool:
        """
        Charge for certificate verification.

        Args:
            citizen_id: The citizen requesting verification
            verification_type: Type of verification
            reference_id: Reference to the verification event

        Returns:
            True if charge successful
        """
        account = self.get_citizen_billing_account(citizen_id)
        if not account:
            return False

        tier = self.pricing_tiers.get(account.pricing_tier)
        if not tier:
            return False

        fee = tier.per_verification_fee
        multiplier = tier.compliance_addon_multiplier if account.compliance_packages else Decimal("1.0")
        fee = fee * multiplier

        if account.credit_balance < fee:
            return False

        self._charge_transaction(
            citizen_id, account.tenant_id, "verification_fee", fee,
            f"Certificate verification fee - {verification_type}",
            reference_id
        )

        return True

    def process_monthly_billing(self) -> Dict[str, any]:
        """
        Process monthly billing cycle for all active citizens.

        Returns:
            Billing processing results
        """
        import sqlite3

        conn = sqlite3.connect(self.billing_db_path)
        cursor = conn.execute("""
            SELECT citizen_id, tenant_id, pricing_tier, compliance_packages
            FROM citizen_billing_accounts
            WHERE status = 'active'
        """)

        processed = 0
        total_billed = Decimal("0.00")

        for row in cursor.fetchall():
            citizen_id, tenant_id, pricing_tier, compliance_packages_json = row

            tier = self.pricing_tiers.get(pricing_tier)
            if not tier:
                continue

            # Base subscription
            subscription_fee = tier.monthly_subscription

            # Add compliance package fees
            compliance_packages = json.loads(compliance_packages_json) if compliance_packages_json else []
            compliance_fee = Decimal("0.00")

            for package_id in compliance_packages:
                package = self.compliance_packages.get(package_id)
                if package:
                    compliance_fee += package.monthly_fee_per_citizen

            total_fee = subscription_fee + compliance_fee

            # Create billing transaction
            self._charge_transaction(
                citizen_id, tenant_id, "subscription",
                total_fee, f"Monthly subscription - {tier.name}"
            )

            processed += 1
            total_billed += total_fee

        conn.close()

        result = {
            "accounts_processed": processed,
            "total_billed": str(total_billed),
            "billing_cycle": datetime.utcnow().strftime("%Y-%m"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        self.logger.info("Monthly billing processed", **result)
        return result

    def get_citizen_billing_account(self, citizen_id: str) -> Optional[CitizenBillingAccount]:
        """Get billing account for a citizen."""
        import sqlite3

        conn = sqlite3.connect(self.billing_db_path)
        cursor = conn.execute("""
            SELECT citizen_id, tenant_id, pricing_tier, compliance_packages,
                   credit_balance, auto_recharge_threshold, auto_recharge_amount,
                   payment_method, billing_cycle_start, status
            FROM citizen_billing_accounts
            WHERE citizen_id = ?
        """, (citizen_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return CitizenBillingAccount(
                citizen_id=row[0],
                tenant_id=row[1],
                pricing_tier=row[2],
                compliance_packages=json.loads(row[3]) if row[3] else [],
                credit_balance=Decimal(row[4]),
                auto_recharge_threshold=Decimal(row[5]),
                auto_recharge_amount=Decimal(row[6]),
                payment_method=row[7],
                billing_cycle_start=row[8],
                status=row[9]
            )
        return None

    def generate_revenue_report(self, period_start: str, period_end: str) -> RevenueAnalytics:
        """
        Generate revenue analytics report for a period.

        Args:
            period_start: Start date (ISO format)
            period_end: End date (ISO format)

        Returns:
            Revenue analytics for the period
        """
        import sqlite3

        conn = sqlite3.connect(self.billing_db_path)

        # Get transaction data
        cursor = conn.execute("""
            SELECT transaction_type, amount, citizen_id
            FROM billing_transactions
            WHERE timestamp >= ? AND timestamp <= ? AND status = 'completed'
        """, (period_start, period_end))

        transactions = cursor.fetchall()

        # Calculate metrics
        total_revenue = Decimal("0.00")
        revenue_by_type = {}
        revenue_by_tier = {}
        revenue_by_jurisdiction = {}
        unique_citizens = set()
        decisions_count = 0

        for transaction_type, amount_str, citizen_id in transactions:
            amount = Decimal(amount_str)
            total_revenue += amount
            unique_citizens.add(citizen_id)

            # Revenue by type
            revenue_by_type[transaction_type] = revenue_by_type.get(transaction_type, Decimal("0.00")) + amount

            # Count decisions
            if transaction_type == "decision_fee":
                decisions_count += 1

        # Get citizen tier/jurisdiction data
        citizen_tiers = {}
        for citizen_id in unique_citizens:
            account = self.get_citizen_billing_account(citizen_id)
            if account:
                tier = self.pricing_tiers.get(account.pricing_tier)
                if tier:
                    citizen_tiers[citizen_id] = (tier.trust_level, tier.jurisdiction)

                    # Revenue by tier/jurisdiction (simplified attribution)
                    revenue_by_tier[tier.trust_level] = revenue_by_tier.get(tier.trust_level, Decimal("0.00")) + (total_revenue / len(unique_citizens))
                    revenue_by_jurisdiction[tier.jurisdiction] = revenue_by_jurisdiction.get(tier.jurisdiction, Decimal("0.00")) + (total_revenue / len(unique_citizens))

        # Calculate derived metrics
        active_citizens = len(unique_citizens)
        average_revenue_per_citizen = total_revenue / active_citizens if active_citizens > 0 else Decimal("0.00")

        # Simplified churn rate (would need historical data)
        churn_rate = Decimal("5.0")  # Placeholder

        analytics = RevenueAnalytics(
            period_start=period_start,
            period_end=period_end,
            total_revenue=total_revenue,
            revenue_by_type=revenue_by_type,
            revenue_by_tier=revenue_by_tier,
            revenue_by_jurisdiction=revenue_by_jurisdiction,
            new_citizens=active_citizens,  # Simplified
            active_citizens=active_citizens,
            total_decisions=decisions_count,
            average_revenue_per_citizen=average_revenue_per_citizen,
            churn_rate=churn_rate
        )

        # Store analytics
        conn.execute("""
            INSERT OR REPLACE INTO revenue_analytics (
                period_start, period_end, total_revenue, revenue_by_type,
                revenue_by_tier, revenue_by_jurisdiction, new_citizens,
                active_citizens, total_decisions, average_revenue_per_citizen,
                churn_rate, growth_metrics, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analytics.period_start, analytics.period_end, str(analytics.total_revenue),
            json.dumps({k: str(v) for k, v in analytics.revenue_by_type.items()}),
            json.dumps({k: str(v) for k, v in analytics.revenue_by_tier.items()}),
            json.dumps({k: str(v) for k, v in analytics.revenue_by_jurisdiction.items()}),
            analytics.new_citizens, analytics.active_citizens, analytics.total_decisions,
            str(analytics.average_revenue_per_citizen), str(analytics.churn_rate),
            json.dumps(analytics.growth_metrics), datetime.utcnow().isoformat() + "Z"
        ))

        conn.commit()
        conn.close()

        self.logger.info("Revenue report generated",
                        period=f"{period_start} to {period_end}",
                        total_revenue=str(total_revenue),
                        active_citizens=active_citizens)

        return analytics

    def get_pricing_recommendation(self, citizen_profile: Dict[str, any]) -> Dict[str, any]:
        """
        Get pricing tier recommendation based on citizen profile.

        Args:
            citizen_profile: Profile data including trust_level, jurisdiction, expected_usage

        Returns:
            Recommended pricing tier with rationale
        """
        trust_level = citizen_profile.get("trust_level", "low")
        jurisdiction = citizen_profile.get("jurisdiction", "us")
        expected_decisions = citizen_profile.get("expected_decisions_per_month", 1000)
        compliance_needs = citizen_profile.get("compliance_requirements", [])

        # Find best matching tier
        best_tier = None
        best_score = 0

        for tier_id, tier in self.pricing_tiers.items():
            score = 0

            # Trust level match
            if tier.trust_level == trust_level:
                score += 40

            # Jurisdiction match
            if tier.jurisdiction == jurisdiction:
                score += 30

            # Usage cost estimation
            monthly_decision_cost = tier.per_decision_fee * expected_decisions
            if monthly_decision_cost < 100:  # Reasonable threshold
                score += 20

            # Compliance multiplier consideration
            if compliance_needs and tier.compliance_addon_multiplier > 1:
                score += 10

            if score > best_score:
                best_score = score
                best_tier = tier

        if best_tier:
            # Estimate monthly cost
            base_subscription = best_tier.monthly_subscription
            decision_costs = best_tier.per_decision_fee * expected_decisions
            total_monthly = base_subscription + decision_costs

            return {
                "recommended_tier": best_tier.tier_id,
                "tier_name": best_tier.name,
                "estimated_monthly_cost": str(total_monthly),
                "breakdown": {
                    "subscription": str(base_subscription),
                    "decisions": str(decision_costs),
                    "compliance_multiplier": str(best_tier.compliance_addon_multiplier)
                },
                "features": best_tier.features,
                "confidence_score": best_score
            }

        return {"error": "No suitable pricing tier found"}


# Global infrastructure revenue engine instance
infrastructure_revenue = InfrastructureRevenueEngine()
