"""Simple anomaly detector for cost/latency/quality signals."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from core.incident.alerting import send_alert
from db.models import Anomaly
from db.models.anomaly import AnomalyType, AnomalySeverity, AnomalyStatus
from db.models.ai_audit import AIAuditLog
from db.models.routing_policy import RoutingPolicy
import json


class AnomalyDetector:
    """Detect anomalies from recent audit logs."""

    def detect_cost_spike(
        self,
        db: Session,
        workspace_id: str,
        lookback_minutes: int = 60,
        spike_multiplier: float = 3.0,
        min_events: int = 5,
    ) -> Optional[Anomaly]:
        """Detect a cost spike vs previous window."""
        now = datetime.utcnow()
        window_end = now
        window_start = now - timedelta(minutes=lookback_minutes)
        prev_end = window_start
        prev_start = prev_end - timedelta(minutes=lookback_minutes)

        recent = (
            db.query(AIAuditLog)
            .filter(AIAuditLog.workspace_id == workspace_id, AIAuditLog.created_at >= window_start)
            .all()
        )
        prev = (
            db.query(AIAuditLog)
            .filter(
                AIAuditLog.workspace_id == workspace_id,
                AIAuditLog.created_at >= prev_start,
                AIAuditLog.created_at < prev_end,
            )
            .all()
        )

        if len(recent) < min_events or len(prev) < min_events:
            return None

        recent_cost = sum((Decimal(str(l.cost)) for l in recent), Decimal("0"))
        prev_cost = sum((Decimal(str(l.cost)) for l in prev), Decimal("0"))

        if prev_cost <= 0:
            return None

        ratio = float(recent_cost / prev_cost) if prev_cost > 0 else 0.0
        if ratio < spike_multiplier:
            return None

        severity = AnomalySeverity.HIGH if ratio < 10 else AnomalySeverity.CRITICAL
        description = (
            f"Cost spike detected: last {lookback_minutes}m cost ${recent_cost} vs previous ${prev_cost} "
            f"({ratio:.1f}x)."
        )

        anomaly = Anomaly(
            workspace_id=workspace_id,
            anomaly_type=AnomalyType.COST_SPIKE,
            severity=severity,
            status=AnomalyStatus.DETECTED,
            description=description,
            baseline_value=str(prev_cost),
            actual_value=str(recent_cost),
            deviation_percent=str((ratio - 1.0) * 100.0),
            anomaly_metadata={
                "lookback_minutes": lookback_minutes,
                "recent_window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
                "prev_window": {"start": prev_start.isoformat(), "end": prev_end.isoformat()},
                "recent_events": len(recent),
                "prev_events": len(prev),
            },
        )

        db.add(anomaly)
        db.commit()
        db.refresh(anomaly)

        # Auto-mitigation (high/critical): move to cost_optimized and optionally restrict providers
        if severity in {AnomalySeverity.HIGH, AnomalySeverity.CRITICAL}:
            self._auto_mitigate_cost_spike(db=db, workspace_id=workspace_id, anomaly=anomaly)

        send_alert(
            alert_type="cost_spike",
            severity="critical" if severity == AnomalySeverity.CRITICAL else "high",
            message=description,
            workspace_id=workspace_id,
            metadata={"anomaly_id": anomaly.id, "ratio": ratio},
        )

        return anomaly

    def _auto_mitigate_cost_spike(self, db: Session, workspace_id: str, anomaly: Anomaly) -> None:
        policy = db.query(RoutingPolicy).filter(RoutingPolicy.workspace_id == workspace_id).first()

        constraints = {}
        if policy and policy.constraints_json:
            try:
                constraints = json.loads(policy.constraints_json)
            except Exception:
                constraints = {}

        # Default strict enforcement
        constraints["enforcement_mode"] = constraints.get("enforcement_mode") or "strict"

        allowed = constraints.get("allowed_providers")
        if not allowed or not isinstance(allowed, list):
            # Conservative default: avoid expensive hosted providers during a spike
            constraints["allowed_providers"] = ["huggingface", "local_llm", "local_whisper"]
        else:
            # If openai was allowed, remove it as a conservative response
            constraints["allowed_providers"] = [p for p in allowed if p != "openai"]

        if not policy:
            policy = RoutingPolicy(
                workspace_id=workspace_id,
                strategy="cost_optimized",
                constraints_json=json.dumps(constraints),
                enabled=True,
                version=1,
            )
            db.add(policy)
        else:
            policy.strategy = "cost_optimized"
            policy.constraints_json = json.dumps(constraints)
            policy.enabled = True
            policy.version = (policy.version or 0) + 1

        anomaly.status = AnomalyStatus.REMEDIATED
        anomaly.remediated_at = datetime.utcnow()
        anomaly.remediation_action = (
            "Updated routing policy to cost_optimized and restricted allowed_providers"
        )
        anomaly.remediation_result = json.dumps(
            {
                "policy_id": policy.id,
                "policy_version": (
                    str(policy.version) if getattr(policy, "version", None) is not None else None
                ),
                "constraints": constraints,
            }
        )

        db.commit()


_detector = AnomalyDetector()


def get_anomaly_detector() -> AnomalyDetector:
    return _detector
