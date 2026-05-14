"""Operator health watch and pre-critical alert generation.

This is the backend-owned feedback loop for the owner/operator. Slack, email,
and GitHub are delivery rails; the source of truth is the backend database.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from db.models import Alert, AlertSeverity, AIAuditLog, SecurityAuditLog, WorkspaceRequestLog


@dataclass(frozen=True)
class WatchFinding:
    code: str
    title: str
    severity: AlertSeverity
    signal: str
    diagnosis: str
    operator_action: str
    self_healing_action: str | None
    metadata: dict[str, Any]


def _percentile(values: list[int], percentile: float) -> int:
    clean = sorted(v for v in values if v >= 0)
    if not clean:
        return 0
    index = int(round((len(clean) - 1) * percentile))
    return int(clean[max(0, min(index, len(clean) - 1))])


def _alert_fingerprint(finding: WatchFinding, workspace_id: str | None) -> str:
    raw = json.dumps(
        {
            "workspace_id": workspace_id or "global",
            "code": finding.code,
            "signal": finding.signal,
            "operator_action": finding.operator_action,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _severity_rank(severity: AlertSeverity) -> int:
    order = {
        AlertSeverity.INFO: 0,
        AlertSeverity.LOW: 1,
        AlertSeverity.MEDIUM: 2,
        AlertSeverity.HIGH: 3,
        AlertSeverity.CRITICAL: 4,
    }
    return order.get(severity, 0)


def _find_or_create_alert(
    db: Session,
    *,
    workspace_id: str | None,
    finding: WatchFinding,
) -> tuple[Alert, bool]:
    fingerprint = _alert_fingerprint(finding, workspace_id)
    existing = (
        db.query(Alert)
        .filter(
            Alert.workspace_id == workspace_id,
            Alert.alert_type == f"operator_watch:{finding.code}",
            Alert.status == "open",
        )
        .first()
    )
    details = {
        "fingerprint": fingerprint,
        "signal": finding.signal,
        "diagnosis": finding.diagnosis,
        "operator_action": finding.operator_action,
        "self_healing_action": finding.self_healing_action,
        "metadata": finding.metadata,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    if existing:
        existing.description = finding.diagnosis
        existing.severity = finding.severity
        existing.details = details
        return existing, False

    alert = Alert(
        workspace_id=workspace_id,
        title=finding.title,
        description=finding.diagnosis,
        severity=finding.severity,
        alert_type=f"operator_watch:{finding.code}",
        status="open",
        source="backend_operator_watch",
        details=details,
    )
    db.add(alert)
    return alert, True


def _record_self_healing(
    db: Session,
    *,
    workspace_id: str | None,
    finding: WatchFinding,
) -> None:
    if not finding.self_healing_action:
        return
    db.add(
        SecurityAuditLog(
            workspace_id=workspace_id,
            event_type="operator_self_healing",
            event_category="operator_watch",
            success=True,
            details=json.dumps(
                {
                    "finding": finding.code,
                    "action": finding.self_healing_action,
                    "reason": finding.diagnosis,
                    "metadata": finding.metadata,
                },
                sort_keys=True,
                default=str,
            ),
        )
    )


def evaluate_operator_watch(
    db: Session,
    *,
    workspace_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Evaluate pre-critical health and optionally persist actionable alerts."""
    now = datetime.utcnow()
    one_hour = now - timedelta(hours=1)
    one_day = now - timedelta(days=1)

    request_query = db.query(WorkspaceRequestLog).filter(WorkspaceRequestLog.created_at >= one_day)
    audit_query = db.query(AIAuditLog).filter(AIAuditLog.created_at >= one_day)
    open_alert_query = db.query(Alert).filter(Alert.status == "open")
    if workspace_id:
        request_query = request_query.filter(WorkspaceRequestLog.workspace_id == workspace_id)
        audit_query = audit_query.filter(AIAuditLog.workspace_id == workspace_id)
        open_alert_query = open_alert_query.filter(Alert.workspace_id == workspace_id)

    requests_24h = request_query.order_by(desc(WorkspaceRequestLog.created_at)).limit(1000).all()
    requests_1h = [row for row in requests_24h if row.created_at >= one_hour]
    audits_24h = audit_query.order_by(desc(AIAuditLog.created_at)).limit(1000).all()
    open_alerts = open_alert_query.order_by(desc(Alert.created_at)).limit(100).all()

    latencies = [int(row.latency_ms or 0) for row in requests_1h if row.latency_ms is not None]
    p50 = int(median(latencies)) if latencies else 0
    p95 = _percentile(latencies, 0.95)
    total_1h = len(requests_1h)
    failed_1h = len([row for row in requests_1h if str(row.status).lower() not in {"success", "ok", "200", "completed"}])
    error_rate_pct = round((failed_1h / total_1h) * 100, 2) if total_1h else 0.0
    fallback_1h = len([row for row in requests_1h if (row.provider or "").lower() not in {"", "ollama"}])
    fallback_pct = round((fallback_1h / total_1h) * 100, 2) if total_1h else 0.0
    latest_request_at = requests_24h[0].created_at if requests_24h else None
    latest_audit_at = audits_24h[0].created_at if audits_24h else None

    findings: list[WatchFinding] = []
    if total_1h >= 5 and p95 >= 3000:
        findings.append(
            WatchFinding(
                code="latency_p95_precritical",
                title="Latency pressure is above pre-critical threshold",
                severity=AlertSeverity.HIGH if p95 >= 5000 else AlertSeverity.MEDIUM,
                signal=f"p95={p95}ms p50={p50}ms samples={total_1h}",
                diagnosis="The backend is still serving traffic, but tail latency is high enough to degrade user trust before an outage appears.",
                operator_action="Inspect provider/model mix, Ollama host pressure, fallback rate, and recent slow traces in Sunnyvale.",
                self_healing_action="operator_watch_logged_latency_pressure",
                metadata={"p50_ms": p50, "p95_ms": p95, "samples": total_1h},
            )
        )

    if total_1h >= 5 and error_rate_pct >= 5:
        findings.append(
            WatchFinding(
                code="error_rate_precritical",
                title="Request error rate is above autonomous guardrail",
                severity=AlertSeverity.CRITICAL if error_rate_pct >= 15 else AlertSeverity.HIGH,
                signal=f"error_rate={error_rate_pct}% failed={failed_1h}/{total_1h}",
                diagnosis="Live traffic is producing failures. This needs intervention before users interpret the system as unreliable.",
                operator_action="Check recent failed request logs, provider responses, token wallet state, and rate-limit/license gates.",
                self_healing_action="operator_watch_escalated_error_rate",
                metadata={"error_rate_pct": error_rate_pct, "failed": failed_1h, "total": total_1h},
            )
        )

    if total_1h >= 5 and fallback_pct >= 40:
        findings.append(
            WatchFinding(
                code="fallback_pressure",
                title="Fallback route pressure is rising",
                severity=AlertSeverity.MEDIUM,
                signal=f"fallback={fallback_pct}% samples={total_1h}",
                diagnosis="A large share of recent work is leaving the primary path. Cost, latency, or provider-health drift may be building.",
                operator_action="Review route policy, primary Ollama health, and fallback spend before reserve usage climbs.",
                self_healing_action="operator_watch_marked_route_pressure",
                metadata={"fallback_pct": fallback_pct, "fallback_runs": fallback_1h, "total": total_1h},
            )
        )

    if requests_24h and audits_24h and latest_request_at and latest_audit_at:
        drift_seconds = abs((latest_request_at - latest_audit_at).total_seconds())
        if drift_seconds >= 900:
            findings.append(
                WatchFinding(
                    code="audit_telemetry_drift",
                    title="Audit and request telemetry are drifting",
                    severity=AlertSeverity.MEDIUM,
                    signal=f"latest_request={latest_request_at.isoformat()} latest_audit={latest_audit_at.isoformat()}",
                    diagnosis="Runtime telemetry and audit lineage are not advancing together. The Archives can become incomplete if this continues.",
                    operator_action="Verify AI completion path writes both WorkspaceRequestLog and AIAuditLog for every real run.",
                    self_healing_action="operator_watch_preserved_drift_evidence",
                    metadata={"drift_seconds": int(drift_seconds)},
                )
            )

    critical_open = [alert for alert in open_alerts if _severity_rank(alert.severity) >= _severity_rank(AlertSeverity.HIGH)]
    if len(critical_open) >= 3:
        findings.append(
            WatchFinding(
                code="open_alert_backlog",
                title="Operator alert backlog is accumulating",
                severity=AlertSeverity.HIGH,
                signal=f"high_or_critical_open_alerts={len(critical_open)}",
                diagnosis="The system is detecting issues faster than they are being acknowledged or resolved.",
                operator_action="Triage the highest severity open alerts and close resolved stale alerts to restore operator signal quality.",
                self_healing_action=None,
                metadata={"open_high_critical": len(critical_open)},
            )
        )

    created = 0
    updated = 0
    if persist:
        for finding in findings:
            _, was_created = _find_or_create_alert(db, workspace_id=workspace_id, finding=finding)
            _record_self_healing(db, workspace_id=workspace_id, finding=finding)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
        db.commit()

    status_value = "critical" if any(f.severity == AlertSeverity.CRITICAL for f in findings) else "warning" if findings else "healthy"
    return {
        "status": status_value,
        "workspace_id": workspace_id,
        "generated_at": now.isoformat() + "Z",
        "summary": {
            "requests_1h": total_1h,
            "requests_24h": len(requests_24h),
            "audit_entries_24h": len(audits_24h),
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "error_rate_pct": error_rate_pct,
            "fallback_pct": fallback_pct,
            "open_alerts": len(open_alerts),
            "high_or_critical_open_alerts": len(critical_open),
        },
        "findings": [
            {
                "code": finding.code,
                "title": finding.title,
                "severity": finding.severity.value,
                "signal": finding.signal,
                "diagnosis": finding.diagnosis,
                "operator_action": finding.operator_action,
                "self_healing_action": finding.self_healing_action,
                "metadata": finding.metadata,
            }
            for finding in findings
        ],
        "persistence": {"created": created, "updated": updated, "enabled": persist},
    }
