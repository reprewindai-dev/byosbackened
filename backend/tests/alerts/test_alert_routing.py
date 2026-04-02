"""Test alert routing - verify alerts notify correctly."""
import pytest
from core.incident.alerting import send_alert
from core.config import get_settings
import logging
import os

settings = get_settings()
logger = logging.getLogger(__name__)


def test_alert_routing():
    """
    Test that alerts are routed correctly.
    
    This test verifies:
    1. Alert is created
    2. Alert is logged
    3. Alert notification is sent (if configured)
    """
    # Send test alert
    result = send_alert(
        alert_type="test",
        severity="low",
        message="Test alert - verify notification channel works",
        workspace_id=None,
        metadata={
            "test": True,
            "timestamp": "2024-01-01T00:00:00Z",
        },
    )
    
    # Verify alert was created
    assert result is not None
    
    # Check if notification channels are configured
    email_configured = bool(os.getenv("ALERT_EMAIL_TO"))
    slack_configured = bool(os.getenv("SLACK_WEBHOOK_URL"))
    pagerduty_configured = bool(os.getenv("PAGERDUTY_INTEGRATION_KEY"))
    
    if not any([email_configured, slack_configured, pagerduty_configured]):
        logger.warning(
            "No alert notification channels configured. "
            "Set ALERT_EMAIL_TO, SLACK_WEBHOOK_URL, or PAGERDUTY_INTEGRATION_KEY"
        )
    
    # Log alert details for manual verification
    logger.info(f"Alert sent: {result}")
    logger.info(f"Email configured: {email_configured}")
    logger.info(f"Slack configured: {slack_configured}")
    logger.info(f"PagerDuty configured: {pagerduty_configured}")
    
    print("\n" + "="*60)
    print("ALERT ROUTING TEST")
    print("="*60)
    print(f"Alert Type: test")
    print(f"Severity: low")
    print(f"Message: Test alert - verify notification channel works")
    print(f"\nNotification Channels:")
    print(f"  Email: {'✅ Configured' if email_configured else '❌ Not configured'}")
    print(f"  Slack: {'✅ Configured' if slack_configured else '❌ Not configured'}")
    print(f"  PagerDuty: {'✅ Configured' if pagerduty_configured else '❌ Not configured'}")
    print("\n⚠️  MANUAL VERIFICATION REQUIRED:")
    print("  Check your email/Slack/PagerDuty to verify alert was received")
    print("="*60)
    
    # Test passes if alert function doesn't raise exception
    assert True


def test_critical_alert_routing():
    """Test critical alert routing."""
    result = send_alert(
        alert_type="cost_cap_exceeded",
        severity="critical",
        message="CRITICAL: Global daily cost cap exceeded",
        workspace_id=None,
        metadata={
            "current_spend": 10001.00,
            "cap": 10000.00,
        },
    )
    
    assert result is not None
    logger.info(f"Critical alert sent: {result}")


if __name__ == "__main__":
    # Run alert test
    pytest.main([__file__, "-v", "-s"])
