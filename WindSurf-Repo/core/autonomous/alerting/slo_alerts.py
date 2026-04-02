"""SLO-based alerting - monitor service level objectives."""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import AIAuditLog, Anomaly
from core.autonomous.anomaly.detector import get_anomaly_detector
from core.autonomous.anomaly.remediator import get_auto_remediator
from core.incident.alerting import send_alert
from core.metrics.autonomous_metrics import get_autonomous_metrics
from core.config import get_settings
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
settings = get_settings()
autonomous_metrics = get_autonomous_metrics()
anomaly_detector = get_anomaly_detector()
auto_remediator = get_auto_remediator()


class SLOAlerts:
    """
    SLO-based alerting system.

    Monitors service level objectives and alerts when thresholds are breached.
    """

    # SLO Definitions
    SLO_LATENCY_P95_MS = 2000  # p95 latency should be < 2000ms
    SLO_LATENCY_ALERT_THRESHOLD_MS = 3000  # Alert if p95 > 3000ms

    SLO_COST_SAVINGS_PERCENT = 20.0  # Should save > 20%
    SLO_COST_SAVINGS_ALERT_THRESHOLD = 10.0  # Alert if savings < 10%

    SLO_ERROR_RATE_PERCENT = 1.0  # Error rate should be < 1%
    SLO_ERROR_RATE_ALERT_THRESHOLD = 5.0  # Alert if error rate > 5%

    SLO_REMEDIATION_SUCCESS_PERCENT = 80.0  # Remediation success should be > 80%
    SLO_REMEDIATION_SUCCESS_ALERT_THRESHOLD = 50.0  # Alert if success < 50%

    def check_slos(
        self,
        workspace_id: str,
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Check all SLOs for workspace and alert if breached.

        Returns SLO status and any alerts triggered.
        """
        if not db:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        alerts_triggered = []

        try:
            # Check latency SLO
            latency_status = self._check_latency_slo(workspace_id, db)
            if latency_status["breached"]:
                alerts_triggered.append(latency_status)

            # Check cost savings SLO
            cost_status = self._check_cost_savings_slo(workspace_id, db)
            if cost_status["breached"]:
                alerts_triggered.append(cost_status)

            # Check error rate SLO
            error_status = self._check_error_rate_slo(workspace_id, db)
            if error_status["breached"]:
                alerts_triggered.append(error_status)

            # Check remediation success SLO
            remediation_status = self._check_remediation_slo(workspace_id, db)
            if remediation_status["breached"]:
                alerts_triggered.append(remediation_status)

            # Send alerts
            for alert in alerts_triggered:
                send_alert(
                    alert_type="slo_breach",
                    severity="high" if alert["severity"] == "critical" else "medium",
                    message=alert["message"],
                    workspace_id=workspace_id,
                    metadata=alert,
                )

            return {
                "workspace_id": workspace_id,
                "slos_checked": 4,
                "alerts_triggered": len(alerts_triggered),
                "alerts": alerts_triggered,
                "status": "breached" if alerts_triggered else "healthy",
            }
        finally:
            if should_close:
                db.close()

    def _check_latency_slo(
        self,
        workspace_id: str,
        db: Session,
    ) -> Dict[str, any]:
        """Check latency p95 SLO."""
        # Get last hour of operations
        cutoff = datetime.utcnow() - timedelta(hours=1)

        operations = (
            db.query(AIAuditLog)
            .filter(
                AIAuditLog.workspace_id == workspace_id,
                AIAuditLog.created_at >= cutoff,
                AIAuditLog.latency_ms.isnot(None),
            )
            .all()
        )

        if len(operations) < 10:
            return {
                "slo": "latency_p95",
                "breached": False,
                "reason": "Insufficient data",
            }

        # Calculate p95 latency
        latencies = sorted([op.latency_ms for op in operations if op.latency_ms])
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[min(p95_index, len(latencies) - 1)]

        breached = p95_latency > self.SLO_LATENCY_ALERT_THRESHOLD_MS

        return {
            "slo": "latency_p95",
            "breached": breached,
            "current_value": p95_latency,
            "threshold": self.SLO_LATENCY_ALERT_THRESHOLD_MS,
            "target": self.SLO_LATENCY_P95_MS,
            "severity": (
                "critical" if p95_latency > self.SLO_LATENCY_ALERT_THRESHOLD_MS * 1.5 else "medium"
            ),
            "message": (
                f"Latency p95 breach: {p95_latency}ms > {self.SLO_LATENCY_ALERT_THRESHOLD_MS}ms "
                f"(target: {self.SLO_LATENCY_P95_MS}ms)"
            ),
        }

    def _check_cost_savings_slo(
        self,
        workspace_id: str,
        db: Session,
    ) -> Dict[str, any]:
        """Check cost savings SLO."""
        from core.autonomous.reporting.savings_calculator import get_savings_calculator

        savings_calculator = get_savings_calculator()

        # Get last 7 days of savings
        start_date = datetime.utcnow() - timedelta(days=7)
        savings = savings_calculator.calculate_savings(
            workspace_id=workspace_id,
            start_date=start_date,
            db=db,
        )

        savings_percent = savings.get("savings_percent", 0.0)
        breached = savings_percent < self.SLO_COST_SAVINGS_ALERT_THRESHOLD

        return {
            "slo": "cost_savings",
            "breached": breached,
            "current_value": savings_percent,
            "threshold": self.SLO_COST_SAVINGS_ALERT_THRESHOLD,
            "target": self.SLO_COST_SAVINGS_PERCENT,
            "severity": "medium",
            "message": (
                f"Cost savings below threshold: {savings_percent:.1f}% < {self.SLO_COST_SAVINGS_ALERT_THRESHOLD}% "
                f"(target: {self.SLO_COST_SAVINGS_PERCENT}%)"
            ),
        }

    def _check_error_rate_slo(
        self,
        workspace_id: str,
        db: Session,
    ) -> Dict[str, any]:
        """Check error rate SLO."""
        # Get last hour of operations
        cutoff = datetime.utcnow() - timedelta(hours=1)

        total_operations = (
            db.query(AIAuditLog)
            .filter(
                AIAuditLog.workspace_id == workspace_id,
                AIAuditLog.created_at >= cutoff,
            )
            .count()
        )

        # Count errors (operations with high latency or failures)
        error_operations = (
            db.query(AIAuditLog)
            .filter(
                AIAuditLog.workspace_id == workspace_id,
                AIAuditLog.created_at >= cutoff,
                AIAuditLog.latency_ms > 10000,  # > 10s is considered error
            )
            .count()
        )

        if total_operations == 0:
            return {
                "slo": "error_rate",
                "breached": False,
                "reason": "No operations",
            }

        error_rate = (error_operations / total_operations) * 100
        breached = error_rate > self.SLO_ERROR_RATE_ALERT_THRESHOLD

        return {
            "slo": "error_rate",
            "breached": breached,
            "current_value": error_rate,
            "threshold": self.SLO_ERROR_RATE_ALERT_THRESHOLD,
            "target": self.SLO_ERROR_RATE_PERCENT,
            "severity": (
                "critical" if error_rate > self.SLO_ERROR_RATE_ALERT_THRESHOLD * 2 else "medium"
            ),
            "message": (
                f"Error rate breach: {error_rate:.1f}% > {self.SLO_ERROR_RATE_ALERT_THRESHOLD}% "
                f"(target: {self.SLO_ERROR_RATE_PERCENT}%)"
            ),
        }

    def _check_remediation_slo(
        self,
        workspace_id: str,
        db: Session,
    ) -> Dict[str, any]:
        """Check remediation success rate SLO."""
        from db.models.anomaly import AnomalyStatus

        # Get last 7 days of remediated anomalies
        cutoff = datetime.utcnow() - timedelta(days=7)

        remediated = (
            db.query(Anomaly)
            .filter(
                Anomaly.workspace_id == workspace_id,
                Anomaly.status == AnomalyStatus.REMEDIATED,
                Anomaly.remediated_at >= cutoff,
            )
            .all()
        )

        if len(remediated) == 0:
            return {
                "slo": "remediation_success",
                "breached": False,
                "reason": "No remediations",
            }

        # Count successful remediations (remediation_result indicates success)
        successful = [
            a
            for a in remediated
            if a.remediation_result and "success" in a.remediation_result.lower()
        ]

        success_rate = (len(successful) / len(remediated)) * 100
        breached = success_rate < self.SLO_REMEDIATION_SUCCESS_ALERT_THRESHOLD

        return {
            "slo": "remediation_success",
            "breached": breached,
            "current_value": success_rate,
            "threshold": self.SLO_REMEDIATION_SUCCESS_ALERT_THRESHOLD,
            "target": self.SLO_REMEDIATION_SUCCESS_PERCENT,
            "severity": "medium",
            "message": (
                f"Remediation success rate below threshold: {success_rate:.1f}% < {self.SLO_REMEDIATION_SUCCESS_ALERT_THRESHOLD}% "
                f"(target: {self.SLO_REMEDIATION_SUCCESS_PERCENT}%)"
            ),
        }


# Global SLO alerts
_slo_alerts = SLOAlerts()


def get_slo_alerts() -> SLOAlerts:
    """Get global SLO alerts instance."""
    return _slo_alerts
