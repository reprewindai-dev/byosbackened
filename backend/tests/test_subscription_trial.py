from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

from apps.api.routers.subscriptions import current_subscription


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


def test_current_subscription_returns_trial_license_as_effective_plan():
    fake_db = _FakeDB(
        subscription=None,
        workspace=SimpleNamespace(
            license_tier="sovereign",
            license_expires_at=datetime.utcnow() + timedelta(days=14),
        ),
    )
    current_user = SimpleNamespace(workspace_id="workspace-1")

    result = asyncio.run(current_subscription(current_user=current_user, db=fake_db))

    assert result.plan == "sovereign"
    assert result.status == "trialing"
    assert result.amount_cents == 0
    assert result.trial_end is not None
