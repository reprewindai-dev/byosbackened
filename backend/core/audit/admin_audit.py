"""Admin action audit logging."""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import SecurityAuditLog
from core.config import get_settings
import json
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class AdminAuditLogger:
    """
    Log admin actions for audit purposes.
    
    Tracks:
    - Routing strategy changes
    - Manual model retraining
    - Manual remediation actions
    - Configuration changes
    """

    def log_routing_strategy_change(
        self,
        db: Session,
        workspace_id: str,
        admin_user_id: str,
        action: str,  # "create", "update", "delete", "activate", "deactivate"
        strategy_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
    ):
        """
        Log routing strategy change.
        
        Args:
            db: Database session
            workspace_id: Workspace ID
            admin_user_id: User ID who made the change
            action: Action performed
            strategy_id: Strategy ID (if applicable)
            changes: Dictionary of changes made
        """
        audit_log = SecurityAuditLog(
            workspace_id=workspace_id,
            user_id=admin_user_id,
            event_type="admin_action",
            event_category="routing_strategy",
            success=True,
            details=json.dumps({
                "action": action,
                "resource_type": "routing_strategy",
                "resource_id": strategy_id,
                "changes": changes or {},
            }),
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        logger.info(
            f"Admin audit: Routing strategy {action} by user {admin_user_id} "
            f"for workspace {workspace_id}"
        )
        
        return audit_log

    def log_model_retraining(
        self,
        db: Session,
        workspace_id: str,
        admin_user_id: str,
        model_type: str,  # "cost_predictor", "quality_predictor", "routing_optimizer"
        model_version: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """
        Log manual model retraining.
        
        Args:
            db: Database session
            workspace_id: Workspace ID
            admin_user_id: User ID who triggered retraining
            model_type: Type of model retrained
            model_version: New model version (if available)
            reason: Reason for manual retraining
        """
        audit_log = SecurityAuditLog(
            workspace_id=workspace_id,
            user_id=admin_user_id,
            event_type="admin_action",
            event_category="ml_model",
            success=True,
            details=json.dumps({
                "action": "manual_retraining",
                "resource_type": "ml_model",
                "resource_id": model_version,
                "model_type": model_type,
                "reason": reason or "Manual retraining triggered by admin",
            }),
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        logger.info(
            f"Admin audit: Model retraining triggered by user {admin_user_id} "
            f"for workspace {workspace_id}, model_type={model_type}"
        )
        
        return audit_log

    def log_remediation_action(
        self,
        db: Session,
        workspace_id: str,
        admin_user_id: str,
        anomaly_id: str,
        remediation_action: str,
        result: Optional[str] = None,
    ):
        """
        Log manual remediation action.
        
        Args:
            db: Database session
            workspace_id: Workspace ID
            admin_user_id: User ID who triggered remediation
            anomaly_id: Anomaly ID being remediated
            remediation_action: Action taken
            result: Result of remediation
        """
        audit_log = SecurityAuditLog(
            workspace_id=workspace_id,
            user_id=admin_user_id,
            action=AuditAction.ADMIN_ACTION,
            resource_type="anomaly",
            resource_id=anomaly_id,
            severity=AuditSeverity.HIGH,
            description=f"Manual remediation: {remediation_action}",
            metadata={
                "anomaly_id": anomaly_id,
                "remediation_action": remediation_action,
                "result": result,
            },
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        logger.info(
            f"Admin audit: Manual remediation by user {admin_user_id} "
            f"for workspace {workspace_id}, anomaly={anomaly_id}"
        )
        
        return audit_log

    def log_configuration_change(
        self,
        db: Session,
        workspace_id: Optional[str],
        admin_user_id: str,
        config_key: str,
        old_value: Optional[str],
        new_value: Optional[str],
    ):
        """
        Log configuration change.
        
        Args:
            db: Database session
            workspace_id: Workspace ID (None for global config)
            admin_user_id: User ID who made the change
            config_key: Configuration key changed
            old_value: Old value (may be None for security)
            new_value: New value (may be None for security)
        """
        # Mask sensitive values
        if "key" in config_key.lower() or "secret" in config_key.lower() or "password" in config_key.lower():
            old_value = "***MASKED***" if old_value else None
            new_value = "***MASKED***" if new_value else None
        
        audit_log = SecurityAuditLog(
            workspace_id=workspace_id,
            user_id=admin_user_id,
            event_type="admin_action",
            event_category="configuration",
            success=True,
            details=json.dumps({
                "action": "configuration_change",
                "resource_type": "configuration",
                "resource_id": config_key,
                "old_value": old_value,
                "new_value": new_value,
            }),
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        logger.info(
            f"Admin audit: Configuration change by user {admin_user_id}: {config_key}"
        )
        
        return audit_log


# Global admin audit logger
_admin_audit_logger = AdminAuditLogger()


def get_admin_audit_logger() -> AdminAuditLogger:
    """Get global admin audit logger instance."""
    return _admin_audit_logger
