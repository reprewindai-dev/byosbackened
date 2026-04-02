"""Intrusion Detection System (IDS)."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from db.models import SecurityAuditLog, AbuseLog
from core.config import get_settings
import logging
import re

logger = logging.getLogger(__name__)
settings = get_settings()


class IntrusionDetectionSystem:
    """Detect and respond to security intrusions."""

    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        # SQL injection attempts
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        # XSS attempts
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        # Path traversal
        r"\.\./",
        r"\.\.\\",
        # Command injection
        r"[;&|`$]",
        r"\b(cat|ls|pwd|whoami|id|uname|ps|kill|rm|mv|cp)\b",
        # Suspicious user agents
        r"(sqlmap|nikto|nmap|masscan|zap|burp)",
        # Suspicious paths
        r"(/admin|/phpmyadmin|/wp-admin|/\.env|/config|/backup)",
    ]

    def __init__(self):
        self.threat_levels = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }

    def detect_intrusion(
        self,
        db: Session,
        request_path: str,
        request_method: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect potential intrusion attempts.

        Returns:
            {
                "is_intrusion": bool,
                "threat_level": str,
                "reason": str,
                "patterns_detected": List[str],
            }
        """
        patterns_detected = []
        threat_level = "low"

        # Check request path — skip SQL-keyword patterns on API routes.
        # SQL injection in paths is handled by input validation (allow_sql=True for paths).
        SQL_KW = r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\b)"
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern == SQL_KW:
                continue  # Skip: already handled by input validation middleware
            if re.search(pattern, request_path, re.IGNORECASE):
                patterns_detected.append(f"Path pattern: {pattern}")
                threat_level = self._escalate_threat(threat_level, "medium")

        # Check headers
        user_agent = headers.get("user-agent", "")
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                patterns_detected.append(f"User-Agent pattern: {pattern}")
                threat_level = self._escalate_threat(threat_level, "high")

        # Check body
        if body:
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, body, re.IGNORECASE):
                    patterns_detected.append(f"Body pattern: {pattern}")
                    threat_level = self._escalate_threat(threat_level, "high")

        # Check for rapid requests from same IP
        if ip_address:
            try:
                recent_requests = (
                    db.query(SecurityAuditLog)
                    .filter(
                        SecurityAuditLog.ip_address == ip_address,
                        SecurityAuditLog.created_at >= datetime.utcnow() - timedelta(minutes=1),
                    )
                    .count()
                )
            except OperationalError as e:
                # Local/dev safety: allow the API to boot even if migrations haven't run yet.
                logger.warning(
                    f"Security audit log table unavailable; skipping rapid-request check. error={e}"
                )
                recent_requests = 0

            if recent_requests > 200:  # More than 200 requests per minute
                patterns_detected.append(f"Rapid requests: {recent_requests}/min")
                threat_level = self._escalate_threat(threat_level, "high")

        # Check for failed authentication attempts
        if user_id:
            try:
                failed_auths = (
                    db.query(SecurityAuditLog)
                    .filter(
                        SecurityAuditLog.user_id == user_id,
                        SecurityAuditLog.event_type == "login",
                        SecurityAuditLog.success == False,
                        SecurityAuditLog.created_at >= datetime.utcnow() - timedelta(minutes=5),
                    )
                    .count()
                )
            except OperationalError as e:
                logger.warning(
                    f"Security audit log table unavailable; skipping failed-auth check. error={e}"
                )
                failed_auths = 0

            if failed_auths > 10:
                patterns_detected.append(f"Failed auth attempts: {failed_auths}")
                threat_level = self._escalate_threat(threat_level, "critical")

        # Check for suspicious paths
        suspicious_paths = [
            "/admin",
            "/phpmyadmin",
            "/wp-admin",
            "/.env",
            "/config",
            "/backup",
            "/shell",
            "/cmd",
            "/exec",
            "/eval",
        ]
        rp_lower = request_path.lower()
        for spath in suspicious_paths:
            # Exact path-segment match to avoid false positives (e.g. /exec != /execute)
            seg = re.escape(spath.lstrip("/"))
            if re.search(r"(?:^|/)" + seg + r"(?:/|$)", rp_lower):
                patterns_detected.append(f"Suspicious path: {spath}")
                threat_level = self._escalate_threat(threat_level, "high")

        is_intrusion = len(patterns_detected) > 0

        if is_intrusion:
            # Log intrusion attempt
            abuse_log = AbuseLog(
                workspace_id=workspace_id,
                user_id=user_id,
                ip_address=ip_address,
                abuse_type="intrusion_detection",
                severity=threat_level,
                reason=f"Intrusion detected: {', '.join(patterns_detected[:3])}",
                blocked=True,
            )
            db.add(abuse_log)
            db.commit()

            logger.warning(
                f"Intrusion detected: level={threat_level}, "
                f"ip={ip_address}, user={user_id}, patterns={patterns_detected}"
            )

        return {
            "is_intrusion": is_intrusion,
            "threat_level": threat_level,
            "reason": ", ".join(patterns_detected) if patterns_detected else None,
            "patterns_detected": patterns_detected,
        }

    def _escalate_threat(self, current_level: str, new_level: str) -> str:
        """Escalate threat level."""
        current_score = self.threat_levels.get(current_level, 0)
        new_score = self.threat_levels.get(new_level, 0)
        return new_level if new_score > current_score else current_level

    def should_block(self, threat_level: str) -> bool:
        """Determine if request should be blocked."""
        return threat_level in ["high", "critical"]

    def get_response_delay(self, threat_level: str) -> float:
        """Get response delay based on threat level."""
        delays = {
            "low": 0.0,
            "medium": 0.5,
            "high": 2.0,
            "critical": 5.0,
        }
        return delays.get(threat_level, 0.0)
