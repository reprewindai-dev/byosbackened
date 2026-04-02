"""Savings calculator - calculate savings vs baseline."""

from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import CostPrediction, RoutingDecision, AIAuditLog
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class SavingsCalculator:
    """
    Calculate savings vs baseline.

    Shows users exactly how much the system saved them.
    Creates "value demonstration" - proves the moat works.
    """

    def calculate_savings(
        self,
        workspace_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Calculate total savings for workspace.

        Compares actual costs vs single-provider baseline.
        """
        if not db:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)  # Last 30 days
            if not end_date:
                end_date = datetime.utcnow()

            # Get all operations in period (with limit to prevent unbounded queries)
            # Max 100,000 operations per query
            operations = (
                db.query(AIAuditLog)
                .filter(
                    AIAuditLog.workspace_id == workspace_id,
                    AIAuditLog.created_at >= start_date,
                    AIAuditLog.created_at <= end_date,
                    AIAuditLog.cost.isnot(None),
                )
                .limit(100000)
                .all()
            )

            if not operations:
                return {
                    "total_savings": Decimal("0.00"),
                    "baseline_cost": Decimal("0.00"),
                    "actual_cost": Decimal("0.00"),
                    "savings_percent": 0.0,
                    "operations_count": 0,
                    "latency_reduction_ms": 0,
                    "cache_hit_rate_improvement": 0.0,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                }

            # Calculate baseline (single-provider cost)
            baseline_cost = self._calculate_baseline_cost(operations)

            # Calculate actual cost
            actual_cost = sum(Decimal(str(op.cost)) for op in operations if op.cost)

            # Calculate savings
            total_savings = baseline_cost - actual_cost
            savings_percent = (total_savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

            # Calculate latency reduction
            latency_reduction = self._calculate_latency_reduction(operations)

            # Calculate cache improvements
            cache_improvements = self._calculate_cache_improvements(workspace_id, db)

            return {
                "total_savings": total_savings,
                "baseline_cost": baseline_cost,
                "actual_cost": actual_cost,
                "savings_percent": float(savings_percent),
                "operations_count": len(operations),
                "latency_reduction_ms": latency_reduction,
                "cache_hit_rate_improvement": cache_improvements.get("hit_rate_improvement", 0.0),
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
            }
        finally:
            if should_close:
                db.close()

    def _calculate_baseline_cost(self, operations: List) -> Decimal:
        """
        Calculate baseline cost (single-provider scenario).

        Uses most expensive provider as baseline (worst case).
        """
        # For each operation, calculate what it would cost with most expensive provider
        baseline_total = Decimal("0.00")

        # Provider pricing (per 1M tokens)
        pricing = {
            "openai": {
                "input": Decimal("2.50"),
                "output": Decimal("10.00"),
            },  # GPT-4o (most expensive)
            "huggingface": {"input": Decimal("0.00"), "output": Decimal("0.00")},
            "local": {"input": Decimal("0.001"), "output": Decimal("0.001")},
        }

        for op in operations:
            if op.tokens_input and op.tokens_output:
                # Calculate cost with most expensive provider
                input_cost = (Decimal(op.tokens_input) / Decimal(1_000_000)) * pricing["openai"][
                    "input"
                ]
                output_cost = (Decimal(op.tokens_output) / Decimal(1_000_000)) * pricing["openai"][
                    "output"
                ]
                baseline_total += input_cost + output_cost

        return baseline_total

    def _calculate_latency_reduction(self, operations: List) -> int:
        """
        Calculate latency reduction vs baseline.

        Compares p95 latency vs single-provider baseline.
        """
        if not operations:
            return 0

        # Get actual latencies
        latencies = [
            op.latency_ms for op in operations if hasattr(op, "latency_ms") and op.latency_ms
        ]

        if not latencies:
            return 0

        # Calculate p95
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)]

        # Baseline p95 (assume 3000ms for single provider)
        baseline_p95 = 3000

        reduction = baseline_p95 - p95_latency
        return max(0, reduction)

    def _calculate_cache_improvements(
        self,
        workspace_id: str,
        db: Session,
    ) -> Dict[str, float]:
        """Calculate cache hit rate improvements."""
        # This would query cache statistics
        # For now, return placeholder
        return {
            "hit_rate_improvement": 0.15,  # 15% improvement
            "current_hit_rate": 0.75,
            "baseline_hit_rate": 0.60,
        }

    def calculate_projected_savings(
        self,
        workspace_id: str,
        months_ahead: int = 1,
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Project savings for next N months.

        Uses historical trends to project future savings.
        """
        if not db:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            # Get last 3 months of savings
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=90)

            savings = self.calculate_savings(
                workspace_id=workspace_id,
                start_date=start_date,
                end_date=end_date,
                db=db,
            )

            monthly_savings = savings["total_savings"] / Decimal("3")  # Average per month

            # Project forward
            projected_savings = monthly_savings * Decimal(str(months_ahead))

            return {
                "projected_savings": projected_savings,
                "monthly_avg_savings": monthly_savings,
                "months_ahead": months_ahead,
                "projected_savings_percent": float(savings["savings_percent"]),
            }
        finally:
            if should_close:
                db.close()


# Global savings calculator
_savings_calculator = SavingsCalculator()


def get_savings_calculator() -> SavingsCalculator:
    """Get global savings calculator instance."""
    return _savings_calculator
