"""
Integration tests for /v1/exec and /status endpoints.

Run with:
    pytest tests/test_exec_endpoints.py -v

These tests use FastAPI's TestClient with mocked DB + Ollama to avoid
requiring a live Postgres or Ollama during CI.
"""
import hashlib
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

RAW_KEY = "byos_test_key_abc123_dev"
KEY_HASH = hashlib.sha256(RAW_KEY.encode()).hexdigest()


def _mock_api_key():
    k = MagicMock()
    k.workspace_id = "workspace-test-001"
    k.is_active = True
    k.expires_at = None
    k.key_hash = KEY_HASH
    k.last_used_at = None
    return k


def _mock_db():
    db = MagicMock()
    # query().filter().first() returns the mock API key
    db.query.return_value.filter.return_value.first.return_value = _mock_api_key()
    db.execute.return_value = None
    db.commit.return_value = None
    db.add.return_value = None
    db.refresh.side_effect = lambda obj: None
    return db


def _mock_ollama_ok():
    ollama = MagicMock()
    ollama.generate.return_value = {
        "response": "Hello! I am a local Ollama model.",
        "model": "llama3.2:1b",
        "prompt_tokens": 10,
        "completion_tokens": 12,
        "total_tokens": 22,
        "latency_ms": 350,
        "done": True,
    }
    ollama.health_check.return_value = True
    ollama.list_models.return_value = ["llama3.2:1b", "llama3:latest"]
    return ollama


def _mock_ollama_down():
    from core.llm.ollama_client import OllamaError
    ollama = MagicMock()
    ollama.generate.side_effect = OllamaError("Cannot reach Ollama at http://host.docker.internal:11434")
    ollama.health_check.return_value = False
    ollama.list_models.return_value = []
    return ollama


@pytest.fixture
def client():
    """TestClient with all heavy dependencies patched."""
    from apps.api.main import app
    from db.session import get_db
    from core.llm.ollama_client import get_ollama_client

    def override_db():
        yield _mock_db()

    def override_ollama_ok():
        return _mock_ollama_ok()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_ollama_client] = override_ollama_ok
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_ollama_down():
    """TestClient with Ollama unavailable."""
    from apps.api.main import app
    from db.session import get_db
    from core.llm.ollama_client import get_ollama_client

    def override_db():
        yield _mock_db()

    def override_ollama_down():
        return _mock_ollama_down()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_ollama_client] = override_ollama_down
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_apikey():
    """TestClient where the DB returns no matching API key (401 scenario)."""
    from apps.api.main import app
    from db.session import get_db
    from core.llm.ollama_client import get_ollama_client

    def override_db_no_key():
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None  # not found
        yield db

    app.dependency_overrides[get_db] = override_db_no_key
    app.dependency_overrides[get_ollama_client] = _mock_ollama_ok
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── /status tests ─────────────────────────────────────────────────────────────

class TestStatusEndpoint:
    def test_status_ok(self, client):
        """GET /status returns 200 with all health fields."""
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value.ping.return_value = True
            resp = client.get("/status")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "db_ok" in data
        assert "redis_ok" in data
        assert "llm_ok" in data
        assert "llm_base_url" in data
        assert "llm_model" in data
        assert "llm_models_available" in data
        assert "uptime_seconds" in data

    def test_status_llm_down(self, client_ollama_down):
        """GET /status reports llm_ok=false when Ollama is unreachable."""
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value.ping.return_value = True
            resp = client_ollama_down.get("/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["llm_ok"] is False
        assert data["llm_models_available"] == []

    def test_status_no_auth_required(self, client):
        """GET /status must work without any auth header."""
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value.ping.return_value = True
            resp = client.get("/status")

        assert resp.status_code != 401


# ── /v1/exec tests ────────────────────────────────────────────────────────────

class TestExecEndpoint:
    def test_exec_success(self, client):
        """POST /v1/exec with valid API key returns LLM response."""
        resp = client.post(
            "/v1/exec",
            json={"prompt": "Say hello in one sentence."},
            headers={"X-API-Key": RAW_KEY},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["response"] == "Hello! I am a local Ollama model."
        assert data["model"] == "llama3.2:1b"
        assert data["tenant_id"] == "workspace-test-001"
        assert data["total_tokens"] == 22
        assert isinstance(data["latency_ms"], int)
        assert data["latency_ms"] >= 0
        assert "log_id" in data

    def test_exec_invalid_api_key(self, client_no_apikey):
        """POST /v1/exec with unknown key returns 401."""
        resp = client_no_apikey.post(
            "/v1/exec",
            json={"prompt": "Hello"},
            headers={"X-API-Key": "byos_invalid_key"},
        )
        assert resp.status_code == 401
        assert "Invalid API key" in resp.json()["detail"]

    def test_exec_missing_api_key(self, client):
        """POST /v1/exec without X-API-Key header returns 422."""
        resp = client.post(
            "/v1/exec",
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 422

    def test_exec_empty_prompt_rejected(self, client):
        """POST /v1/exec with empty prompt returns 422."""
        resp = client.post(
            "/v1/exec",
            json={"prompt": ""},
            headers={"X-API-Key": RAW_KEY},
        )
        assert resp.status_code == 422

    def test_exec_ollama_down_returns_503(self, client_ollama_down):
        """POST /v1/exec returns 503 when Ollama is unreachable."""
        resp = client_ollama_down.post(
            "/v1/exec",
            json={"prompt": "Hello"},
            headers={"X-API-Key": RAW_KEY},
        )
        assert resp.status_code == 503
        assert "LLM unavailable" in resp.json()["detail"]

    def test_exec_with_model_override(self, client):
        """POST /v1/exec accepts optional model field."""
        resp = client.post(
            "/v1/exec",
            json={"prompt": "Hello", "model": "llama3:latest"},
            headers={"X-API-Key": RAW_KEY},
        )
        assert resp.status_code == 200

    def test_exec_prompt_too_long_rejected(self, client):
        """POST /v1/exec with prompt > 32000 chars returns 422."""
        resp = client.post(
            "/v1/exec",
            json={"prompt": "x" * 33000},
            headers={"X-API-Key": RAW_KEY},
        )
        assert resp.status_code == 422

    def test_exec_no_auth_required_in_zero_trust(self, client):
        """/v1/exec is in public paths but uses its own X-API-Key auth."""
        resp = client.post(
            "/v1/exec",
            json={"prompt": "Hello"},
        )
        # Missing key → 422 (field required), not 401 from ZeroTrustMiddleware
        assert resp.status_code == 422
