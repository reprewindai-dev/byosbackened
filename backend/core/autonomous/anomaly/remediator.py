"""Auto-remediation for detected anomalies."""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from core.autonomous.ml_models.routing_optimizer import get_routing_optimizer_ml
from core.autonomous.feature_flags import get_feature_flags
from core.safety.rate_limiting import RateLimiter
from core.incident.alerting import send_alert
from db.models import Anomaly
from db.models.anomaly import AnomalyType, AnomalySeverity, AnomalyStatus
from core.autonomous.schemas.anomaly import validate_anomaly_metadata
import logging

logger = logging.getLogger(__name__)
routing_optimizer_ml = get_routing_optimizer_ml()
rate_limiter = RateLimiter()
feature_flags = get_feature_flags()


class AutoRemediator:
    """
    Auto-remediate common issues.
    
    Prevents problems before they impact customers.
    Creates "invisible value" - problems that never happened.
    """

    def remediate(
        self,
        workspace_id: str,
        anomalies: List[Dict],
        db: Optional[Session] = None,
    ) -> Dict[str, any]:
        """
        Auto-remediate detected anomalies.
        
        Creates Anomaly records in database with remediation actions logged.
        Returns remediation actions taken.
        """
        # Check kill switch
        if not feature_flags.is_enabled("auto_remediation_enabled"):
            logger.info("Auto-remediation disabled via kill switch")
            return {
                "remediated": False,
                "actions": [],
                "reason": "Auto-remediation disabled via kill switch",
            }
        
        actions_taken = []
        anomaly_records = []
        
        # Map anomaly types to AnomalyType enum
        type_map = {
            "cost_spike": AnomalyType.COST_SPIKE,
            "traffic_spike": AnomalyType.TRAFFIC_SPIKE,
            "quality_degradation": AnomalyType.QUALITY_DEGRADATION,
            "latency_spike": AnomalyType.LATENCY_SPIKE,
            "failure_rate_increase": AnomalyType.FAILURE_RATE_INCREASE,
            "unusual_pattern": AnomalyType.UNUSUAL_PATTERN,
        }
        
        # Map severity strings to AnomalySeverity enum
        severity_map = {
            "low": AnomalySeverity.LOW,
            "medium": AnomalySeverity.MEDIUM,
            "high": AnomalySeverity.HIGH,
            "critical": AnomalySeverity.CRITICAL,
        }
        
        for anomaly in anomalies:
            anomaly_type_str = anomaly.get("type")
            severity_str = anomaly.get("severity", "medium")
            message = anomaly.get("message", f"{anomaly_type_str} detected")
            
            # Map to enums
            anomaly_type = type_map.get(anomaly_type_str, AnomalyType.UNUSUAL_PATTERN)
            severity = severity_map.get(severity_str, AnomalySeverity.MEDIUM)
            
            # Determine remediation action
            remediation_action = None
            action_result = None
            
            if anomaly_type_str == "cost_spike":
                remediation_action = "switch_provider: Switching to cheaper provider to reduce costs"
                action_result = "initiated"
                actions_taken.append({
                    "action": "switch_provider",
                    "reason": "Cost spike detected",
                    "severity": severity_str,
                })
                logger.warning(f"Auto-remediating cost spike for workspace {workspace_id}")
            
            elif anomaly_type_str == "traffic_spike":
                remediation_action = "rate_limit: Applying rate limiting to prevent abuse"
                action_result = "initiated"
                actions_taken.append({
                    "action": "rate_limit",
                    "reason": "Traffic spike detected",
                    "severity": severity_str,
                })
                logger.warning(f"Auto-remediating traffic spike for workspace {workspace_id}")
            
            elif anomaly_type_str == "quality_degradation":
                remediation_action = "switch_provider: Switching to higher-quality provider"
                action_result = "initiated"
                actions_taken.append({
                    "action": "switch_provider",
                    "reason": "Quality degradation detected",
                    "severity": severity_str,
                })
                logger.warning(f"Auto-remediating quality degradation for workspace {workspace_id}")
            
            # Create Anomaly record if db provided
            if db:
                # Validate metadata
                metadata = validate_anomaly_metadata(anomaly.get("metadata", {}))
                
                anomaly_record = Anomaly(
                    workspace_id=workspace_id,
                    anomaly_type=anomaly_type,
                    severity=severity,
                    status=AnomalyStatus.DETECTED,
                    detected_by="anomaly_detector",
                    description=message,
                    metadata=metadata,
                    baseline_value=anomaly.get("baseline_value"),
                    actual_value=anomaly.get("actual_value"),
                    deviation_percent=anomaly.get("deviation_percent"),
                    remediation_action=remediation_action,
                    remediated_at=datetime.utcnow() if remediation_action else None,
                    remediation_result=action_result,
                )
                
                db.add(anomaly_record)
                anomaly_records.append(anomaly_record)
            
            # Alert on high-severity anomalies
            if severity_str in ["high", "critical"]:
                send_alert(
                    alert_type="anomaly",
                    severity=severity_str,
                    message=f"{severity_str.capitalize()}-severity anomaly detected: {anomaly_type_str}",
                    workspace_id=workspace_id,
                    metadata=anomaly,
                )
        
        # Commit anomaly records if db provided
        if db and anomaly_records:
            try:
                db.commit()
                for record in anomaly_records:
                    db.refresh(record)
                logger.info(
                    f"Created {len(anomaly_records)} anomaly records for workspace {workspace_id}"
                )
            except Exception as e:
                logger.error(f"Error creating anomaly records: {e}")
                db.rollback()
        
        return {
            "remediated": len(actions_taken) > 0,
            "actions": actions_taken,
            "anomaly_records_created": len(anomaly_records),
        }
    
    def update_remediation_result(
        self,
        db: Session,
        anomaly_id: str,
        success: bool,
        result_details: Optional[str] = None,
    ):
        """
        Update remediation result after action completes.
        
        Call this after remediation action has been executed to record outcome.
        """
        anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
        
        if not anomaly:
            logger.warning(f"Anomaly {anomaly_id} not found for remediation update")
            return
        
        anomaly.status = AnomalyStatus.REMEDIATED
        anomaly.remediation_result = (
            f"success: {result_details}" if success else f"failure: {result_details or 'Unknown error'}"
        )
        anomaly.remediated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(anomaly)
        
        logger.info(
            f"Updated remediation result for anomaly {anomaly_id}: "
            f"success={success}, result={anomaly.remediation_result}"
        )


# Global auto-remediator
_auto_remediator = AutoRemediator()


def get_auto_remediator() -> AutoRemediator:
    """Get global auto-remediator instance."""
    return _auto_remediator
