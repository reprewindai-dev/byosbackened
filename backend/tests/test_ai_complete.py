from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from apps.api.routers.ai import AICompleteRequest, _call_runtime_model, complete
from db.models import AIAuditLog, Subscription, TokenTransaction, TokenWallet


class _FakeQuery:
    def __init__(self, db, model):
        self._db = db
        self._model = model

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def with_for_update(self):
        return self

    def first(self):
        if self._model is TokenWallet:
            return self._db.wallet
        if self._model is AIAuditLog:
            return self._db.previous_audit
        if self._model is Subscription:
            return self._db.subscription
        return None

    def all(self):
        if self._model is TokenTransaction:
            return self._db.transactions
        return []


class _FakeDB:
    def __init__(self, wallet=None, previous_audit=None, subscription=None, transactions=None):
        self.wallet = wallet
        self.previous_audit = previous_audit
        self.subscription = subscription
        self.transactions = transactions or []
        self.added = []
        self.committed = False
        self.rolled_back = False

    def query(self, model):
        return _FakeQuery(self, model)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class _RuntimeCall:
    def __init__(self, output_text="hello from ollama", output_tokens=151):
        self.output_text = output_text
        self.output_tokens = output_tokens
        self.called = False

    def __call__(self, model_row, payload):
        self.called = True
        return {
            "response": self.output_text,
            "completion_tokens": self.output_tokens,
            "prompt_tokens": 17,
        }, model_row.provider, "primary_runtime"


def _model_row():
    return SimpleNamespace(
        model_slug="ollama-default",
        display_name="qwen2.5:1.5b (Ollama)",
        bedrock_model_id="qwen2.5:1.5b",
        provider="ollama",
        enabled=True,
        connected=True,
    )


class _FakeOpenAIResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "model": "gpt-4o-mini-2024-07-18",
            "choices": [{"message": {"content": "openai governed response"}}],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            },
        }


class _FakeOpenAIClient:
    posted = None

    def __init__(self, timeout=None):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers=None, json=None):
        self.__class__.posted = {"url": url, "headers": headers, "json": json}
        return _FakeOpenAIResponse()


def test_complete_deducts_wallet_and_logs_call(monkeypatch):
    wallet = SimpleNamespace(
        id="wallet-1",
        workspace_id="workspace-1",
        balance=1000,
        monthly_credits_used=0,
        total_credits_used=0,
        updated_at=None,
    )
    subscription = SimpleNamespace(plan=SimpleNamespace(value="starter"))
    fake_db = _FakeDB(wallet=wallet, subscription=subscription)
    runtime = _RuntimeCall(output_text="response text", output_tokens=151)
    monkeypatch.setattr("apps.api.routers.ai.get_model_setting", lambda db, workspace_id, model: _model_row())
    monkeypatch.setattr("apps.api.routers.ai._call_runtime_model", runtime)

    current_user = SimpleNamespace(id="user-1", workspace_id="workspace-1")
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-1"))
    payload = AICompleteRequest(model="ollama-default", prompt="Summarize the contract", max_tokens=512)

    result = asyncio.run(complete(payload=payload, request=request, current_user=current_user, db=fake_db))

    assert runtime.called is True
    assert result.response_text == "response text"
    assert result.provider == "ollama"
    assert result.request_id == "req-1"
    assert result.audit_hash
    assert result.prompt_tokens == 17
    assert result.output_tokens == 151
    assert result.total_tokens == 168
    assert result.cost_usd == "0.250000"
    assert result.tokens_deducted == 250
    assert result.reserve_debited == 250
    assert result.billing_event_type == "governed_run"
    assert result.pricing_tier == "founding"
    assert result.wallet_balance == 750
    assert wallet.balance == 750
    assert wallet.monthly_credits_used == 250
    assert wallet.total_credits_used == 250
    assert fake_db.committed is True
    assert any(obj.__class__.__name__ == "TokenTransaction" for obj in fake_db.added)
    assert any(obj.__class__.__name__ == "AIAuditLog" for obj in fake_db.added)


def test_call_runtime_model_executes_openai_through_governed_provider(monkeypatch):
    _FakeOpenAIClient.posted = None
    monkeypatch.setattr("apps.api.routers.ai.httpx.Client", _FakeOpenAIClient)
    monkeypatch.setattr(
        "apps.api.routers.ai.settings",
        SimpleNamespace(
            openai_api_key="configured",
            openai_base_url="https://api.openai.com/v1",
            llm_timeout_seconds=60,
        ),
    )
    model_row = SimpleNamespace(
        model_slug="openai-chat",
        bedrock_model_id="gpt-4o-mini",
        provider="openai",
        workspace_id="workspace-1",
    )
    payload = AICompleteRequest(
        model="openai-chat",
        prompt="Return JSON",
        system_prompt="Follow policy",
        max_tokens=64,
        response_format="json",
        temperature=0.2,
    )

    result, provider, routing_reason = _call_runtime_model(model_row, payload)

    assert provider == "openai"
    assert routing_reason == "primary_runtime"
    assert result["response"] == "openai governed response"
    assert result["model"] == "gpt-4o-mini-2024-07-18"
    assert result["prompt_tokens"] == 11
    assert result["completion_tokens"] == 7
    assert _FakeOpenAIClient.posted["url"] == "https://api.openai.com/v1/chat/completions"
    assert _FakeOpenAIClient.posted["headers"]["Authorization"].startswith("Bearer ")
    assert _FakeOpenAIClient.posted["json"]["model"] == "gpt-4o-mini"
    assert _FakeOpenAIClient.posted["json"]["response_format"] == {"type": "json_object"}


def test_call_runtime_model_executes_gemini_through_modelfarm_provider(monkeypatch):
    _FakeOpenAIClient.posted = None
    monkeypatch.setattr("apps.api.routers.ai.httpx.Client", _FakeOpenAIClient)
    monkeypatch.setattr(
        "apps.api.routers.ai.settings",
        SimpleNamespace(
            gemini_api_key="configured",
            gemini_base_url="http://localhost:1106/modelfarm/gemini",
            llm_timeout_seconds=60,
        ),
    )
    model_row = SimpleNamespace(
        model_slug="gemini-chat",
        bedrock_model_id="gemini-2.5-pro",
        provider="gemini",
        workspace_id="workspace-1",
    )
    payload = AICompleteRequest(
        model="gemini-chat",
        prompt="Return a governed answer",
        system_prompt="Follow policy",
        max_tokens=64,
        temperature=0.2,
    )

    result, provider, routing_reason = _call_runtime_model(model_row, payload)

    assert provider == "gemini"
    assert routing_reason == "primary_runtime"
    assert result["response"] == "openai governed response"
    assert _FakeOpenAIClient.posted["url"] == "http://localhost:1106/modelfarm/gemini/chat/completions"
    assert _FakeOpenAIClient.posted["headers"]["Authorization"].startswith("Bearer ")
    assert _FakeOpenAIClient.posted["json"]["model"] == "gemini-2.5-pro"


def test_call_runtime_model_falls_back_after_ollama_timeout(monkeypatch):
    class _ColdStartOllama:
        attempts = []

        def __init__(self, model=None, timeout=None, **kwargs):
            self.model = model
            self.timeout = timeout

        def generate(self, prompt, model=None, options=None):
            self.__class__.attempts.append(self.timeout)
            raise ai_module.OllamaError("Ollama request failed: timed out")

    import apps.api.routers.ai as ai_module

    monkeypatch.setattr(ai_module, "_shared_ollama_client", lambda **kwargs: _ColdStartOllama(**kwargs))
    monkeypatch.setattr(ai_module, "is_open", lambda scope: False)
    monkeypatch.setattr(ai_module, "record_success", lambda scope: None)
    monkeypatch.setattr(ai_module, "record_failure", lambda scope: "closed")
    monkeypatch.setattr(
        ai_module,
        "call_groq",
        lambda **kwargs: {
            "response": "groq fallback",
            "model": "llama-3.1-8b-instant",
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
        },
    )
    monkeypatch.setattr(
        ai_module,
        "settings",
        SimpleNamespace(
            llm_timeout_seconds=60,
            llm_on_prem_timeout_seconds=20,
            llm_fallback="groq",
            groq_api_key="test-key",
            groq_timeout_seconds=10,
        ),
    )
    model_row = SimpleNamespace(
        model_slug="ollama-default",
        bedrock_model_id="qwen2.5:3b",
        provider="ollama",
        workspace_id="workspace-1",
    )
    payload = AICompleteRequest(model="ollama-default", prompt="reply with healthy", max_tokens=16)

    result, provider, routing_reason = _call_runtime_model(model_row, payload)

    assert provider == "groq"
    assert routing_reason == "ollama_latency_budget_exceeded"
    assert result["response"] == "groq fallback"
    assert _ColdStartOllama.attempts == [20]


def test_complete_rejects_when_wallet_is_too_small(monkeypatch):
    wallet = SimpleNamespace(
        id="wallet-1",
        workspace_id="workspace-1",
        balance=100,
        monthly_credits_used=0,
        total_credits_used=0,
        updated_at=None,
    )
    subscription = SimpleNamespace(plan=SimpleNamespace(value="starter"))
    fake_db = _FakeDB(wallet=wallet, subscription=subscription)
    runtime = _RuntimeCall()
    monkeypatch.setattr("apps.api.routers.ai.get_model_setting", lambda db, workspace_id, model: _model_row())
    monkeypatch.setattr("apps.api.routers.ai._call_runtime_model", runtime)
    current_user = SimpleNamespace(id="user-1", workspace_id="workspace-1")
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-1"))
    payload = AICompleteRequest(model="ollama-default", prompt="Write a line", max_tokens=512)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(complete(payload=payload, request=request, current_user=current_user, db=fake_db))

    assert exc.value.status_code == 402
    assert exc.value.detail == "Insufficient operating reserve"
    assert runtime.called is False
    assert fake_db.committed is False


def test_complete_records_free_evaluation_run_without_debit(monkeypatch):
    wallet = SimpleNamespace(
        id="wallet-1",
        workspace_id="workspace-1",
        balance=50000,
        monthly_credits_used=0,
        total_credits_used=0,
        updated_at=None,
    )
    fake_db = _FakeDB(wallet=wallet, transactions=[])
    runtime = _RuntimeCall(output_text="free evaluation response", output_tokens=42)
    monkeypatch.setattr("apps.api.routers.ai.get_model_setting", lambda db, workspace_id, model: _model_row())
    monkeypatch.setattr("apps.api.routers.ai._call_runtime_model", runtime)

    current_user = SimpleNamespace(id="user-1", workspace_id="workspace-1")
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-free"))
    payload = AICompleteRequest(model="ollama-default", prompt="Run evaluation", max_tokens=512)

    result = asyncio.run(complete(payload=payload, request=request, current_user=current_user, db=fake_db))

    assert runtime.called is True
    assert result.pricing_tier == "free_evaluation"
    assert result.billing_event_type == "governed_run"
    assert result.reserve_debited == 0
    assert result.tokens_deducted == 0
    assert result.free_evaluation_remaining == 14
    assert result.wallet_balance == 50000
    assert wallet.balance == 50000
    assert any(obj.__class__.__name__ == "TokenTransaction" and obj.amount == 0 for obj in fake_db.added)


def test_complete_debits_compare_run_price(monkeypatch):
    wallet = SimpleNamespace(
        id="wallet-1",
        workspace_id="workspace-1",
        balance=1000,
        monthly_credits_used=0,
        total_credits_used=0,
        updated_at=None,
    )
    subscription = SimpleNamespace(plan=SimpleNamespace(value="starter"))
    fake_db = _FakeDB(wallet=wallet, subscription=subscription)
    runtime = _RuntimeCall(output_text="compare response", output_tokens=64)
    monkeypatch.setattr("apps.api.routers.ai.get_model_setting", lambda db, workspace_id, model: _model_row())
    monkeypatch.setattr("apps.api.routers.ai._call_runtime_model", runtime)

    current_user = SimpleNamespace(id="user-1", workspace_id="workspace-1")
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-compare"))
    payload = AICompleteRequest(
        model="ollama-default",
        prompt="Compare this answer",
        max_tokens=512,
        billing_event_type="compare_run",
    )

    result = asyncio.run(complete(payload=payload, request=request, current_user=current_user, db=fake_db))

    assert result.billing_event_type == "compare_run"
    assert result.reserve_debited == 750
    assert result.cost_usd == "0.750000"
    assert result.wallet_balance == 250
    assert wallet.balance == 250


def test_complete_rejects_unknown_model_slug(monkeypatch):
    fake_db = _FakeDB(wallet=None)
    monkeypatch.setattr(
        "apps.api.routers.ai.get_model_setting",
        lambda db, workspace_id, model: (_ for _ in ()).throw(ValueError("Unknown model slug: bad-model")),
    )

    current_user = SimpleNamespace(id="user-1", workspace_id="workspace-1")
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-1"))
    payload = AICompleteRequest(model="bad-model", prompt="Write a line", max_tokens=16)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(complete(payload=payload, request=request, current_user=current_user, db=fake_db))

    assert exc.value.status_code == 404
    assert "Unknown model slug" in exc.value.detail
