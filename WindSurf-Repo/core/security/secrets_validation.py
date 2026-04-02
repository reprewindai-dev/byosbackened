"""Secrets validation and rotation documentation."""

from core.config import get_settings
from core.autonomous.feature_flags import get_feature_flags
from core.cost_intelligence.kill_switch import get_cost_kill_switch
from decimal import Decimal, InvalidOperation
import os
import logging

logger = logging.getLogger(__name__)


def validate_secrets_on_startup():
    """
    Validate that required secrets are configured.

    Called on application startup to ensure secrets are present.
    """
    settings = get_settings()
    errors = []
    warnings = []

    # Critical secrets (must be set)
    if settings.secret_key == "change-me-in-production-use-env-var":
        if settings.debug:
            # Development: Warn but don't fail
            warnings.append("SECRET_KEY is using default value - change this in production")
        else:
            # Production: Fail fast
            errors.append("SECRET_KEY must be changed from default value")

    # Optional but recommended
    if not settings.huggingface_api_key:
        warnings.append("HUGGINGFACE_API_KEY not set (some features may not work)")

    if not settings.serpapi_key:
        warnings.append("SERPAPI_KEY not set (search features will not work)")

    # S3 credentials (required for ML model storage)
    if settings.s3_access_key_id == "minioadmin" and settings.s3_secret_access_key == "minioadmin":
        warnings.append("S3 credentials are using default MinIO values (OK for development)")

    # Log errors and warnings
    for error in errors:
        logger.error(f"Secret validation error: {error}")

    for warning in warnings:
        logger.warning(f"Secret validation warning: {warning}")

    if errors:
        raise ValueError(f"Secret validation failed: {', '.join(errors)}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# Secret rotation documentation
SECRET_ROTATION_GUIDE = """
# Secret Rotation Guide

## Overview
This guide documents how to rotate secrets in the BYOS AI Backend.

## Secrets to Rotate

### 1. SECRET_KEY (JWT Signing Key)
**Frequency**: Quarterly or after security incident
**Impact**: All existing JWT tokens will be invalidated
**Procedure**:
1. Generate new key: `openssl rand -hex 32`
2. Update environment variable: `SECRET_KEY=<new_key>`
3. Restart application
4. Users will need to re-authenticate

### 2. Database Password
**Frequency**: Quarterly
**Impact**: Brief downtime during rotation
**Procedure**:
1. Update database password
2. Update DATABASE_URL environment variable
3. Restart application
4. Verify connection

### 3. S3/MinIO Credentials
**Frequency**: Quarterly
**Impact**: ML models stored in S3 may be temporarily inaccessible
**Procedure**:
1. Create new S3 credentials
2. Update S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY
3. Restart application
4. Verify ML models can be loaded

### 4. Provider API Keys (OpenAI, Hugging Face, SERP API)
**Frequency**: As needed (if compromised)
**Impact**: Provider-specific features may be temporarily unavailable
**Procedure**:
1. Generate new API key from provider dashboard
2. Update corresponding environment variable (OPENAI_API_KEY, HUGGINGFACE_API_KEY, SERPAPI_KEY)
3. Restart application
4. No downtime if multiple providers configured

### 5. Encryption Key (ENCRYPTION_KEY)
**Frequency**: Annually or after security incident
**Impact**: Encrypted fields cannot be decrypted with old key
**Procedure**:
1. Decrypt all encrypted fields using old key
2. Generate new key: `openssl rand -hex 32`
3. Re-encrypt all fields with new key
4. Update ENCRYPTION_KEY environment variable
5. Restart application

## Best Practices

1. **Use Secret Management**: Prefer using AWS Secrets Manager, HashiCorp Vault, or similar
2. **Rotate Regularly**: Set calendar reminders for quarterly rotations
3. **Test Rotation**: Test rotation procedure in staging before production
4. **Monitor After Rotation**: Check logs and metrics after rotation
5. **Document Changes**: Log all secret rotations in audit log

## Automated Rotation (Future Enhancement)

Consider implementing automated secret rotation using:
- AWS Secrets Manager rotation lambda
- HashiCorp Vault dynamic secrets
- Kubernetes secrets rotation
"""


def get_secret_rotation_guide() -> str:
    """Get secret rotation guide."""
    return SECRET_ROTATION_GUIDE


def validate_production_config():
    """
    Validate production configuration on startup.

    Checks:
    1. Alert channels configured (fail in production if none)
    2. Budget caps valid (fail if invalid)
    3. Feature flags loaded correctly (log states)

    Raises ValueError if production config is invalid.
    """
    settings = get_settings()
    errors = []
    warnings = []

    # First, run basic secrets validation
    try:
        secrets_result = validate_secrets_on_startup()
        if not secrets_result["valid"]:
            errors.extend(secrets_result["errors"])
        warnings.extend(secrets_result["warnings"])
    except ValueError as e:
        errors.append(str(e))

    # 1. Validate alert channels
    alert_email = os.getenv("ALERT_EMAIL_TO")
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    pagerduty_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")

    has_alert_channel = bool(alert_email or slack_webhook or pagerduty_key)

    if not has_alert_channel:
        if settings.debug:
            # Development: Log loud warning but don't fail
            logger.critical(
                "⚠️⚠️⚠️ NO ALERT CHANNEL CONFIGURED ⚠️⚠️⚠️\n"
                "Production alerts will not be delivered!\n"
                "Set at least one of: ALERT_EMAIL_TO, SLACK_WEBHOOK_URL, PAGERDUTY_INTEGRATION_KEY"
            )
            warnings.append("No alert channel configured - alerts will not be delivered")
        else:
            # Production: Fail fast
            errors.append(
                "No alert channel configured. Set at least one of: "
                "ALERT_EMAIL_TO, SLACK_WEBHOOK_URL, PAGERDUTY_INTEGRATION_KEY"
            )
    else:
        configured_channels = []
        if alert_email:
            configured_channels.append("Email")
        if slack_webhook:
            configured_channels.append("Slack")
        if pagerduty_key:
            configured_channels.append("PagerDuty")
        logger.info(f"Alert channels configured: {', '.join(configured_channels)}")

    # 2. Validate budget caps
    try:
        kill_switch = get_cost_kill_switch()

        global_cap = kill_switch.GLOBAL_DAILY_CAP
        workspace_cap = kill_switch.DEFAULT_WORKSPACE_DAILY_CAP

        # Validate global cap
        if global_cap <= 0:
            errors.append(f"GLOBAL_DAILY_COST_CAP must be > 0, got: {global_cap}")
        elif global_cap < workspace_cap:
            errors.append(
                f"GLOBAL_DAILY_COST_CAP ({global_cap}) must be >= DEFAULT_WORKSPACE_DAILY_CAP ({workspace_cap})"
            )
        else:
            logger.info(f"Budget caps validated: Global=${global_cap}, Workspace=${workspace_cap}")

        # Validate workspace cap
        if workspace_cap <= 0:
            errors.append(f"DEFAULT_WORKSPACE_DAILY_CAP must be > 0, got: {workspace_cap}")

        # Validate kill switch enabled
        if not kill_switch._enabled:
            warnings.append("Cost kill switch is DISABLED - cost caps will not be enforced")
        else:
            logger.info("Cost kill switch is ENABLED")

    except (ValueError, InvalidOperation, TypeError) as e:
        errors.append(f"Invalid budget cap configuration: {e}")

    # 3. Validate feature flags loaded correctly
    try:
        flags = get_feature_flags()
        all_flags = flags.get_all_flags()

        # Log all flag states for visibility
        logger.info("Feature flags loaded:")
        for flag_name, flag_value in sorted(all_flags.items()):
            status = "✅ ENABLED" if flag_value else "❌ DISABLED"
            logger.info(f"  {flag_name}: {status}")

        # Verify flags can be toggled (test one)
        test_flag = "autonomous_routing_enabled"
        original_value = flags.is_enabled(test_flag)
        flags.disable(test_flag)
        if flags.is_enabled(test_flag) != False:
            errors.append(f"Feature flag {test_flag} failed toggle test")
        flags.enable(test_flag) if original_value else flags.disable(test_flag)

        # Check if all autonomous features are disabled (safe default)
        enabled_count = sum(1 for v in all_flags.values() if v)
        if enabled_count == 0:
            logger.info("All autonomous features are DISABLED (safe default)")
        else:
            logger.info(f"{enabled_count} autonomous feature(s) are ENABLED")

    except Exception as e:
        errors.append(f"Feature flags validation failed: {e}")

    # Log all warnings
    for warning in warnings:
        logger.warning(f"Configuration warning: {warning}")

    # Fail fast in production if errors
    if errors:
        error_msg = "Production configuration validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        logger.critical(error_msg)
        raise ValueError(error_msg)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "alert_channels_configured": has_alert_channel,
        "budget_caps_valid": len([e for e in errors if "budget" in e.lower() or "cap" in e.lower()])
        == 0,
        "feature_flags_loaded": True,
    }
