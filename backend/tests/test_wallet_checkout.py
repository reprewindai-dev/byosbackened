import asyncio
import os
from types import SimpleNamespace

import stripe
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_wallet_checkout.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough")
os.environ.setdefault("LICENSE_ADMIN_TOKEN", "test-license-admin-token")

from apps.api.routers import token_wallet
from apps.api.routers.token_wallet import CreateCheckoutRequest, create_topup_checkout
from apps.api.routers import subscriptions
from apps.api.routers.subscriptions import CheckoutRequest, _apply_paid_checkout_session, create_checkout
from db.models import PlanTier, Subscription, SubscriptionStatus, TokenTransaction, TokenWallet


class _FakeQuery:
    def __init__(self, value):
        self.value = value

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.value


class _FakeDB:
    def __init__(self, subscription=None):
        self.subscription = subscription

    def query(self, model):
        if model is Subscription:
            return _FakeQuery(self.subscription)
        return _FakeQuery(None)


def test_topup_checkout_preserves_existing_success_query(monkeypatch):
    captured = {}

    def fake_checkout_session_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/topup", id="cs_test_topup")

    monkeypatch.setattr(token_wallet.settings, "stripe_secret_key", "unit-test-stripe-key")
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_checkout_session_create)

    result = asyncio.run(
        create_topup_checkout(
            request=CreateCheckoutRequest(
                pack_name="founding",
                success_url="https://veklom.com/workspace-app#/billing?topup=success",
                cancel_url="https://veklom.com/workspace-app#/billing?topup=cancel",
            ),
            current_user=SimpleNamespace(workspace_id="workspace-1", email="buyer@example.com"),
            db=_FakeDB(
                subscription=SimpleNamespace(
                    workspace_id="workspace-1",
                    status=SubscriptionStatus.ACTIVE,
                )
            ),
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


def test_topup_checkout_requires_paid_activation(monkeypatch):
    monkeypatch.setattr(token_wallet.settings, "stripe_secret_key", "unit-test-stripe-key")
    try:
        asyncio.run(
            create_topup_checkout(
                request=CreateCheckoutRequest(
                    pack_name="founding",
                    success_url="https://veklom.com/workspace-app#/billing",
                    cancel_url="https://veklom.com/workspace-app#/billing",
                ),
                current_user=SimpleNamespace(workspace_id="workspace-1", email="buyer@example.com"),
                db=_FakeDB(subscription=None),
            )
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 402
    else:
        raise AssertionError("Free Evaluation workspace should not be able to add reserve directly")


def test_activation_checkout_collects_minimum_reserve(monkeypatch):
    captured = {}
    sub = SimpleNamespace(stripe_customer_id="cus_existing")

    def fake_checkout_session_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/activate", id="cs_test_activate")

    monkeypatch.setattr(subscriptions.settings, "stripe_secret_key", "unit-test-stripe-key")
    monkeypatch.setattr(stripe.checkout.Session, "create", fake_checkout_session_create)

    result = asyncio.run(
        create_checkout(
            payload=CheckoutRequest(
                plan=PlanTier.STARTER,
                success_url="https://veklom.com/workspace-app#/billing",
                cancel_url="https://veklom.com/workspace-app#/billing",
            ),
            current_user=SimpleNamespace(workspace_id="workspace-1", email="buyer@example.com"),
            db=_FakeDB(subscription=sub),
        )
    )

    assert result.session_id == "cs_test_activate"
    price_data = captured["line_items"][0]["price_data"]
    assert price_data["unit_amount"] == 54_500
    assert captured["metadata"]["activation_cents"] == "39500"
    assert captured["metadata"]["minimum_reserve_cents"] == "15000"
    assert captured["metadata"]["reserve_units"] == "150000"


def test_paid_activation_credits_only_reserve_portion():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (Subscription.__table__, TokenWallet.__table__, TokenTransaction.__table__):
        table.create(engine, checkfirst=True)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    db.add(
        Subscription(
            workspace_id="workspace-1",
            plan=PlanTier.STARTER,
            status=SubscriptionStatus.INCOMPLETE,
            billing_cycle="activation",
        )
    )
    db.commit()

    applied = _apply_paid_checkout_session(
        db,
        {
            "id": "cs_paid_activation",
            "mode": "payment",
            "payment_status": "paid",
            "customer": "cus_paid",
            "payment_intent": "pi_paid",
            "metadata": {
                "type": "workspace_activation",
                "workspace_id": "workspace-1",
                "plan": "starter",
                "activation_cents": "39500",
                "minimum_reserve_cents": "15000",
                "reserve_units": "150000",
            },
        },
    )

    wallet = db.query(TokenWallet).filter(TokenWallet.workspace_id == "workspace-1").first()
    tx = db.query(TokenTransaction).filter(TokenTransaction.workspace_id == "workspace-1").first()
    sub = db.query(Subscription).filter(Subscription.workspace_id == "workspace-1").first()

    assert applied is True
    assert sub.status == SubscriptionStatus.ACTIVE
    assert wallet.balance == 150_000
    assert wallet.total_credits_purchased == 150_000
    assert tx.transaction_type == "purchase"
    assert tx.amount == 150_000
    assert tx.stripe_checkout_session_id == "cs_paid_activation"
