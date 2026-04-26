"""AI audit logger - cryptographically verifiable."""
import hashlib
import hmac
import json
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from db.models import AIAuditLog
from core.config import get_settings
from core.privacy.pii_detection import detect_pii
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class AuditLogger:
    """Log AI operations for compliance."""

    def __init__(self):
        self.last_log_hash: Optional[str] = None

    def log_ai_operation(
        self,
        db: Session,
        workspace_id: str,
        user_id: str,
        operation_type: str,
        provider: str,
        model: Optional[str],
        input_data: str,
        output_data: str,
        cost: Decimal,
        tokens_input: Optional[int],
        tokens_output: Optional[int],
        routing_decision_id: Optional[str] = None,
        routing_reasoning: Optional[str] = None,
    ) -> AIAuditLog:
        """
        Create immutable audit log entry.
        
        Returns audit log with cryptographic hash.
        """
        # Hash input and output
        input_hash = hashlib.sha256(input_data.encode()).hexdigest()
        output_hash = hashlib.sha256(output_data.encode()).hexdigest()
        
        # Detect PII
        pii_detected_list = detect_pii(input_data + " " + output_data)
        pii_detected = len(pii_detected_list) > 0
        pii_types = [pii["type"] for pii in pii_detected_list] if pii_detected else []
        
        # Create preview (first 500 chars)
        input_preview = input_data[:500] if len(input_data) > 500 else input_data
        output_preview = output_data[:500] if len(output_data) > 500 else output_data
        
        # Create audit log entry
        audit_log = AIAuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            operation_type=operation_type,
            provider=provider,
            model=model,
            input_hash=input_hash,
            output_hash=output_hash,
            input_preview=input_preview,
            output_preview=output_preview,
            cost=cost,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            routing_decision_id=routing_decision_id,
            routing_reasoning=routing_reasoning,
            pii_detected=pii_detected,
            pii_types=pii_types,
            previous_log_hash=self.last_log_hash,
        )
        
        # Calculate log hash (HMAC-SHA256 of entire entry)
        log_hash = self._calculate_log_hash(audit_log)
        audit_log.log_hash = log_hash
        
        # Save to database
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        # Update last log hash for chaining
        self.last_log_hash = log_hash
        
        logger.info(f"Audit log created: {audit_log.id}, hash={log_hash[:16]}...")
        
        return audit_log

    def _calculate_log_hash(self, audit_log: AIAuditLog) -> str:
        """Calculate HMAC-SHA256 hash of audit log entry."""
        # Create string representation of log entry
        log_data = {
            "id": audit_log.id,
            "workspace_id": audit_log.workspace_id,
            "user_id": audit_log.user_id,
            "operation_type": audit_log.operation_type,
            "provider": audit_log.provider,
            "model": audit_log.model,
            "input_hash": audit_log.input_hash,
            "output_hash": audit_log.output_hash,
            "cost": str(audit_log.cost),
            "created_at": audit_log.created_at.isoformat() if audit_log.created_at else None,
            "previous_log_hash": audit_log.previous_log_hash,
        }
        
        log_string = json.dumps(log_data, sort_keys=True)
        
        # Calculate HMAC
        secret = settings.secret_key.encode()
        hmac_hash = hmac.new(secret, log_string.encode(), hashlib.sha256)
        return hmac_hash.hexdigest()

    def verify_log(self, audit_log: AIAuditLog) -> bool:
        """Verify audit log integrity."""
        calculated_hash = self._calculate_log_hash(audit_log)
        return calculated_hash == audit_log.log_hash


# Global audit logger instance
_audit_logger = AuditLogger()


def log_ai_operation(
    db: Session,
    workspace_id: str,
    user_id: str,
    operation_type: str,
    provider: str,
    model: Optional[str],
    input_data: str,
    output_data: str,
    cost: Decimal,
    tokens_input: Optional[int] = None,
    tokens_output: Optional[int] = None,
    routing_decision_id: Optional[str] = None,
    routing_reasoning: Optional[str] = None,
) -> AIAuditLog:
    """Log AI operation."""
    return _audit_logger.log_ai_operation(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        operation_type=operation_type,
        provider=provider,
        model=model,
        input_data=input_data,
        output_data=output_data,
        cost=cost,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        routing_decision_id=routing_decision_id,
        routing_reasoning=routing_reasoning,
    )


def verify_log(audit_log: AIAuditLog) -> bool:
    """Verify audit log integrity."""
    return _audit_logger.verify_log(audit_log)
