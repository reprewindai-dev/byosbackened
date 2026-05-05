import os
from types import SimpleNamespace

from fastapi.testclient import TestClient

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_marketplace_public_access.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough")
os.environ.setdefault("LICENSE_ADMIN_TOKEN", "test-license-admin-token")

try:
    os.remove("test_marketplace_public_access.db")
except FileNotFoundError:
    pass

from apps.api.main import app
from apps.api.deps import get_current_user
from core.services.marketplace_catalog import real_marketplace_catalog
from core.security import create_access_token
from db.models import Listing, MarketplaceOrder, User, Vendor, Workspace
from db.session import Base, SessionLocal, engine
from db.session import get_db

Base.metadata.create_all(bind=engine)


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
    assert all(row.get("source_verified") is True for row in payload)
    assert all(row.get("rating_count", 0) == 0 for row in payload if row["id"] != "checkout-listing")
    assert all(row.get("install_count", 0) == 0 for row in payload if row["id"] != "checkout-listing")


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


def test_curated_marketplace_catalog_uses_live_official_sources():
    catalog = {row["id"]: row for row in real_marketplace_catalog()}
    slack = catalog["slack-send-github-action"]

    assert slack["source_url"] == "https://github.com/slackapi/slack-github-action"
    assert slack["use_url"] == "https://docs.slack.dev/tools/slack-github-action/"
    assert slack["usage"] == "uses: slackapi/slack-github-action@v3"
    assert "slack-send-to-slack" not in slack["source_url"]
    assert all(row["source_url"].startswith("https://") for row in catalog.values())
    assert all(row["source_verified"] is True for row in catalog.values())
    assert all(row["rating_count"] == 0 for row in catalog.values())
    assert all(row["install_count"] == 0 for row in catalog.values())


def _seed_paid_listing():
    db = SessionLocal()
    try:
        workspace = Workspace(id="checkout-ws", name="Checkout Workspace", slug="checkout-ws")
        user = User(
            id="checkout-user",
            email="buyer@example.com",
            hashed_password="not-used",
            workspace_id=workspace.id,
        )
        vendor_user = User(
            id="checkout-vendor-user",
            email="vendor@example.com",
            hashed_password="not-used",
            workspace_id=workspace.id,
        )
        vendor = Vendor(
            id="checkout-vendor",
            user_id=vendor_user.id,
            workspace_id=workspace.id,
            display_name="Checkout Vendor",
            plan="verified",
            subscription_status="active",
        )
        listing = Listing(
            id="checkout-listing",
            vendor_id=vendor.id,
            workspace_id=workspace.id,
            title="Paid Governance Pack",
            description="Paid marketplace pack for checkout wiring.",
            price_cents=4900,
            currency="usd",
            status="active",
        )
        db.add_all([workspace, user, vendor_user, vendor, listing])
        db.commit()
        return SimpleNamespace(id=user.id, workspace_id=user.workspace_id, email=user.email, role="user", is_superuser=False)
    finally:
        db.close()


def test_marketplace_checkout_accepts_listing_id_and_creates_order(monkeypatch):
    current_user = _seed_paid_listing()
    captured = {}

    def fake_checkout_session_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/session", id="cs_test_marketplace")

    monkeypatch.setattr("apps.api.routers.marketplace_v1.settings.stripe_secret_key", "sk_test_marketplace")
    monkeypatch.setattr(
        "apps.api.routers.marketplace_v1.stripe.checkout.Session.create",
        fake_checkout_session_create,
    )
    app.dependency_overrides[get_current_user] = lambda: current_user
    token = create_access_token(
        {"user_id": current_user.id, "workspace_id": current_user.workspace_id, "role": "user"}
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/marketplace/payments/create-checkout",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "listing_id": "checkout-listing",
                    "success_url": "https://veklom.com/workspace-app#/marketplace?checkout=success",
                    "cancel_url": "https://veklom.com/workspace-app#/marketplace?checkout=cancel",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["checkout_url"] == "https://checkout.stripe.test/session"
    assert payload["checkout_session_id"] == "cs_test_marketplace"
    assert payload["order_id"]
    assert captured["mode"] == "payment"
    assert captured["customer_email"] == "buyer@example.com"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 4900
    assert captured["metadata"]["order_id"] == payload["order_id"]

    db = SessionLocal()
    try:
        order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == payload["order_id"]).first()
        assert order is not None
        assert order.buyer_id == "checkout-user"
        assert order.workspace_id == "checkout-ws"
        assert order.total_cents == 4900
        assert order.items[0].listing_id == "checkout-listing"
    finally:
        db.close()


def test_marketplace_checkout_requires_order_or_listing_id(monkeypatch):
    monkeypatch.setattr("apps.api.routers.marketplace_v1.settings.stripe_secret_key", "sk_test_marketplace")
    token = create_access_token({"user_id": "checkout-user", "workspace_id": "checkout-ws", "role": "user"})
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="checkout-user",
        workspace_id="checkout-ws",
        email="buyer@example.com",
        role="user",
        is_superuser=False,
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/marketplace/payments/create-checkout",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "order_id or listing_id is required"
