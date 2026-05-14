from __future__ import annotations

import os

import pytest

os.environ.setdefault("DEBUG", "true")
# Keep this aligned with app-level tests that import settings once per process.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_marketplace_public_access.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough")
os.environ.setdefault("LICENSE_ADMIN_TOKEN", "test-license-admin-token")

from apps.api.routers import workspace


def test_status_target_validation_rejects_placeholder_webhook():
    with pytest.raises(Exception) as exc:
        workspace._validate_status_target("webhook", "https://example.com/webhook")

    assert getattr(exc.value, "status_code", None) == 400


def test_status_target_validation_accepts_slack_hook():
    target = "https://hooks.slack.com/services/T000/B000/abcdef"

    assert workspace._validate_status_target("slack", target) == target


def test_status_rss_contains_operational_item_when_no_incidents():
    xml = workspace._render_status_rss(
        {
            "timestamp": "2026-05-05T12:00:00",
            "incidents": [],
            "maintenance": [],
        }
    )

    assert "<rss version=\"2.0\">" in xml
    assert "All Veklom services operational" in xml
    assert "https://veklom.com/status#veklom-operational" in xml
