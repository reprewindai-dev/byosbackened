from types import SimpleNamespace
from datetime import datetime, timedelta

from apps.api.middleware.entitlement_check import EntitlementCheckMiddleware
import apps.api.middleware.entitlement_check as entitlement_check
from db.models.subscription import SubscriptionStatus


class _FakeQuery:
    def __init__(self, db, model):
        self._db = db
        self._model = model

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        if self._model.__name__ == "Subscription":
            return self._db.subscription
        if self._model.__name__ == "Workspace":
            return self._db.workspace
        return None


class _FakeDB:
    def __init__(self, subscription=None, workspace=None):
        self.subscription = subscription
        self.workspace = workspace

    def query(self, model):
        return _FakeQuery(self, model)

    def close(self):
        return None


def test_admin_and_owner_are_treated_as_enterprise():
    middleware = EntitlementCheckMiddleware(app=SimpleNamespace())

    admin_request = SimpleNamespace(state=SimpleNamespace(is_superuser=False, role="admin"))
    owner_request = SimpleNamespace(state=SimpleNamespace(is_superuser=False, role="owner"))
    superuser_request = SimpleNamespace(state=SimpleNamespace(is_superuser=True, role="user"))

    assert middleware._resolve_current_plan(admin_request, "workspace-1") == "enterprise"
    assert middleware._resolve_current_plan(owner_request, "workspace-1") == "enterprise"
    assert middleware._resolve_current_plan(superuser_request, "workspace-1") == "enterprise"


def test_active_trial_license_unlocks_the_trial_tier(monkeypatch):
    workspace = SimpleNamespace(
        license_tier="sovereign",
        license_expires_at=datetime.utcnow() + timedelta(days=1),
    )
    fake_db = _FakeDB(subscription=None, workspace=workspace)
    fake_redis = SimpleNamespace(get=lambda key: None, setex=lambda *args, **kwargs: None)

    monkeypatch.setattr(entitlement_check, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(entitlement_check, "get_redis", lambda: fake_redis)

    middleware = EntitlementCheckMiddleware(app=SimpleNamespace())
    request = SimpleNamespace(state=SimpleNamespace(is_superuser=False, role="user"))

    assert middleware._resolve_current_plan(request, "workspace-1") == "sovereign"
