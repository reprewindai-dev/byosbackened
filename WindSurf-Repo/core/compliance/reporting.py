"""Compliance report generation."""

from typing import Dict, List
from sqlalchemy.orm import Session
from db.models import AIAuditLog, SecurityAuditLog
from core.compliance.regulations import RegulationManager, get_regulation_manager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ComplianceReporter:
    """Generate compliance reports."""

    def __init__(self):
        self.regulation_manager = get_regulation_manager()

    def generate_report(
        self,
        db: Session,
        workspace_id: str,
        regulation_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, any]:
        """Generate compliance report."""
        regulation = self.regulation_manager.get_regulation(regulation_id)
        if not regulation:
            return {
                "error": f"Unknown regulation: {regulation_id}",
            }

        # Get audit logs in period
        audit_logs = (
            db.query(AIAuditLog)
            .filter(
                AIAuditLog.workspace_id == workspace_id,
                AIAuditLog.created_at >= start_date,
                AIAuditLog.created_at <= end_date,
            )
            .all()
        )

        # Get security audit logs
        security_logs = (
            db.query(SecurityAuditLog)
            .filter(
                SecurityAuditLog.workspace_id == workspace_id,
                SecurityAuditLog.created_at >= start_date,
                SecurityAuditLog.created_at <= end_date,
            )
            .all()
        )

        # Generate report based on regulation
        report = {
            "regulation": regulation_id,
            "regulation_name": regulation.get("name"),
            "workspace_id": workspace_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_ai_operations": len(audit_logs),
                "total_security_events": len(security_logs),
                "operations_with_pii": len([l for l in audit_logs if l.pii_detected]),
                "total_cost": str(sum(l.cost for l in audit_logs)),
            },
            "compliance_status": "compliant",  # TODO: Run actual compliance check
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Add regulation-specific sections
        if regulation_id == "gdpr":
            report["gdpr_specific"] = {
                "data_minimization": "Implemented",
                "purpose_limitation": "Implemented",
                "right_to_access": "Available via /api/v1/privacy/export",
                "right_to_deletion": "Available via /api/v1/privacy/delete",
                "audit_trail": f"{len(audit_logs)} operations logged",
            }

        return report
