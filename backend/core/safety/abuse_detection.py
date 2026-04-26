"""Abuse detection."""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import SecurityAuditLog
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class AbuseDetector:
    """Detect abuse patterns."""

    def __init__(self):
        self.suspicious_patterns = []

    def detect_abuse(
        self,
        db: Session,
        workspace_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        operation_type: str,
    ) -> Dict[str, Any]:
        """
        Detect abuse patterns.
        
        Returns:
        - is_abuse: bool
        - reason: str
        - severity: str (low, medium, high)
        """
        # Check for rapid requests
        recent_requests = db.query(SecurityAuditLog).filter(
            SecurityAuditLog.workspace_id == workspace_id,
            SecurityAuditLog.created_at >= datetime.utcnow() - timedelta(minutes=1),
        ).count()
        
        if recent_requests > 100:  # More than 100 requests per minute
            return {
                "is_abuse": True,
                "reason": f"Too many requests: {recent_requests} in last minute",
                "severity": "high",
            }
        
        # Check for failed authentication attempts
        if user_id:
            failed_auths = db.query(SecurityAuditLog).filter(
                SecurityAuditLog.user_id == user_id,
                SecurityAuditLog.event_type == "login",
                SecurityAuditLog.success == False,
                SecurityAuditLog.created_at >= datetime.utcnow() - timedelta(minutes=5),
            ).count()
            
            if failed_auths > 5:
                return {
                    "is_abuse": True,
                    "reason": f"Too many failed login attempts: {failed_auths}",
                    "severity": "high",
                }
        
        # Check IP address patterns
        if ip_address:
            ip_requests = db.query(SecurityAuditLog).filter(
                SecurityAuditLog.ip_address == ip_address,
                SecurityAuditLog.created_at >= datetime.utcnow() - timedelta(hours=1),
            ).count()
            
            if ip_requests > 1000:  # More than 1000 requests per hour from same IP
                return {
                    "is_abuse": True,
                    "reason": f"Too many requests from IP: {ip_requests} in last hour",
                    "severity": "medium",
                }
        
        return {
            "is_abuse": False,
            "reason": None,
            "severity": None,
        }
