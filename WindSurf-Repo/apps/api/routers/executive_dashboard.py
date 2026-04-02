"""Executive admin dashboard router."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_current_workspace_id
from apps.api.routers.dashboard_auth import get_admin_user
from apps.api.routers.admin_dashboard import admin_dashboard_service
from core.environmental.service import environmental_service
from db.models.subscription import (
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
)
from db.models.cost_allocation import CostAllocation
from db.session import get_db


router = APIRouter(prefix="/executive/dashboard", tags=["executive-dashboard"])


class PricingAdjustmentRequest(BaseModel):
    """Request payload for pricing adjustments."""

    tier: SubscriptionTier
    new_price: float = Field(gt=0)
    apply_to_active: bool = True


class GuardrailConfig(BaseModel):
    """Cost guardrail configuration."""

    daily_budget: float = Field(gt=0, description="Daily spend ceiling in USD")
    monthly_budget: float = Field(gt=0, description="Monthly spend ceiling in USD")
    power_saving_mode: bool = False
    provider_spend_caps: Dict[str, float] = Field(default_factory=dict)
    pricing_floor_margin: float = Field(
        default=25.0, description="Minimum gross margin % for auto-approvals"
    )
    cost_strategy: Optional[str] = Field(
        default="balanced",
        description="Exec-selected cost strategy",
    )
    updated_by: Optional[str] = None


class ControlUpdateRequest(BaseModel):
    """Payload for updating power/cost controls."""

    power_saving_mode: Optional[bool] = None
    cost_strategy: Optional[str] = Field(
        default=None,
        regex="^(balanced|aggressive_savings|performance)$",
        description="Exec strategy tag",
    )


@dataclass
class RevenueBreakdown:
    """Internal helper for revenue calculations."""

    tier: str
    revenue: float
    customers: int


class ExecutiveControlStore:
    """Lightweight persistence for guardrail state."""

    def __init__(self) -> None:
        self.path = Path("data/executive_controls.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text())
        default = GuardrailConfig(
            daily_budget=2500.0,
            monthly_budget=60000.0,
            power_saving_mode=False,
            provider_spend_caps={"openai": 20000, "huggingface": 5000, "local": 1500},
            pricing_floor_margin=30.0,
            cost_strategy="balanced",
            updated_by="system",
        ).model_dump() | {"updated_at": datetime.utcnow().isoformat()}
        self.save(default)
        return default

    def save(self, payload: Dict[str, Any]) -> None:
        payload["updated_at"] = datetime.utcnow().isoformat()
        self.path.write_text(json.dumps(payload, indent=2))


control_store = ExecutiveControlStore()


class ExecutiveDashboardService:
    """Aggregates business intelligence for executive dashboard."""

    def __init__(self, db: Session, workspace_id: str, admin_username: str) -> None:
        self.db = db
        self.workspace_id = workspace_id
        self.admin_username = admin_username

    async def build_overview(self, days: int = 30) -> Dict[str, Any]:
        revenue = self._revenue_metrics(days)
        costs = self._cost_metrics(days, revenue)
        users = self._user_metrics(days, revenue)
        pricing = self._pricing_insights(revenue, costs)
        power = await self._power_metrics()
        controls = self._control_snapshot()
        alerts = self._alerts(revenue, costs, users, power)

        gross_margin = (
            ((revenue["total_revenue"] - costs["total_cost"]) / revenue["total_revenue"])
            * 100
            if revenue["total_revenue"]
            else 0.0
        )

        return {
            "period_days": days,
            "last_updated": datetime.utcnow().isoformat(),
            "revenue": revenue,
            "costs": costs,
            "users": users,
            "pricing": pricing,
            "power": power,
            "controls": controls,
            "alerts": alerts,
            "executive_summary": {
                "net_profit": revenue["total_revenue"] - costs["total_cost"],
                "gross_margin_percent": round(gross_margin, 2),
                "run_rate": revenue["mrr"],
                "burn_rate": costs["daily_burn"] * 30,
            },
        }

    def _since(self, days: int) -> datetime:
        return datetime.utcnow() - timedelta(days=days)

    def _revenue_metrics(self, days: int) -> Dict[str, Any]:
        since = self._since(days)
        payments = (
            self.db.query(Payment)
            .filter(
                Payment.workspace_id == self.workspace_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.created_at >= since,
            )
            .all()
        )

        total_revenue = float(sum(p.amount for p in payments))
        avg_payment = total_revenue / len(payments) if payments else 0.0

        # Provider breakdown
        by_provider: Dict[str, Dict[str, float]] = {}
        for payment in payments:
            provider = payment.payment_provider or "unknown"
            provider_entry = by_provider.setdefault(provider, {"count": 0, "revenue": 0.0})
            provider_entry["count"] += 1
            provider_entry["revenue"] += float(payment.amount)

        # Tier breakdown
        tier_map: Dict[str, RevenueBreakdown] = {}
        subscription_ids = {p.subscription_id for p in payments if p.subscription_id}
        if subscription_ids:
            subs = (
                self.db.query(Subscription)
                .filter(Subscription.id.in_(subscription_ids))
                .all()
            )
        else:
            subs = []
        subs_by_id = {s.id: s for s in subs}

        for payment in payments:
            subscription = subs_by_id.get(payment.subscription_id)
            tier_label = (subscription.tier.value if subscription else "unknown").upper()
            breakdown = tier_map.setdefault(
                tier_label, RevenueBreakdown(tier=tier_label, revenue=0.0, customers=0)
            )
            breakdown.revenue += float(payment.amount)
            breakdown.customers += 1

        tier_summary = {
            tier: {
                "revenue": round(data.revenue, 2),
                "customers": data.customers,
                "arpu": round((data.revenue / data.customers) if data.customers else 0.0, 2),
            }
            for tier, data in tier_map.items()
        }

        # Growth baseline (previous period)
        previous_payments = (
            self.db.query(Payment)
            .filter(
                Payment.workspace_id == self.workspace_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.created_at >= self._since(days * 2),
                Payment.created_at < since,
            )
            .all()
        )
        previous_total = float(sum(p.amount for p in previous_payments))
        growth_rate = (
            (total_revenue - previous_total) / previous_total * 100
            if previous_total > 0
            else 100.0
        )

        mrr = (total_revenue / days) * 30 if days else total_revenue

        return {
            "total_revenue": round(total_revenue, 2),
            "average_payment": round(avg_payment, 2),
            "total_payments": len(payments),
            "by_provider": by_provider,
            "by_tier": tier_summary,
            "growth_rate": round(growth_rate, 2),
            "mrr": round(mrr, 2),
        }

    def _cost_metrics(self, days: int, revenue_metrics: Dict[str, Any]) -> Dict[str, Any]:
        since = self._since(days)
        allocations = (
            self.db.query(CostAllocation)
            .filter(
                CostAllocation.workspace_id == self.workspace_id,
                CostAllocation.created_at >= since,
            )
            .all()
        )

        total_cost = Decimal("0")
        power_cost = Decimal("0")
        by_dimension: Dict[str, Decimal] = {}

        for allocation in allocations:
            amount = Decimal(allocation.final_cost or allocation.allocated_cost or 0)
            total_cost += amount
            if allocation.allocation_method == "power":
                power_cost += amount
            key = (allocation.operation_id or "general").split(":")[0]
            by_dimension[key] = by_dimension.get(key, Decimal("0")) + amount

        total_cost_float = float(total_cost)
        daily_burn = total_cost_float / days if days else total_cost_float

        # Estimate gross margin by tier (proportional allocation)
        tier_costs: Dict[str, float] = {}
        total_revenue = revenue_metrics.get("total_revenue", 0.0)
        for tier, stats in revenue_metrics.get("by_tier", {}).items():
            share = stats["revenue"] / total_revenue if total_revenue else 0
            tier_costs[tier] = round(total_cost_float * share, 2)

        return {
            "total_cost": round(total_cost_float, 2),
            "power_cost": round(float(power_cost), 2),
            "daily_burn": round(daily_burn, 2),
            "cost_by_operation": {k: round(float(v), 2) for k, v in by_dimension.items()},
            "tier_costs": tier_costs,
        }

    def _user_metrics(self, days: int, revenue_metrics: Dict[str, Any]) -> Dict[str, Any]:
        since = self._since(days)
        subs = (
            self.db.query(Subscription)
            .filter(Subscription.workspace_id == self.workspace_id)
            .all()
        )

        active = sum(1 for s in subs if s.status == SubscriptionStatus.ACTIVE)
        new_subs = sum(1 for s in subs if (s.started_at or datetime.min) >= since)
        churned = sum(1 for s in subs if s.status in {SubscriptionStatus.CANCELLED, SubscriptionStatus.CANCELED})
        churn_rate = (churned / active * 100) if active else 0

        arpu = (
            revenue_metrics.get("total_revenue", 0.0) / active if active else 0.0
        )

        tier_counts: Dict[str, int] = {}
        for s in subs:
            tier_counts[s.tier.value.upper()] = tier_counts.get(s.tier.value.upper(), 0) + 1

        return {
            "active_users": active,
            "new_subscriptions": new_subs,
            "churn_rate": round(churn_rate, 2),
            "arpu": round(arpu, 2),
            "by_tier": tier_counts,
        }

    def _pricing_insights(
        self, revenue_metrics: Dict[str, Any], cost_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        suggestions: List[Dict[str, Any]] = []
        tier_costs = cost_metrics.get("tier_costs", {})

        for tier, stats in revenue_metrics.get("by_tier", {}).items():
            revenue = stats["revenue"]
            cost = tier_costs.get(tier, 0.0)
            margin = ((revenue - cost) / revenue * 100) if revenue else 0.0
            target_price = stats["arpu"] * 1.08 if margin > 35 else stats["arpu"] * 1.15
            impact = (target_price - stats["arpu"]) * stats["customers"]
            suggestions.append(
                {
                    "tier": tier,
                    "current_arpu": stats["arpu"],
                    "projected_price": round(target_price, 2),
                    "margin_percent": round(margin, 2),
                    "estimated_monthly_impact": round(impact, 2),
                    "action": "increase" if target_price > stats["arpu"] else "evaluate",
                }
            )

        return {"suggestions": suggestions[:3]}

    async def _power_metrics(self) -> Dict[str, Any]:
        summary = await environmental_service.get_environmental_summary(self.workspace_id)
        return {
            "total_energy_kwh": round(summary["total_energy_kwh"], 2),
            "co2_emissions_kg": round(summary["total_co2_emissions_kg"], 2),
            "co2_savings_kg": round(summary["co2_savings_kg"], 2),
            "efficiency_percent": round(summary["efficiency_percentage"], 2),
            "avg_latency_ms": summary["average_latency_ms"],
        }

    def _control_snapshot(self) -> Dict[str, Any]:
        switches = admin_dashboard_service.load_switches()
        relevant_categories = {"Providers", "Billing", "Advanced"}
        filtered = [
            s.dict()
            for s in switches
            if s.category in relevant_categories
        ]
        guardrails = control_store.load()
        return {"switches": filtered, "guardrails": guardrails}

    def _alerts(
        self,
        revenue: Dict[str, Any],
        costs: Dict[str, Any],
        users: Dict[str, Any],
        power: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []

        gross_margin = (
            (revenue["total_revenue"] - costs["total_cost"]) / revenue["total_revenue"] * 100
            if revenue["total_revenue"]
            else 0
        )
        if gross_margin < 30:
            alerts.append(
                {
                    "severity": "error",
                    "title": "Margin compression",
                    "message": f"Gross margin at {gross_margin:.1f}%",
                    "impact": "Investigate provider mix and pricing",
                }
            )

        if users["churn_rate"] > 5:
            alerts.append(
                {
                    "severity": "warning",
                    "title": "Churn spike",
                    "message": f"Churn rate {users['churn_rate']:.1f}% exceeds target",
                    "impact": "Trigger win-back campaigns",
                }
            )

        if power["co2_emissions_kg"] > power["co2_savings_kg"] * 4:
            alerts.append(
                {
                    "severity": "info",
                    "title": "Power optimization opportunity",
                    "message": "Enable carbon-aware routing for heavy workloads",
                    "impact": "Potential energy savings > 12%",
                }
            )

        return alerts


@router.get("/overview")
async def get_executive_overview(
    days: int = 30,
    admin_user: dict = Depends(get_admin_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Return enterprise-grade analytics for admins only."""

    if days <= 0:
        raise HTTPException(status_code=400, detail="Days must be positive")

    service = ExecutiveDashboardService(db, workspace_id, admin_user["username"])
    return await service.build_overview(days)


@router.post("/pricing/adjust", status_code=status.HTTP_202_ACCEPTED)
async def adjust_pricing(
    payload: PricingAdjustmentRequest,
    admin_user: dict = Depends(get_admin_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Apply pricing change across subscriptions in a workspace."""

    query = db.query(Subscription).filter(
        Subscription.workspace_id == workspace_id,
        Subscription.tier == payload.tier,
    )

    if payload.apply_to_active:
        query = query.filter(Subscription.status == SubscriptionStatus.ACTIVE)

    updated = query.update({Subscription.price_period: payload.new_price}, synchronize_session=False)
    db.commit()

    return {
        "tier": payload.tier.value,
        "new_price": payload.new_price,
        "updated_subscriptions": updated,
        "updated_by": admin_user["username"],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/controls/guardrails", response_model=GuardrailConfig)
async def get_guardrails(admin_user: dict = Depends(get_admin_user)):
    """Fetch persisted guardrail configuration."""

    data = control_store.load()
    filtered = {k: v for k, v in data.items() if k in GuardrailConfig.model_fields}
    return GuardrailConfig(**filtered)


@router.post("/controls/guardrails")
async def set_guardrails(
    payload: GuardrailConfig,
    admin_user: dict = Depends(get_admin_user),
):
    """Update guardrail configuration."""

    data = payload.model_dump()
    data["updated_by"] = admin_user["username"]
    control_store.save(data)
    return {"message": "Guardrails updated", "config": data}


@router.post("/controls/update")
async def update_control_strategy(
    payload: ControlUpdateRequest,
    admin_user: dict = Depends(get_admin_user),
):
    """Toggle high-level power/cost strategies on top of switch layer."""

    guardrails = control_store.load()
    if payload.power_saving_mode is not None:
        guardrails["power_saving_mode"] = payload.power_saving_mode
    if payload.cost_strategy:
        guardrails["cost_strategy"] = payload.cost_strategy
    guardrails["updated_by"] = admin_user["username"]
    control_store.save(guardrails)
    return {"message": "Controls updated", "guardrails": guardrails}
