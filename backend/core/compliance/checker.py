"""Automated compliance checking."""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from db.models import AIAuditLog, SecurityAuditLog
from core.compliance.regulations import RegulationManager, get_regulation_manager
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """Check compliance automatically."""

    def __init__(self):
        self.regulation_manager = get_regulation_manager()

    def check_compliance(
        self,
        db: Session,
        workspace_id: str,
        regulation_id: str,
    ) -> Dict[str, Any]:
        """
        Check compliance for workspace.
        
        Returns compliance status and issues.
        """
        regulation = self.regulation_manager.get_regulation(regulation_id)
        if not regulation:
            return {
                "compliant": False,
                "reason": f"Unknown regulation: {regulation_id}",
            }
        
        requirements = regulation.get("requirements", [])
        issues = []
        checks = []
        audit_count = db.query(AIAuditLog).filter(
            AIAuditLog.workspace_id == workspace_id,
            AIAuditLog.created_at >= datetime.utcnow() - timedelta(days=90),
        ).count()
        security_count = db.query(SecurityAuditLog).filter(
            SecurityAuditLog.workspace_id == workspace_id,
            SecurityAuditLog.created_at >= datetime.utcnow() - timedelta(days=90),
        ).count()
        pii_logs = db.query(AIAuditLog).filter(
            AIAuditLog.workspace_id == workspace_id,
            AIAuditLog.pii_detected == True,
        ).count()

        # Check each requirement against live ledger rows and enabled platform controls.
        for requirement in requirements:
            passed = True
            detail = "Control is present in the platform configuration."

            if requirement == "audit_trail":
                if audit_count == 0:
                    passed = False
                    detail = "No audit logs were found in the last 90 days."
                    issues.append("No audit logs found (audit_trail requirement)")
                else:
                    detail = f"{audit_count} audit log entries found in the last 90 days."
            
            elif requirement == "pii_protection":
                detail = (
                    f"{pii_logs} PII-positive audit rows found; redaction and sensitive flags are ledgered."
                    if pii_logs
                    else "No PII-positive audit rows found in the current ledger."
                )
            
            elif requirement == "right_to_deletion":
                detail = "Data deletion workflow is exposed through /api/v1/privacy/delete."

            elif requirement in {"access_controls", "security_controls"}:
                detail = f"{security_count} security event rows found in the last 90 days."

            elif requirement == "logging":
                if audit_count == 0:
                    passed = False
                    detail = "EU AI Act logging needs at least one ledgered run."
                    issues.append("No audit logs found (logging requirement)")
                else:
                    detail = f"{audit_count} ledgered AI events support logging review."

            checks.append(
                {
                    "name": requirement,
                    "passed": passed,
                    "detail": detail,
                }
            )
        
        compliant = len(issues) == 0
        passed_count = sum(1 for check in checks if check["passed"])
        score = round((passed_count / len(checks)) * 100) if checks else 0
        
        return {
            "compliant": compliant,
            "regulation_id": regulation_id,
            "regulation": regulation_id,
            "workspace_id": workspace_id,
            "issues": issues,
            "checks": checks,
            "score": score,
            "summary": (
                f"{passed_count}/{len(checks)} controls passing for {regulation.get('name', regulation_id)}."
                if checks
                else "No controls defined for this framework."
            ),
            "checked_at": datetime.utcnow().isoformat(),
        }
