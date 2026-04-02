"""Alert system with external notification routing."""

from typing import List, Dict, Optional
from datetime import datetime
from core.config import get_settings
import logging
import os
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)
settings = get_settings()


class AlertManager:
    """Manage alerts."""

    def __init__(self):
        self.alert_history: List[Dict] = []

    def send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        workspace_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Send alert."""
        alert = {
            "type": alert_type,
            "severity": severity,
            "message": message,
            "workspace_id": workspace_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.alert_history.append(alert)

        # Log based on severity
        if severity == "critical":
            logger.critical(f"ALERT [{alert_type}]: {message}")
        elif severity == "high":
            logger.error(f"ALERT [{alert_type}]: {message}")
        else:
            logger.warning(f"ALERT [{alert_type}]: {message}")

        # Send to external notification channels
        self._send_email_alert(alert) if os.getenv("ALERT_EMAIL_TO") else None
        self._send_slack_alert(alert) if os.getenv("SLACK_WEBHOOK_URL") else None
        self._send_pagerduty_alert(alert) if os.getenv("PAGERDUTY_INTEGRATION_KEY") else None

        return alert

    def _send_email_alert(self, alert: Dict):
        """Send alert via email."""
        try:
            email_to = os.getenv("ALERT_EMAIL_TO")
            email_from = os.getenv("ALERT_EMAIL_FROM", "alerts@byos-ai.com")
            smtp_host = os.getenv("SMTP_HOST", "localhost")
            smtp_port = int(os.getenv("SMTP_PORT", "25"))

            msg = MIMEMultipart()
            msg["From"] = email_from
            msg["To"] = email_to
            msg["Subject"] = f"[{alert['severity'].upper()}] {alert['type']}"

            body = f"""
            Alert Type: {alert['type']}
            Severity: {alert['severity']}
            Message: {alert['message']}
            Workspace: {alert.get('workspace_id', 'N/A')}
            Timestamp: {alert['timestamp']}
            """
            msg.attach(MIMEText(body, "plain"))

            # Send email (if SMTP configured)
            if smtp_host != "localhost":
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.send_message(msg)
                    logger.info(f"Alert email sent to {email_to}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    def _send_slack_alert(self, alert: Dict):
        """Send alert via Slack webhook."""
        try:
            webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            if not webhook_url:
                return

            severity_colors = {
                "critical": "#FF0000",
                "high": "#FF6600",
                "medium": "#FFAA00",
                "low": "#00AAFF",
            }

            payload = {
                "text": f"Alert: {alert['type']}",
                "attachments": [
                    {
                        "color": severity_colors.get(alert["severity"], "#808080"),
                        "fields": [
                            {"title": "Severity", "value": alert["severity"], "short": True},
                            {"title": "Type", "value": alert["type"], "short": True},
                            {"title": "Message", "value": alert["message"], "short": False},
                            {
                                "title": "Workspace",
                                "value": alert.get("workspace_id", "N/A"),
                                "short": True,
                            },
                            {"title": "Timestamp", "value": alert["timestamp"], "short": True},
                        ],
                    }
                ],
            }

            httpx.post(webhook_url, json=payload, timeout=5.0)
            logger.info(f"Alert sent to Slack: {alert['type']}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    def _send_pagerduty_alert(self, alert: Dict):
        """Send alert via PagerDuty."""
        try:
            integration_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")
            if not integration_key:
                return

            # Only send critical/high severity to PagerDuty
            if alert["severity"] not in ["critical", "high"]:
                return

            payload = {
                "routing_key": integration_key,
                "event_action": "trigger",
                "payload": {
                    "summary": f"{alert['type']}: {alert['message']}",
                    "severity": alert["severity"],
                    "source": "byos-ai-backend",
                    "custom_details": alert.get("metadata", {}),
                },
            }

            httpx.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                timeout=5.0,
            )
            logger.info(f"Alert sent to PagerDuty: {alert['type']}")
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")

    def get_alerts(
        self,
        workspace_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get recent alerts."""
        alerts = self.alert_history[-limit:]

        if workspace_id:
            alerts = [a for a in alerts if a.get("workspace_id") == workspace_id]
        if alert_type:
            alerts = [a for a in alerts if a.get("type") == alert_type]

        return alerts


# Global alert manager
_alert_manager = AlertManager()


def send_alert(
    alert_type: str,
    severity: str,
    message: str,
    workspace_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
):
    """Send alert."""
    return _alert_manager.send_alert(alert_type, severity, message, workspace_id, metadata)
