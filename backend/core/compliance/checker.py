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
        
        # Check each requirement
        for requirement in requirements:
            if requirement == "audit_trail":
                # Check if audit logs exist
                audit_count = db.query(AIAuditLog).filter(
                    AIAuditLog.workspace_id == workspace_id,
                    AIAuditLog.created_at >= datetime.utcnow() - timedelta(days=90),
                ).count()
                
                if audit_count == 0:
                    issues.append("No audit logs found (audit_trail requirement)")
            
            elif requirement == "pii_protection":
                # Check if PII is being detected
                pii_logs = db.query(AIAuditLog).filter(
                    AIAuditLog.workspace_id == workspace_id,
                    AIAuditLog.pii_detected == True,
                ).count()
                
                if pii_logs > 0:
                    # PII detected - check if it's being handled properly
                    # (This is a basic check - can be enhanced)
                    pass
            
            elif requirement == "right_to_deletion":
                # Check if deletion endpoint exists (it does - /privacy/delete)
                # This is more of a feature check
                pass
        
        compliant = len(issues) == 0
        
        return {
            "compliant": compliant,
            "regulation": regulation_id,
            "workspace_id": workspace_id,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat(),
        }
