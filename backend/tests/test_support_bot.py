import asyncio
import os

from fastapi.testclient import TestClient

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_support_bot.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-tests")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough")
os.environ.setdefault("LICENSE_ADMIN_TOKEN", "test-license-admin-token")

from apps.api.main import app
from apps.api.routers import support_bot


class _Memory:
    async def get_messages(self, *args, **kwargs):
        return []

    async def add_message(self, *args, **kwargs):
        return None


def test_support_chat_returns_fallback_when_llm_times_out(monkeypatch):
    import core.llm
    import core.memory

    support_bot._rate_limit.clear()
    monkeypatch.setattr(support_bot, "SUPPORT_LLM_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(core.llm, "is_open", lambda: True)
    monkeypatch.setattr(core.memory, "get_memory", lambda *args, **kwargs: _Memory())

    async def slow_groq(*args, **kwargs):
        await asyncio.sleep(1)
        return "late response"

    monkeypatch.setattr(core.llm, "call_groq", slow_groq)

    with TestClient(app) as client:
        response = client.post("/api/v1/support/chat", json={"message": "pricing"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"].startswith("sup_")
    assert "operating reserve" in payload["response"]
