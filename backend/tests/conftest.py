"""Shared test bootstrap for local and CI runs.

The backend package is sometimes installed editable from a temporary worktree on
developer machines. Put this checkout's backend directory first so tests never
resolve stale packages, and default tests to SQLite unless a caller deliberately
provides a database URL.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
backend_path = str(BACKEND_ROOT)
if sys.path[0] != backend_path:
    sys.path.insert(0, backend_path)

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_suite.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough")
os.environ.setdefault("LICENSE_ADMIN_TOKEN", "test-license-admin-token")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-github-client-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-github-client-secret")
os.environ.setdefault("GITHUB_REDIRECT_URI", "https://veklom.com/auth/github/callback")
os.environ.setdefault("ALERT_EMAIL_TO", "alerts@example.test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/15")
