import os
from uuid import uuid4

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_github_oauth_wallet.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough")
os.environ.setdefault("LICENSE_ADMIN_TOKEN", "test-license-admin-token")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-github-client-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-github-client-secret")
os.environ.setdefault("GITHUB_REDIRECT_URI", "https://veklom.com/auth/github/callback")

try:
    os.remove("test_github_oauth_wallet.db")
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers.auth import FREE_TRIAL_CREDITS, _build_github_state

GITHUB_TEST_ID = int(uuid4().int % 1_000_000_000)
GITHUB_TEST_EMAIL = f"github-wallet-{uuid4().hex}@example.com"


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, headers=None):
        return _FakeResponse(200, {"access_token": "gh_test_token"})

    async def get(self, url, headers=None, params=None):
        if url.endswith("/user"):
            return _FakeResponse(
                200,
                {
                    "id": 123456,
                    "login": "reprewindai-dev",
                    "name": "Anthony Veklom",
                    "email": GITHUB_TEST_EMAIL,
                },
            )
        if url.endswith("/user/emails"):
            return _FakeResponse(200, [])
        if url.endswith("/user/repos"):
            return _FakeResponse(200, [])
        return _FakeResponse(404, {})


def test_github_oauth_new_user_gets_workspace_tokens_and_trial_wallet(monkeypatch):
    monkeypatch.setattr("apps.api.routers.auth.httpx.AsyncClient", _FakeAsyncClient)

    with TestClient(app) as client:
        state = _build_github_state()
        callback = client.post(
            "/api/v1/auth/github/callback",
            json={"code": "gh_code", "state": state},
        )

        assert callback.status_code == 200
        payload = callback.json()
        assert payload["is_new_user"] is True
        assert payload["access_token"]
        assert payload["workspace_id"]

        headers = {"Authorization": f"Bearer {payload['access_token']}"}
        me = client.get("/api/v1/auth/me", headers=headers)
        wallet = client.get("/api/v1/wallet/balance", headers=headers)

    assert me.status_code == 200
    assert me.json()["email"] == GITHUB_TEST_EMAIL
    assert me.json()["workspace_name"] == "reprewindai-dev"
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == FREE_TRIAL_CREDITS
