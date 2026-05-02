"""Financial and operational analytics services for workspace and platform dashboards."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
from typing import Any, Optional

from sqlalchemy import func

from db.models import (
    CostAllocation,
    Subscription,
    SubscriptionStatus,
    TokenTransaction,
    Workspace,
    WorkspaceRequestLog,
)


def _to_int(value: object) -> int:
    """Parse numeric strings or numbers into integer cents."""
    try:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _to_decimal(value: object, default: str = "0") -> Decimal:
    """Parse values safely for accounting math."""
    if value is None:
        value = default
    try:
        return Decimal(str(value))
    except (TypeError, InvalidOperation):
        try:
            return Decimal(default)
        except (TypeError, InvalidOperation):
            return Decimal("0")


def _resolve_window(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    default_days: int = 30,
) -> tuple[datetime, datetime]:
    """Resolve analytics window with sane defaults."""
    now = datetime.utcnow()
    if end_date is None:
        end_date = now
    if start_date is None:
        start_date = end_date - timedelta(days=default_days)
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def _subscription_monthly_revenue_cents(subscription: Subscription) -> int:
    """Normalize recurring subscription price to a monthly amount in cents."""
    amount = _to_int(subscription.amount_cents)
    cycle = (subscription.billing_cycle or "").lower()
    if cycle == "yearly":
        return amount // 12
    return amount


def _subscription_annual_revenue_cents(subscription: Subscription) -> int:
    """Normalize recurring subscription price to annual amount in cents."""
    amount = _to_int(subscription.amount_cents)
    cycle = (subscription.billing_cycle or "").lower()
    if cycle == "yearly":
        return amount
    return amount * 12


def _safe_parse_json(value: Optional[str]) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _cents_to_usd(cents: int) -> Decimal:
    return (_to_decimal(cents) / Decimal("100")).quantize(Decimal("0.000001"))


def _build_time_buckets(start_date: datetime, end_date: datetime) -> list[str]:
    total_days = max((end_date.date() - start_date.date()).days, 0) + 1
    return [(start_date + timedelta(days=i)).date().isoformat() for i in range(total_days)]


def fetch_token_pack_revenue(
    *,
    db,
    workspace_id: Optional[str],
    start_date: datetime,
    end_date: datetime,
) -> dict[str, Any]:
    """Return token pack sales and revenue from token transactions."""
    tx_query = db.query(TokenTransaction).filter(
        TokenTransaction.transaction_type == "purchase",
        TokenTransaction.created_at >= start_date,
        TokenTransaction.created_at <= end_date,
    )
    if workspace_id:
        tx_query = tx_query.filter(TokenTransaction.workspace_id == workspace_id)

    transactions = tx_query.all()

    by_pack: dict[str, dict[str, int | Decimal]] = defaultdict(
        lambda: {"transactions": 0, "credits": 0, "revenue_usd": Decimal("0")}
    )
    total_revenue_usd = Decimal("0")
    total_credits = 0

    for tx in transactions:
        payload = _safe_parse_json(tx.metadata_json)
        pack_name = str(payload.get("pack_name", "unknown"))
        pack_credits = _to_int(payload.get("credits", tx.amount))
        pack_price_cents = _to_int(payload.get("price_cents", 0))
        if pack_price_cents <= 0:
            # No recorded price, infer from absolute transaction delta when possible.
            pack_price_cents = _to_int(payload.get("credits_price_cents", 0))
        revenue_usd = _cents_to_usd(pack_price_cents)

        bucket = by_pack[pack_name]
        bucket["transactions"] = int(bucket["transactions"]) + 1
        bucket["credits"] = int(bucket["credits"]) + max(pack_credits, 0)
        bucket["revenue_usd"] = bucket["revenue_usd"] + revenue_usd

        total_revenue_usd += revenue_usd
        total_credits += max(pack_credits, 0)

    sorted_packs = sorted(
        (
            {
                "pack_name": pack_name,
                "transactions": int(values["transactions"]),
                "credits": int(values["credits"]),
                "revenue_usd": float(values["revenue_usd"]),
            }
            for pack_name, values in by_pack.items()
        ),
        key=lambda item: item["revenue_usd"],
        reverse=True,
    )

    return {
        "window": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "summary": {
            "transactions": len(transactions),
            "credits_sold": total_credits,
            "revenue_usd": float(total_revenue_usd),
        },
        "by_pack": sorted_packs,
    }


def fetch_workspace_request_metrics(
    db,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
    limit: int = 50,
    offset: int = 0,
    model: Optional[str] = None,
    request_path: Optional[str] = None,
    status: Optional[str] = None,
    include_rows: bool = False,
) -> dict[str, Any]:
    """Return workspace usage + request quality metrics."""
    base_query = db.query(WorkspaceRequestLog).filter(
        WorkspaceRequestLog.workspace_id == workspace_id,
        WorkspaceRequestLog.created_at >= start_date,
        WorkspaceRequestLog.created_at <= end_date,
    )
    if model:
        base_query = base_query.filter(WorkspaceRequestLog.model == model)
    if request_path:
        base_query = base_query.filter(WorkspaceRequestLog.request_path == request_path)
    if status:
        base_query = base_query.filter(WorkspaceRequestLog.status == status)

    total_requests = base_query.count()
    blocked_statuses = ("blocked", "blocked_by_budget", "blocked_by_tokens", "error", "denied")
    blocked_requests = base_query.filter(WorkspaceRequestLog.status.in_(blocked_statuses)).count()
    total_cost_row = db.query(func.coalesce(func.sum(WorkspaceRequestLog.cost_usd), 0)).filter(
        WorkspaceRequestLog.workspace_id == workspace_id,
        WorkspaceRequestLog.created_at >= start_date,
        WorkspaceRequestLog.created_at <= end_date,
    )
    if model:
        total_cost_row = total_cost_row.filter(WorkspaceRequestLog.model == model)
    if request_path:
        total_cost_row = total_cost_row.filter(WorkspaceRequestLog.request_path == request_path)
    if status:
        total_cost_row = total_cost_row.filter(WorkspaceRequestLog.status == status)
    total_cost = _to_decimal(total_cost_row.scalar())

    by_model_rows = (
        db.query(
            WorkspaceRequestLog.model.label("model"),
            func.count().label("requests"),
            func.coalesce(func.sum(WorkspaceRequestLog.cost_usd), 0).label("cost_usd"),
        )
        .filter(
            WorkspaceRequestLog.workspace_id == workspace_id,
            WorkspaceRequestLog.created_at >= start_date,
            WorkspaceRequestLog.created_at <= end_date,
        )
        .group_by(WorkspaceRequestLog.model)
    )
    by_model = [
        {
            "model": row.model or "unknown",
            "requests": int(row.requests or 0),
            "cost_usd": float(_to_decimal(row.cost_usd)),
        }
        for row in by_model_rows.all()
    ]

    by_path_rows = (
        db.query(
            WorkspaceRequestLog.request_path.label("path"),
            func.count().label("requests"),
            func.coalesce(func.sum(WorkspaceRequestLog.cost_usd), 0).label("cost_usd"),
        )
        .filter(
            WorkspaceRequestLog.workspace_id == workspace_id,
            WorkspaceRequestLog.created_at >= start_date,
            WorkspaceRequestLog.created_at <= end_date,
        )
        .group_by(WorkspaceRequestLog.request_path)
    )
    by_path = [
        {
            "request_path": row.path,
            "requests": int(row.requests or 0),
            "cost_usd": float(_to_decimal(row.cost_usd)),
        }
        for row in by_path_rows.all()
    ]

    daily_buckets = {bucket: {"requests": 0, "cost_usd": Decimal("0")} for bucket in _build_time_buckets(start_date, end_date)}
    request_rows = (
        db.query(
            WorkspaceRequestLog.created_at.label("created_at"),
            func.count().label("requests"),
            func.coalesce(func.sum(WorkspaceRequestLog.cost_usd), 0).label("cost_usd"),
        )
        .filter(
            WorkspaceRequestLog.workspace_id == workspace_id,
            WorkspaceRequestLog.created_at >= start_date,
            WorkspaceRequestLog.created_at <= end_date,
        )
        .group_by(func.date(WorkspaceRequestLog.created_at))
        .all()
    )
    for row in request_rows:
        key = row.created_at.date().isoformat()
        if key in daily_buckets:
            daily_buckets[key]["requests"] = int(row.requests or 0)
            daily_buckets[key]["cost_usd"] = _to_decimal(row.cost_usd)

    request_rows_sorted = db.query(WorkspaceRequestLog).filter(
        WorkspaceRequestLog.workspace_id == workspace_id,
        WorkspaceRequestLog.created_at >= start_date,
        WorkspaceRequestLog.created_at <= end_date,
    )
    if model:
        request_rows_sorted = request_rows_sorted.filter(WorkspaceRequestLog.model == model)
    if request_path:
        request_rows_sorted = request_rows_sorted.filter(WorkspaceRequestLog.request_path == request_path)
    if status:
        request_rows_sorted = request_rows_sorted.filter(WorkspaceRequestLog.status == status)

    recent_rows = request_rows_sorted.order_by(WorkspaceRequestLog.created_at.desc()).offset(offset).limit(limit).all()

    rows_payload = []
    if include_rows:
        rows_payload = [
            {
                "id": row.id,
                "request_path": row.request_path,
                "request_kind": row.request_kind,
                "model": row.model,
                "status": row.status,
                "tokens_in": int(row.tokens_in or 0),
                "tokens_out": int(row.tokens_out or 0),
                "latency_ms": int(row.latency_ms or 0),
                "cost_usd": float(_to_decimal(row.cost_usd)),
                "created_at": row.created_at.isoformat(),
            }
            for row in recent_rows
        ]

    avg_cost_per_request = 0
    if total_requests > 0:
        avg_cost_per_request = float(total_cost / Decimal(total_requests))

    return {
        "window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "totals": {
            "total_requests": total_requests,
            "blocked_requests": blocked_requests,
            "blocked_request_rate": (blocked_requests / total_requests * 100) if total_requests else 0.0,
            "total_cost_usd": float(total_cost),
            "avg_cost_per_request": avg_cost_per_request,
        },
        "by_model": by_model,
        "by_path": by_path,
        "daily_series": [
            {"date": date_key, "requests": bucket["requests"], "cost_usd": float(bucket["cost_usd"])}
            for date_key, bucket in sorted(daily_buckets.items())
        ],
        "rows": rows_payload,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "returned": len(rows_payload),
        },
    }


def workspace_financial_summary(
    db,
    workspace_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict[str, Any]:
    """Return a workspace-level financial summary for dashboard consumption."""
    start, end = _resolve_window(start_date=start_date, end_date=end_date, default_days=30)

    sub = db.query(Subscription).filter(Subscription.workspace_id == workspace_id).first()
    sub_plan = None
    sub_status = None
    sub_billing_cycle = "monthly"
    mrr_usd = Decimal("0")
    arr_usd = Decimal("0")
    if sub:
        sub_plan = sub.plan.value if sub.plan else None
        sub_status = sub.status.value if sub.status else None
        sub_billing_cycle = sub.billing_cycle or "monthly"
        mrr_usd = _cents_to_usd(_subscription_monthly_revenue_cents(sub))
        arr_usd = _cents_to_usd(_subscription_annual_revenue_cents(sub))

    token_pack_payload = fetch_token_pack_revenue(
        db=db,
        workspace_id=workspace_id,
        start_date=start,
        end_date=end,
    )
    request_payload = fetch_workspace_request_metrics(
        db=db,
        workspace_id=workspace_id,
        start_date=start,
        end_date=end,
        limit=0,
        offset=0,
        include_rows=False,
    )

    return {
        "workspace_id": workspace_id,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "subscription": {
            "plan": sub_plan,
            "status": sub_status,
            "billing_cycle": sub_billing_cycle,
            "monthly_revenue_usd": float(mrr_usd),
            "annual_revenue_usd": float(arr_usd),
        },
        "token_packs": token_pack_payload,
        "usage": request_payload["totals"],
        "daily_cost_series": request_payload["daily_series"],
        "by_model": request_payload["by_model"],
        "total_revenue_usd": float(_to_decimal(mrr_usd + _to_decimal(token_pack_payload["summary"]["revenue_usd"]))),
    }


def _active_subscriptions_count_at(
    db,
    workspace_ids: Optional[set[str]] = None,
) -> int:
    query = db.query(func.count(Subscription.id)).filter(
        Subscription.status == SubscriptionStatus.ACTIVE
    )
    if workspace_ids is not None:
        query = query.filter(Subscription.workspace_id.in_(workspace_ids))
    return query.scalar() or 0


def platform_financial_overview(
    db,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict[str, Any]:
    """Return platform financial KPIs for admin overview."""
    start, end = _resolve_window(start_date=start_date, end_date=end_date, default_days=30)

    subscription_rows = db.query(Subscription).filter(
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE])
    ).all()
    active_revenue_rows = [
        row for row in subscription_rows if row.status == SubscriptionStatus.ACTIVE
    ]

    mrr_cents = sum(_subscription_monthly_revenue_cents(row) for row in active_revenue_rows)
    arr_usd = sum(_subscription_annual_revenue_cents(row) for row in active_revenue_rows) / 100
    mrr_usd = mrr_cents / 100

    by_plan: dict[str, dict[str, int | float]] = {}
    plan_rows = (
        db.query(Subscription.plan, func.count(Subscription.id))
        .group_by(Subscription.plan)
        .all()
    )
    for plan, count in plan_rows:
        by_plan[plan.value if plan else "none"] = int(count or 0)

    started = (
        db.query(func.count(Subscription.id))
        .filter(Subscription.created_at >= start, Subscription.created_at <= end)
        .scalar()
        or 0
    )
    canceled = (
        db.query(func.count(Subscription.id))
        .filter(
            Subscription.status == SubscriptionStatus.CANCELED,
            Subscription.canceled_at != None,
            Subscription.canceled_at >= start,
            Subscription.canceled_at <= end,
        )
        .scalar()
        or 0
    )

    active_workspace_rows = (
        db.query(Workspace.id)
        .join(Subscription, Subscription.workspace_id == Workspace.id)
        .filter(Workspace.is_active.is_(True))
        .all()
    )
    active_workspaces = len({row.id for row in active_workspace_rows})

    # Churn proxy: canceled subscriptions against active baseline at period start.
    period_start_active = _active_subscriptions_count_at(
        db,
        None,
    )
    churn_rate = (canceled / period_start_active * 100) if period_start_active else 0.0

    token_pack_payload = fetch_token_pack_revenue(
        db=db,
        workspace_id=None,
        start_date=start,
        end_date=end,
    )

    request_rows = (
        db.query(WorkspaceRequestLog)
        .filter(WorkspaceRequestLog.created_at >= start, WorkspaceRequestLog.created_at <= end)
        .all()
    )
    total_requests = len(request_rows)
    blocked_requests = len([row for row in request_rows if (row.status or "").lower() in ("blocked", "denied", "error", "blocked_by_budget", "blocked_by_tokens")])
    total_cost = sum(_to_decimal(row.cost_usd) for row in request_rows)

    daily = {bucket: {"requests": 0, "cost_usd": Decimal("0")} for bucket in _build_time_buckets(start, end)}
    for row in request_rows:
        key = row.created_at.date().isoformat()
        if key in daily:
            daily[key]["requests"] += 1
            daily[key]["cost_usd"] += _to_decimal(row.cost_usd)

    by_model_rows = (
        db.query(
            WorkspaceRequestLog.model.label("model"),
            func.count().label("requests"),
            func.coalesce(func.sum(WorkspaceRequestLog.cost_usd), 0).label("cost_usd"),
        )
        .filter(WorkspaceRequestLog.created_at >= start, WorkspaceRequestLog.created_at <= end)
        .group_by(WorkspaceRequestLog.model)
        .all()
    )
    by_model = [
        {
            "model": row.model or "unknown",
            "requests": int(row.requests or 0),
            "cost_usd": float(_to_decimal(row.cost_usd)),
        }
        for row in by_model_rows
    ]

    return {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "subscription": {
            "mrr_usd": float(Decimal(mrr_usd)),
            "arr_usd": float(Decimal(arr_usd)),
            "total_active_subscriptions": len(active_revenue_rows),
            "by_plan": by_plan,
            "started_in_window": int(started),
            "canceled_in_window": int(canceled),
            "churn_rate_approx": round(float(churn_rate), 4),
            "active_workspaces": int(active_workspaces),
        },
        "requests": {
            "total_requests": int(total_requests),
            "blocked_requests": int(blocked_requests),
            "blocked_request_rate": round(blocked_requests / total_requests * 100, 4) if total_requests else 0.0,
            "total_cost_usd": float(total_cost),
            "avg_cost_per_request": float(total_cost / Decimal(total_requests)) if total_requests else 0.0,
            "by_model": by_model,
            "daily_series": [
                {"date": day, "requests": payload["requests"], "cost_usd": float(payload["cost_usd"])}
                for day, payload in sorted(daily.items())
            ],
        },
        "token_packs": token_pack_payload,
        "cost_allocation": {
            "period_allocation_count": int(
                db.query(func.count(CostAllocation.id))
                .filter(CostAllocation.created_at >= start, CostAllocation.created_at <= end)
                .scalar()
                or 0
            ),
            "period_allocation_cost_usd": float(
                _to_decimal(
                    db.query(func.coalesce(func.sum(CostAllocation.final_cost), 0))
                    .filter(CostAllocation.created_at >= start, CostAllocation.created_at <= end)
                    .scalar()
                )
            ),
        },
        "finance_snapshot": {
            "arr_usd": float(_to_decimal(arr_usd)),
            "token_pack_revenue_usd": float(_to_decimal(token_pack_payload["summary"]["revenue_usd"])),
            "total_platform_revenue_usd": float(
                _to_decimal(mrr_cents / 100) + _to_decimal(token_pack_payload["summary"]["revenue_usd"])
            ),
        },
    }
