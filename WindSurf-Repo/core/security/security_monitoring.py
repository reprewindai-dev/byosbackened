"""Security monitoring and alerting system."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import SecurityAuditLog, AbuseLog, IncidentLog
from core.config import get_settings
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityMonitor:
    """Monitor security events and send alerts."""

    def __init__(self):
        self.alert_thresholds = {
            "failed_logins": 10,  # Alert after 10 failed logins
            "intrusion_attempts": 5,  # Alert after 5 intrusion attempts
            "ddos_attacks": 3,  # Alert after 3 DDoS attacks
            "suspicious_activity": 10,  # Alert after 10 suspicious activities
        }

    def check_security_events(
        self,
        db: Session,
        workspace_id: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Check security events in last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)

        # Failed logins
        failed_logins = (
            db.query(SecurityAuditLog)
            .filter(
                SecurityAuditLog.event_type == "login",
                SecurityAuditLog.success == False,
                SecurityAuditLog.created_at >= since,
            )
            .count()
        )

        # Intrusion attempts
        intrusion_attempts = (
            db.query(AbuseLog)
            .filter(
                AbuseLog.abuse_type == "intrusion_detection",
                AbuseLog.created_at >= since,
            )
            .count()
        )

        # DDoS attacks
        ddos_attacks = (
            db.query(AbuseLog)
            .filter(
                AbuseLog.abuse_type == "rate_limit",
                AbuseLog.severity.in_(["high", "critical"]),
                AbuseLog.created_at >= since,
            )
            .count()
        )

        # Suspicious activity
        suspicious_activity = (
            db.query(SecurityAuditLog)
            .filter(
                SecurityAuditLog.event_category == "suspicious",
                SecurityAuditLog.created_at >= since,
            )
            .count()
        )

        alerts = []

        # Check thresholds
        if failed_logins >= self.alert_thresholds["failed_logins"]:
            alerts.append(
                {
                    "type": "failed_logins",
                    "severity": "high",
                    "message": f"{failed_logins} failed login attempts in last {hours} hours",
                    "count": failed_logins,
                }
            )

        if intrusion_attempts >= self.alert_thresholds["intrusion_attempts"]:
            alerts.append(
                {
                    "type": "intrusion_attempts",
                    "severity": "critical",
                    "message": f"{intrusion_attempts} intrusion attempts detected in last {hours} hours",
                    "count": intrusion_attempts,
                }
            )

        if ddos_attacks >= self.alert_thresholds["ddos_attacks"]:
            alerts.append(
                {
                    "type": "ddos_attacks",
                    "severity": "critical",
                    "message": f"{ddos_attacks} DDoS attacks detected in last {hours} hours",
                    "count": ddos_attacks,
                }
            )

        if suspicious_activity >= self.alert_thresholds["suspicious_activity"]:
            alerts.append(
                {
                    "type": "suspicious_activity",
                    "severity": "medium",
                    "message": f"{suspicious_activity} suspicious activities in last {hours} hours",
                    "count": suspicious_activity,
                }
            )

        return {
            "failed_logins": failed_logins,
            "intrusion_attempts": intrusion_attempts,
            "ddos_attacks": ddos_attacks,
            "suspicious_activity": suspicious_activity,
            "alerts": alerts,
            "status": "critical" if alerts else "ok",
        }

    def send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: Optional[Dict] = None,
    ):
        """Send security alert."""
        logger.warning(f"SECURITY ALERT [{severity.upper()}]: {alert_type} - {message}")

        # Log to incident log
        # In production, also send email/SMS/Slack notifications

        if severity in ["high", "critical"]:
            # Send immediate notification
            logger.critical(f"CRITICAL SECURITY ALERT: {message}")
            # TODO: Integrate with notification service (email, SMS, Slack, etc.)


class SecurityHealthCheck:
    """Check overall security health."""

    def __init__(self):
        self.monitor = SecurityMonitor()

    def get_security_status(
        self,
        db: Session,
    ) -> Dict[str, Any]:
        """Get overall security status."""
        # Check last 24 hours
        events = self.monitor.check_security_events(db, hours=24)

        # Determine overall status
        if events["status"] == "critical":
            overall_status = "at_risk"
        elif events["alerts"]:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "events": events,
            "recommendations": self._get_recommendations(events),
            "last_check": datetime.utcnow().isoformat(),
        }

    def _get_recommendations(self, events: Dict) -> List[str]:
        """Get security recommendations."""
        recommendations = []

        if events["failed_logins"] > 0:
            recommendations.append(
                "Consider implementing account lockout after failed login attempts"
            )

        if events["intrusion_attempts"] > 0:
            recommendations.append("Review firewall rules and IP blocking policies")

        if events["ddos_attacks"] > 0:
            recommendations.append(
                "Consider using a DDoS protection service (Cloudflare, AWS Shield)"
            )

        if events["suspicious_activity"] > 0:
            recommendations.append("Review security audit logs for suspicious patterns")

        if not recommendations:
            recommendations.append("Security status is healthy. Continue monitoring.")

        return recommendations
