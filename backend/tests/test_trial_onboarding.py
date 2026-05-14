from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from core.services import trial_onboarding


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls: list[str] = []
        self.__class__.last_instance = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json: dict, headers: dict):
        self.calls.append(url)
        if url == "https://license.veklom.com/api/licenses/issue":
            return _FakeResponse(502)
        return _FakeResponse(
            200,
            {
                "license_id": "lic-123",
                "license_key": "vlk_test_123",
                "key_prefix": "vlk_test_",
                "workspace_id": json["workspace_id"],
                "tier": json["tier"],
                "expires_at": "2026-05-14T00:00:00+00:00",
            },
        )


class _FakeDB:
    def __init__(self):
        self.flushed = False

    def flush(self):
        self.flushed = True


def test_issue_trial_license_falls_back_to_backup_url(monkeypatch):
    monkeypatch.setattr(trial_onboarding.settings, "license_issue_url", "https://license.veklom.com/api/licenses/issue")
    monkeypatch.setattr(trial_onboarding.settings, "license_issue_backup_url", "https://license2.veklom.com/api/licenses/issue")
    monkeypatch.setattr(trial_onboarding.settings, "license_admin_token", "token")
    monkeypatch.setattr(trial_onboarding.settings, "buyer_download_base_url", "")
    monkeypatch.setattr(trial_onboarding.settings, "buyer_download_version", "1.0.0")
    monkeypatch.setattr(trial_onboarding.settings, "app_version", "1.0.0")
    monkeypatch.setattr(trial_onboarding.httpx, "AsyncClient", _FakeClient)

    workspace = SimpleNamespace(
        id="workspace-1",
        name="Acme",
        license_key_id=None,
        license_key_prefix=None,
        license_tier=None,
        license_issued_at=None,
        license_expires_at=None,
        license_download_url=None,
    )

    payload = asyncio.run(
        trial_onboarding.issue_trial_license(
            db=_FakeDB(),
            workspace=workspace,
            user_email="buyer@example.com",
            user_name="Buyer",
            requested_tier="starter",
        )
    )

    assert payload.license_id == "lic-123"
    assert payload.tier == "starter"
    assert _FakeClient.last_instance.calls == [
        "https://license.veklom.com/api/licenses/issue",
        "https://license2.veklom.com/api/licenses/issue",
    ]
    assert workspace.license_key_id == "lic-123"
    assert workspace.license_tier == "starter"
    assert workspace.license_download_url.endswith("veklom-backend-starter-1.0.0.zip")
    assert workspace.license_expires_at.replace(tzinfo=timezone.utc).isoformat().startswith("2026-05-14")
