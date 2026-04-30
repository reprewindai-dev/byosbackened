"""License enforcement layer.

This module is the single source of truth for:
- Tier feature gates (what each plan is allowed to do)
- Trial TTL enforcement (14-day trial expiry)
- License status checks (active, trialing, expired, free)

Usage in routers:
    from core.license import require_active_license, require_feature
    from core.license import LicenseStatus, TIER_FEATURES

Dependency injection:
    @router.get("/some-endpoint")
    async def endpoint(
        license_status: LicenseStatus = Depends(require_active_license),
        current_user: User = Depends(get_current_user),
    ):
        require_feature(license_status.tier, "audit_logs")  # raises 403 if not allowed
        ...
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from db.session import get_db


# ─── Tier constants ────────────────────────────────────────────────────────────
# These string values match the PlanTier enum values already in db/models.py.
# Do NOT rename without a corresponding Alembic migration.

TIER_FREE = "free"
TIER_TEAM = "starter"        # DB enum value: starter → display name: Team
TIER_BUSINESS = "pro"        # DB enum value: pro     → display name: Business
TIER_ENTERPRISE = "enterprise"

# Ordered for comparison (higher index = more capable)
TIER_ORDER = [TIER_FREE, TIER_TEAM, TIER_BUSINESS, TIER_ENTERPRISE]


def tier_gte(tier: str, minimum: str) -> bool:
    """Return True if `tier` is equal to or above `minimum` in the tier hierarchy."""
    try:
        return TIER_ORDER.index(tier) >= TIER_ORDER.index(minimum)
    except ValueError:
        return False


# ─── Feature gate catalog ──────────────────────────────────────────────────────
# Each key is a feature flag string used by `require_feature()`.
# Values are the minimum tier required to access that feature.
# Adding a new feature: add a key here + call require_feature() in the router.

FEATURE_MIN_TIER: dict[str, str] = {
    # Routing
    "multi_vendor_routing":   TIER_TEAM,
    "advanced_routing":       TIER_TEAM,
    "failover_routing":       TIER_BUSINESS,
    "custom_routing":         TIER_ENTERPRISE,

    # Cost intelligence
    "cost_dashboard":         TIER_TEAM,
    "budget_controls":        TIER_TEAM,
    "kill_switch":            TIER_TEAM,
    "savings_insights":       TIER_TEAM,

    # Audit & compliance
    "audit_logs":             TIER_TEAM,
    "audit_exports":          TIER_BUSINESS,
    "compliance_reports":     TIER_BUSINESS,
    "gdpr_exports":           TIER_BUSINESS,
    "hipaa_controls":         TIER_BUSINESS,

    # Security & privacy
    "rbac":                   TIER_TEAM,
    "sso":                    TIER_BUSINESS,
    "content_safety":         TIER_BUSINESS,
    "data_masking":           TIER_BUSINESS,
    "privacy_audit_trail":    TIER_BUSINESS,
    "locker_security":        TIER_BUSINESS,
    "advanced_security":      TIER_ENTERPRISE,
    "private_deployment":     TIER_ENTERPRISE,

    # Plugins & execution
    "plugin_execution":       TIER_BUSINESS,
    "governed_execution":     TIER_BUSINESS,
    "custom_endpoints":       TIER_ENTERPRISE,

    # Administration
    "workspace_admin":        TIER_ENTERPRISE,
    "white_label":            TIER_ENTERPRISE,
    "annual_review":          TIER_ENTERPRISE,

    # API keys
    "unlimited_api_keys":     TIER_BUSINESS,
}

# Per-tier API key limits (None = unlimited)
TIER_API_KEY_LIMITS: dict[str, Optional[int]] = {
    TIER_FREE:       1,
    TIER_TEAM:       20,
    TIER_BUSINESS:   100,
    TIER_ENTERPRISE: None,
}

# Per-tier monthly request limits (None = unlimited)
TIER_REQUEST_LIMITS: dict[str, Optional[int]] = {
    TIER_FREE:       100_000,
    TIER_TEAM:       None,
    TIER_BUSINESS:   None,
    TIER_ENTERPRISE: None,
}

# Per-tier vendor connection limits (None = unlimited)
TIER_VENDOR_LIMITS: dict[str, Optional[int]] = {
    TIER_FREE:       3,
    TIER_TEAM:       None,
    TIER_BUSINESS:   None,
    TIER_ENTERPRISE: None,
}


# ─── License status object ─────────────────────────────────────────────────────

class LicenseState(str, Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    EXPIRED = "expired"
    FREE = "free"


class LicenseStatus:
    """Resolved license status for the current workspace.

    Attached to every request that uses `require_active_license`.
    Routers can inspect `.tier`, `.state`, `.days_remaining`.
    """

    def __init__(
        self,
        tier: str,
        state: LicenseState,
        trial_end: Optional[datetime] = None,
        workspace_id: Optional[str] = None,
    ):
        self.tier = tier
        self.state = state
        self.trial_end = trial_end
        self.workspace_id = workspace_id

    @property
    def is_paid(self) -> bool:
        return self.state in (LicenseState.ACTIVE, LicenseState.TRIALING)

    @property
    def days_remaining(self) -> Optional[int]:
        if self.trial_end and self.state == LicenseState.TRIALING:
            delta = self.trial_end - datetime.utcnow()
            return max(0, delta.days)
        return None

    @property
    def display_tier(self) -> str:
        """Human-friendly tier name for API responses and UI."""
        mapping = {
            TIER_FREE:       "Free",
            TIER_TEAM:       "Team",
            TIER_BUSINESS:   "Business",
            TIER_ENTERPRISE: "Enterprise",
        }
        return mapping.get(self.tier, self.tier.title())


# ─── Feature gate helper ───────────────────────────────────────────────────────

def require_feature(tier: str, feature: str) -> None:
    """Raise HTTP 403 if `tier` does not include `feature`.

    Call this inside any router that is gated to a specific tier.

    Example:
        require_feature(license_status.tier, "audit_logs")
    """
    min_tier = FEATURE_MIN_TIER.get(feature)
    if min_tier is None:
        # Feature not in catalog — allow by default (avoids silent lock-outs on new features)
        return
    if not tier_gte(tier, min_tier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Feature '{feature}' requires {min_tier.title()} plan or above. "
                f"Current plan: {tier.title()}. Upgrade at /settings/billing."
            ),
        )


# ─── FastAPI dependency ────────────────────────────────────────────────────────

async def require_active_license(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LicenseStatus:
    """FastAPI dependency — resolves and enforces workspace license.

    - Free tier users pass through with LicenseState.FREE
    - Trialing users pass through with LicenseState.TRIALING (14-day window)
    - Expired trials are blocked with HTTP 402
    - Active paid subscriptions pass through with LicenseState.ACTIVE

    Returns a LicenseStatus object that routers can inspect for tier-gating.
    """
    from db.models import Subscription, SubscriptionStatus, Workspace

    workspace_id = current_user.workspace_id

    # 1. Check live Stripe subscription first
    sub = db.query(Subscription).filter(
        Subscription.workspace_id == workspace_id
    ).first()

    if sub and sub.status == SubscriptionStatus.ACTIVE:
        return LicenseStatus(
            tier=sub.plan.value,
            state=LicenseState.ACTIVE,
            workspace_id=workspace_id,
        )

    if sub and sub.status == SubscriptionStatus.TRIALING:
        trial_expired = sub.trial_end and sub.trial_end < datetime.utcnow()
        if trial_expired:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "Your 14-day trial has ended. "
                    "Upgrade to a Team, Business, or Enterprise license at /settings/billing."
                ),
            )
        return LicenseStatus(
            tier=sub.plan.value,
            state=LicenseState.TRIALING,
            trial_end=sub.trial_end,
            workspace_id=workspace_id,
        )

    # 2. Check workspace-level license key (manual / enterprise provisioning)
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if ws and ws.license_tier and ws.license_expires_at:
        if ws.license_expires_at > datetime.utcnow():
            return LicenseStatus(
                tier=ws.license_tier,
                state=LicenseState.TRIALING,
                trial_end=ws.license_expires_at,
                workspace_id=workspace_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "Your license has expired. "
                    "Contact sales@co2router.com or renew at /settings/billing."
                ),
            )

    # 3. Fall through to free tier — always allowed, never blocked
    return LicenseStatus(
        tier=TIER_FREE,
        state=LicenseState.FREE,
        workspace_id=workspace_id,
    )


async def require_paid_license(
    license_status: LicenseStatus = Depends(require_active_license),
) -> LicenseStatus:
    """Dependency variant — blocks free-tier users entirely.

    Use on endpoints that have no free-tier equivalent.
    """
    if not license_status.is_paid:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This feature requires a Team, Business, or Enterprise license.",
        )
    return license_status
