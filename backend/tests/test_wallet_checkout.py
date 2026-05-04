import asyncio
import os
from types import SimpleNamespace

import stripe

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_wallet_checkout.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough")
os.environ.setdefault("LICENSE_ADMIN_TOKEN", "test-license-admin-token")

from apps.api.routers import token_wallet
from apps.api.routers.token_wallet import CreateCheckoutRequest, create_topup_checkout


def test_topup_checkout_preserves_existing_success_query(monkeypatch):
    captured = {}

    def fake_checkout_session_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/topup", id="cs_test_topup")

    monkeypatch.setattr(token_wallet.settings, "stripe_secret_key", "sk_test_wallet")
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_checkout_session_create)

    result = asyncio.run(
        create_topup_checkout(
            request=CreateCheckoutRequest(
                pack_name="starter",
                success_url="https://veklom.com/workspace-app#/billing?topup=success",
                cancel_url="https://veklom.com/workspace-app#/billing?topup=cancel",
            ),
            current_user=SimpleNamespace(workspace_id="workspace-1", email="buyer@example.com"),
            db=SimpleNamespace(),
        )
    )

    assert result.checkout_url == "https://checkout.stripe.test/topup"
    assert result.session_id == "cs_test_topup"
    assert (
        captured["success_url"]
        == "https://veklom.com/workspace-app#/billing?topup=success&session_id={CHECKOUT_SESSION_ID}"
    )
    assert captured["cancel_url"] == "https://veklom.com/workspace-app#/billing?topup=cancel"
    assert captured["metadata"]["workspace_id"] == "workspace-1"
