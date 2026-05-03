import os

from fastapi.testclient import TestClient

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_marketplace_public_access.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough")
os.environ.setdefault("LICENSE_ADMIN_TOKEN", "test-license-admin-token")

from apps.api.main import app
from db.session import get_db


class _ListingQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _FakeDB:
    def query(self, *args, **kwargs):
        return _ListingQuery()


def _fake_db():
    yield _FakeDB()


def test_public_marketplace_listings_do_not_require_auth():
    app.dependency_overrides[get_db] = _fake_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/listings")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 10
    assert {row["id"] for row in payload} >= {
        "github-actions-checkout",
        "docker-build-push-action",
        "aws-configure-credentials",
        "step-security-harden-runner",
    }
    assert all(row["source_url"].startswith("https://") for row in payload)


def test_public_marketplace_aliases_return_real_catalog():
    app.dependency_overrides[get_db] = _fake_db
    try:
        with TestClient(app) as client:
            listings = client.get("/api/v1/marketplace/listings")
            categories = client.get("/api/v1/marketplace/categories")
            detail = client.get("/api/v1/marketplace/listings/github-actions-checkout")
    finally:
        app.dependency_overrides.clear()

    assert listings.status_code == 200
    assert categories.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["use_url"] == "https://github.com/marketplace/actions/checkout"
    assert any(row["label"] == "SDK Extensions" for row in categories.json())
