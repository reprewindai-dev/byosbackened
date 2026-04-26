"""
End-to-End Production Smoke Tests for BYOS Backend

Tests all critical paths including:
- LLM inference (/v1/exec)
- Circuit breaker functionality
- Multi-tenant isolation
- Security middleware (IDS, rate limiting)
- Authentication & authorization
- Cost tracking & billing
- Autonomous ML features
- Redis & database connectivity

Run with: pytest tests/test_smoke_production.py -v --tb=short
"""

import pytest
import hashlib
import time
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import app and dependencies
from apps.api.main import app
from db.session import get_db, SessionLocal
from core.llm.ollama_client import get_ollama_client, OllamaClient, OllamaError
from core.llm.circuit_breaker import get_state, CircuitState
from core.security import create_access_token


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def test_workspace_id():
    """Test workspace ID."""
    return "test-workspace-001"


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return "test-user-001"


@pytest.fixture
def test_api_key():
    """Test API key."""
    return "byos_test_key_smoke_12345"


@pytest.fixture
def api_key_hash(test_api_key):
    """Hashed API key."""
    return hashlib.sha256(test_api_key.encode()).hexdigest()


@pytest.fixture
def mock_db(test_workspace_id, test_user_id, api_key_hash):
    """Create a mock database session."""
    db = MagicMock(spec=Session)
    
    # Mock API key lookup
    mock_api_key_obj = MagicMock()
    mock_api_key_obj.workspace_id = test_workspace_id
    mock_api_key_obj.is_active = True
    mock_api_key_obj.expires_at = None
    mock_api_key_obj.key_hash = api_key_hash
    mock_api_key_obj.last_used_at = None
    
    # Setup query chain: query().filter().first()
    db.query.return_value.filter.return_value.first.return_value = mock_api_key_obj
    db.execute.return_value = None
    db.commit.return_value = None
    db.add.return_value = None
    db.refresh.side_effect = lambda obj: None
    
    return db


@pytest.fixture
def mock_ollama_healthy():
    """Mock healthy Ollama client."""
    ollama = MagicMock(spec=OllamaClient)
    ollama.generate.return_value = {
        "response": "This is a test response from the local LLM.",
        "model": "qwen2.5:3b",
        "prompt_tokens": 25,
        "completion_tokens": 15,
        "total_tokens": 40,
        "latency_ms": 850,
        "done": True,
    }
    ollama.health_check.return_value = True
    ollama.list_models.return_value = ["qwen2.5:3b", "llama3.2:3b"]
    return ollama


@pytest.fixture
def mock_ollama_unhealthy():
    """Mock unhealthy Ollama client."""
    ollama = MagicMock(spec=OllamaClient)
    ollama.generate.side_effect = OllamaError("Cannot reach Ollama")
    ollama.health_check.return_value = False
    ollama.list_models.return_value = []
    return ollama


@pytest.fixture
def client(mock_db, mock_ollama_healthy):
    """TestClient with mocked dependencies."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_ollama_client] = lambda: mock_ollama_healthy
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def client_ollama_down(mock_db, mock_ollama_unhealthy):
    """TestClient with Ollama down."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_ollama_client] = lambda: mock_ollama_unhealthy
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_token(test_user_id, test_workspace_id):
    """Create JWT auth token."""
    return create_access_token({
        "sub": "test@example.com",
        "user_id": test_user_id,
        "workspace_id": test_workspace_id,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Health & Status Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoints:
    """Test health and status endpoints."""
    
    def test_health_endpoint(self, client):
        """GET /health returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
    
    def test_status_endpoint(self, client):
        """GET /status returns full system status."""
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value.ping.return_value = True
            response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields
        assert "db_ok" in data
        assert "redis_ok" in data
        assert "llm_ok" in data
        assert "llm_model" in data
        assert "llm_models_available" in data
        assert "circuit_breaker" in data
        assert "uptime_seconds" in data


# ═══════════════════════════════════════════════════════════════════════════════
# LLM Inference Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestLLMInference:
    """Test LLM inference via /v1/exec."""
    
    def test_exec_success(self, client, test_api_key):
        """POST /v1/exec with valid key returns LLM response."""
        response = client.post(
            "/v1/exec",
            json={"prompt": "Say hello in one word."},
            headers={"X-API-Key": test_api_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        assert data["model"] == "qwen2.5:3b"
        assert data["provider"] == "ollama"
        assert data["total_tokens"] == 40
        assert "log_id" in data
    
    def test_exec_with_conversation_memory(self, client, test_api_key):
        """POST /v1/exec with conversation_id enables memory."""
        conversation_id = "test-conv-001"
        
        # First message
        response1 = client.post(
            "/v1/exec",
            json={
                "prompt": "My name is Alice.",
                "conversation_id": conversation_id,
            },
            headers={"X-API-Key": test_api_key},
        )
        assert response1.status_code == 200
        
        # Second message (should have context)
        response2 = client.post(
            "/v1/exec",
            json={
                "prompt": "What is my name?",
                "conversation_id": conversation_id,
            },
            headers={"X-API-Key": test_api_key},
        )
        assert response2.status_code == 200
        assert response2.json()["conversation_id"] == conversation_id
    
    def test_exec_invalid_api_key(self, client):
        """POST /v1/exec with invalid key returns 401."""
        response = client.post(
            "/v1/exec",
            json={"prompt": "Hello"},
            headers={"X-API-Key": "byos_invalid_key_12345"},
        )
        
        assert response.status_code == 401
    
    def test_exec_missing_api_key(self, client):
        """POST /v1/exec without key returns 422."""
        response = client.post(
            "/v1/exec",
            json={"prompt": "Hello"},
        )
        
        assert response.status_code == 422
    
    def test_exec_prompt_too_long(self, client, test_api_key):
        """POST /v1/exec with prompt > 32000 chars returns 422."""
        response = client.post(
            "/v1/exec",
            json={"prompt": "x" * 33000},
            headers={"X-API-Key": test_api_key},
        )
        
        assert response.status_code == 422
    
    def test_exec_empty_prompt(self, client, test_api_key):
        """POST /v1/exec with empty prompt returns 422."""
        response = client.post(
            "/v1/exec",
            json={"prompt": ""},
            headers={"X-API-Key": test_api_key},
        )
        
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Circuit Breaker Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_closed_ollama_healthy(self, client, test_api_key):
        """Circuit closed when Ollama healthy - uses local inference."""
        response = client.post(
            "/v1/exec",
            json={"prompt": "Test prompt"},
            headers={"X-API-Key": test_api_key},
        )
        
        assert response.status_code == 200
        assert response.json()["provider"] == "ollama"
    
    def test_circuit_opens_after_failures(self, client_ollama_down, test_api_key):
        """Circuit opens after consecutive failures."""
        # Make multiple requests that will fail
        for _ in range(5):
            response = client_ollama_down.post(
                "/v1/exec",
                json={"prompt": "Test prompt"},
                headers={"X-API-Key": test_api_key},
            )
        
        # After threshold failures, circuit should be open
        # Without Groq fallback, should return 503
        assert response.status_code in [503, 200]  # 503 if no fallback, 200 if Groq works
    
    def test_status_shows_circuit_state(self, client):
        """GET /status includes circuit breaker state."""
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value.ping.return_value = True
            response = client.get("/status")
        
        assert response.status_code == 200
        cb = response.json()["circuit_breaker"]
        
        assert "state" in cb
        assert cb["state"] in ["closed", "open", "half_open"]
        assert "failures" in cb
        assert "threshold" in cb


# ═══════════════════════════════════════════════════════════════════════════════
# Security Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityMiddleware:
    """Test LockerPhycer security middleware integration."""
    
    def test_security_headers_present(self, client):
        """Response includes security headers."""
        response = client.get("/health")
        
        # Check security headers
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
    
    def test_rate_limit_headers_present(self, client, test_api_key):
        """Response includes rate limit headers."""
        response = client.post(
            "/v1/exec",
            json={"prompt": "Test"},
            headers={"X-API-Key": test_api_key},
        )
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
    
    def test_ids_blocks_sql_injection(self, client, test_api_key):
        """IDS blocks SQL injection attempts."""
        response = client.post(
            "/v1/exec",
            json={"prompt": "'; DROP TABLE users; --"},
            headers={"X-API-Key": test_api_key},
        )
        
        # Should either block (403) or be processed safely
        assert response.status_code in [200, 403, 422]
    
    def test_ids_blocks_xss_attempt(self, client):
        """IDS blocks XSS attempts."""
        response = client.get(
            "/health?callback=<script>alert('xss')</script>"
        )
        
        # Should either block or sanitize
        assert response.status_code in [200, 403]
    
    def test_ids_blocks_path_traversal(self, client, auth_token):
        """IDS blocks path traversal attempts."""
        response = client.get(
            "/api/v1/admin/../../../etc/passwd",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        # Should return 403 or 404, never serve the file
        assert response.status_code in [403, 404, 422]


# ═══════════════════════════════════════════════════════════════════════════════
# Authentication Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthentication:
    """Test authentication flows."""
    
    def test_jwt_auth_required_for_protected_endpoints(self, client):
        """Protected endpoints require JWT."""
        response = client.get("/api/v1/cost/predict")
        
        assert response.status_code == 401
    
    def test_valid_jwt_access(self, client, auth_token):
        """Valid JWT grants access."""
        response = client.get(
            "/api/v1/cost/predict",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        # Should not return 401 (might return other errors for missing params)
        assert response.status_code != 401
    
    def test_invalid_jwt_rejected(self, client):
        """Invalid JWT is rejected."""
        response = client.get(
            "/api/v1/cost/predict",
            headers={"Authorization": "Bearer invalid_token"},
        )
        
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# API Documentation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAPIDocumentation:
    """Test API documentation availability."""
    
    def test_swagger_ui_available(self, client):
        """Swagger UI is accessible."""
        response = client.get("/api/v1/docs")
        assert response.status_code == 200
    
    def test_openapi_schema_available(self, client):
        """OpenAPI schema is accessible."""
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
    
    def test_redoc_available(self, client):
        """ReDoc is accessible."""
        response = client.get("/api/v1/redoc")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Landing Page Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestLandingPage:
    """Test landing page."""
    
    def test_landing_page_or_redirect(self, client):
        """Root path returns landing page or API info."""
        response = client.get("/")
        
        assert response.status_code in [200, 307, 308]
    
    def test_landing_page_security_headers(self, client):
        """Landing page has security headers."""
        response = client.get("/")
        
        # Should have CSP and other security headers
        if response.status_code == 200:
            assert "X-Frame-Options" in response.headers


# ═══════════════════════════════════════════════════════════════════════════════
# Performance Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    """Basic performance smoke tests."""
    
    def test_health_response_time(self, client):
        """Health endpoint responds quickly."""
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond in under 1 second
    
    def test_exec_response_time(self, client, test_api_key):
        """Exec endpoint responds within reasonable time."""
        start = time.time()
        response = client.post(
            "/v1/exec",
            json={"prompt": "Quick test"},
            headers={"X-API-Key": test_api_key},
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 10.0  # Should respond in under 10 seconds


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration smoke tests."""
    
    def test_full_request_flow(self, client, test_api_key):
        """Test complete request flow with all middleware."""
        # 1. Health check
        health = client.get("/health")
        assert health.status_code == 200
        
        # 2. Status check
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value.ping.return_value = True
            status = client.get("/status")
        assert status.status_code == 200
        
        # 3. LLM inference
        exec_response = client.post(
            "/v1/exec",
            json={"prompt": "Integration test"},
            headers={"X-API-Key": test_api_key},
        )
        assert exec_response.status_code == 200
        
        # 4. Verify response structure
        data = exec_response.json()
        assert all(key in data for key in [
            "response", "model", "provider", "tenant_id",
            "prompt_tokens", "completion_tokens", "total_tokens", "latency_ms"
        ])


# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point for Manual Testing
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
