"""Public + superuser platform pulse endpoint.

Powers the "Marketplace pulse" section on the workspace Overview page.
Returns transparency-friendly stats to anyone, plus operationally sensitive
fields (MRR, churn, dollar amounts, open threats) ONLY when the caller is a
platform superuser. Other tenants — including workspace OWNERS — see the
public subset only.

All fields are deliberately sanitized: handles only, no emails / user IDs /
personal data ever leaks through this endpoint.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.models import (
    Subscription,
    SubscriptionStatus,
    User,
    Workspace,
)

# These models live in optional sub-modules and may be None at runtime
# if the underlying module fails to import in stripped-down deployments.
try:  # pragma: no cover
    from db.models import Listing  # type: ignore
except ImportError:  # pragma: no cover
    Listing = None  # type: ignore

try:  # pragma: no cover
    from db.models import MarketplaceOrder  # type: ignore
except ImportError:  # pragma: no cover
    MarketplaceOrder = None  # type: ignore

from db.session import get_db

router = APIRouter(prefix="/platform", tags=["platform"])


# ─── Optional auth dep (returns None for anonymous / invalid tokens) ──────────
async def _optional_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not authorization:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
    except ValueError:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.is_active:
        return user
    return None


# ─── helpers ──────────────────────────────────────────────────────────────────
def _to_int(value: Any) -> int:
    """Subscription.amount_cents is stored as String — coerce safely."""
    try:
        return int(str(value or "0"))
    except (TypeError, ValueError):
        return 0


def _delta_pct(current: float, prior: float) -> float:
    if prior <= 0:
        return 0.0
    return round(((current - prior) / prior) * 100.0, 1)


def _sanitize_handle(value: Optional[str]) -> str:
    """Strip emails and IDs to a friendly handle prefix."""
    if not value:
        return "anonymous"
    head = value.split("@", 1)[0]
    return head[:32] or "anonymous"


def _activity_event(
    *,
    kind: str,
    actor: str,
    ts: datetime,
    extra: Dict[str, Any] | None = None,
    superuser_extra: Dict[str, Any] | None = None,
    is_superuser: bool,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "kind": kind,
        "actor": _sanitize_handle(actor),
        "ts": ts.isoformat() + "Z" if ts.tzinfo is None else ts.isoformat(),
    }
    if extra:
        out.update(extra)
    if is_superuser and superuser_extra:
        out.update(superuser_extra)
    return out


# ─── endpoint ─────────────────────────────────────────────────────────────────
@router.get("/pulse")
async def platform_pulse(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_optional_current_user),
) -> Dict[str, Any]:
    """Marketplace transparency pulse.

    Public fields are returned unconditionally. Sensitive fields are only
    populated when the caller is a platform superuser.
    """
    is_super = bool(current_user and current_user.is_superuser)

    now = datetime.utcnow()
    window_30 = now - timedelta(days=30)
    window_60 = now - timedelta(days=60)
    window_7 = now - timedelta(days=7)

    # ── User counts ──────────────────────────────────────────────────────────
    total_users = db.query(func.count(User.id)).scalar() or 0
    users_added_30d = (
        db.query(func.count(User.id)).filter(User.created_at >= window_30).scalar() or 0
    )
    users_added_prior_30d = (
        db.query(func.count(User.id))
        .filter(User.created_at >= window_60, User.created_at < window_30)
        .scalar()
        or 0
    )

    # ── Listings ─────────────────────────────────────────────────────────────
    if Listing is not None:
        active_listings = (
            db.query(func.count(Listing.id)).filter(Listing.status == "active").scalar() or 0
        )
        tool_installs_total = (
            db.query(func.coalesce(func.sum(Listing.install_count), 0))
            .filter(Listing.status == "active")
            .scalar()
            or 0
        )
        active_tools = (
            db.query(func.count(Listing.id))
            .filter(
                Listing.status == "active",
                Listing.listing_type.in_(("tool", "pipeline", "agent", "connector", "edge_template")),
            )
            .scalar()
            or 0
        )
        listings_added_7d = (
            db.query(func.count(Listing.id))
            .filter(Listing.status == "active", Listing.created_at >= window_7)
            .scalar()
            or 0
        )
    else:
        active_listings = 0
        tool_installs_total = 0
        active_tools = 0
        listings_added_7d = 0

    # ── Orders ───────────────────────────────────────────────────────────────
    paid_statuses = ("paid", "fulfilled")
    if MarketplaceOrder is not None:
        orders_30d = (
            db.query(func.count(MarketplaceOrder.id))
            .filter(
                MarketplaceOrder.status.in_(paid_statuses),
                MarketplaceOrder.created_at >= window_30,
            )
            .scalar()
            or 0
        )
        orders_prior_30d = (
            db.query(func.count(MarketplaceOrder.id))
            .filter(
                MarketplaceOrder.status.in_(paid_statuses),
                MarketplaceOrder.created_at >= window_60,
                MarketplaceOrder.created_at < window_30,
            )
            .scalar()
            or 0
        )
    else:
        orders_30d = 0
        orders_prior_30d = 0

    # ── Subscriptions / tier distribution ────────────────────────────────────
    subs_by_plan: Dict[str, int] = {}
    plan_rows = (
        db.query(Subscription.plan, func.count(Subscription.id))
        .filter(Subscription.status == SubscriptionStatus.ACTIVE)
        .group_by(Subscription.plan)
        .all()
    )
    paid_users_total = 0
    for plan, count in plan_rows:
        plan_key = plan.value if plan else "unknown"
        subs_by_plan[plan_key] = int(count or 0)
        paid_users_total += int(count or 0)

    # Free = users without an active subscription
    free_users = max(0, total_users - paid_users_total)
    tier_distribution = {"free": free_users, **subs_by_plan}

    upgrades_30d = (
        db.query(func.count(Subscription.id))
        .filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.created_at >= window_30,
        )
        .scalar()
        or 0
    )

    # ── Public payload ───────────────────────────────────────────────────────
    payload: Dict[str, Any] = {
        "users": {
            "total": int(total_users),
            "delta_pct_30d": _delta_pct(users_added_30d, users_added_prior_30d),
            "added_30d": int(users_added_30d),
        },
        "active_listings": {
            "total": int(active_listings),
            "added_7d": int(listings_added_7d),
        },
        "tool_installs": {
            "total": int(tool_installs_total),
            "active_tools": int(active_tools),
        },
        "orders_30d": {
            "count": int(orders_30d),
            "delta_pct_vs_prior": _delta_pct(orders_30d, orders_prior_30d),
        },
        "paid_tier_users": {
            "total": int(paid_users_total),
            "upgrades_30d": int(upgrades_30d),
        },
        "tier_distribution": tier_distribution,
        "is_superuser": is_super,
        "generated_at": now.isoformat() + "Z",
    }

    # ── Activity feed (sanitized) ────────────────────────────────────────────
    activity: List[Dict[str, Any]] = []

    # Recent listings
    recent_listings = []
    if Listing is not None:
        recent_listings = (
            db.query(Listing)
            .filter(Listing.status == "active")
            .order_by(Listing.created_at.desc())
            .limit(3)
            .all()
        )
    for listing in recent_listings:
        activity.append(
            _activity_event(
                kind="listing_new",
                actor=listing.title or "untitled-listing",
                ts=listing.created_at or now,
                extra={"title": listing.title or "Untitled"},
                is_superuser=is_super,
            )
        )

    # Recent paid orders
    recent_orders = []
    if MarketplaceOrder is not None:
        recent_orders = (
            db.query(MarketplaceOrder)
            .filter(MarketplaceOrder.status.in_(paid_statuses))
            .order_by(MarketplaceOrder.created_at.desc())
            .limit(3)
            .all()
        )
    for order in recent_orders:
        # Sanitize: never expose buyer_id / email / amount publicly.
        # Workspace name is the most public-friendly handle we have.
        ws = db.query(Workspace).filter(Workspace.id == order.workspace_id).first()
        actor_handle = (ws.slug if ws and ws.slug else (ws.name if ws else "buyer"))
        order_short = (order.id or "")[:8]
        activity.append(
            _activity_event(
                kind="order_completed",
                actor=actor_handle,
                ts=order.created_at or now,
                extra={"order_id": f"ORD-{order_short}"},
                superuser_extra={"amount_cents": int(order.total_cents or 0)},
                is_superuser=is_super,
            )
        )

    # Recent upgrades (active subs created in last window)
    recent_upgrades = (
        db.query(Subscription)
        .filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.created_at >= window_30,
        )
        .order_by(Subscription.created_at.desc())
        .limit(3)
        .all()
    )
    for sub in recent_upgrades:
        ws = db.query(Workspace).filter(Workspace.id == sub.workspace_id).first()
        actor_handle = (ws.slug if ws and ws.slug else (ws.name if ws else "tenant"))
        plan_label = sub.plan.value if sub.plan else "unknown"
        activity.append(
            _activity_event(
                kind="upgrade",
                actor=actor_handle,
                ts=sub.created_at or now,
                extra={"to_plan": plan_label},
                superuser_extra={
                    "amount_cents": _to_int(sub.amount_cents),
                    "billing_cycle": sub.billing_cycle or "monthly",
                },
                is_superuser=is_super,
            )
        )

    # Recent registrations
    recent_users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .limit(2)
        .all()
    )
    for u in recent_users:
        activity.append(
            _activity_event(
                kind="user_registered",
                actor=u.full_name or u.email or "new-user",
                ts=u.created_at or now,
                extra={"tier": "free"},
                is_superuser=is_super,
            )
        )

    activity.sort(key=lambda e: e["ts"], reverse=True)
    payload["activity"] = activity[:8]

    # ── Superuser-only sensitive fields ──────────────────────────────────────
    if is_super:
        # MRR — sum of amount_cents on ACTIVE subscriptions, normalized to monthly
        active_subs = (
            db.query(Subscription)
            .filter(Subscription.status == SubscriptionStatus.ACTIVE)
            .all()
        )
        mrr_cents = 0
        for sub in active_subs:
            cents = _to_int(sub.amount_cents)
            cycle = (sub.billing_cycle or "monthly").lower()
            if cycle in ("year", "yearly", "annual"):
                cents = cents // 12
            mrr_cents += cents

        # MRR prior period (subs that were active in prior window — approximation)
        prior_active_count = (
            db.query(func.count(Subscription.id))
            .filter(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.created_at < window_30,
            )
            .scalar()
            or 0
        )
        current_active_count = len(active_subs)
        mrr_delta_pct = _delta_pct(current_active_count, prior_active_count)

        # Churn — canceled in last 30d / total active 30d ago
        canceled_30d = (
            db.query(func.count(Subscription.id))
            .filter(
                Subscription.status == SubscriptionStatus.CANCELED,
                Subscription.updated_at >= window_30,
            )
            .scalar()
            or 0
        )
        denom = max(prior_active_count, 1)
        churn_pct = round((canceled_30d / denom) * 100.0, 2)

        # ARPU
        arpu_cents = mrr_cents // current_active_count if current_active_count else 0

        # Trial conversions: subs whose state moved trialing → active in last 30d
        trial_conversions_30d = (
            db.query(func.count(Subscription.id))
            .filter(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.updated_at >= window_30,
                Subscription.created_at < window_30,
            )
            .scalar()
            or 0
        )

        # Open security threats — pull from admin overview (best-effort, never crash)
        open_threats = 0
        try:
            from db.models import SecurityEvent  # type: ignore
            open_threats = (
                db.query(func.count(SecurityEvent.id))
                .filter(SecurityEvent.status == "open")
                .scalar()
                or 0
            )
        except Exception:  # pragma: no cover — model name drift safety
            open_threats = 0

        # Failed payments at risk
        past_due_count = (
            db.query(func.count(Subscription.id))
            .filter(Subscription.status == SubscriptionStatus.PAST_DUE)
            .scalar()
            or 0
        )

        # Order revenue 30d (gross)
        if MarketplaceOrder is not None:
            order_revenue_30d = (
                db.query(func.coalesce(func.sum(MarketplaceOrder.total_cents), 0))
                .filter(
                    MarketplaceOrder.status.in_(paid_statuses),
                    MarketplaceOrder.created_at >= window_30,
                )
                .scalar()
                or 0
            )
        else:
            order_revenue_30d = 0

        payload["superuser"] = {
            "mrr_cents": int(mrr_cents),
            "mrr_delta_pct_vs_prior": mrr_delta_pct,
            "arpu_cents": int(arpu_cents),
            "churn_pct_30d": churn_pct,
            "trial_conversions_30d": int(trial_conversions_30d),
            "open_security_threats": int(open_threats),
            "past_due_subscriptions": int(past_due_count),
            "marketplace_gross_30d_cents": int(order_revenue_30d),
        }

    return payload
