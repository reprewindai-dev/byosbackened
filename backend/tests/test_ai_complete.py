from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from apps.api.routers.ai import AICompleteRequest, complete
from db.models import AIAuditLog, TokenWallet


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
        return None


class _FakeDB:
    def __init__(self, wallet=None, previous_audit=None):
        self.wallet = wallet
        self.previous_audit = previous_audit
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

    def __call__(self, model_row, prompt, max_tokens):
        self.called = True
        return {
            "response": self.output_text,
            "completion_tokens": self.output_tokens,
            "prompt_tokens": 17,
        }, model_row.provider


def _model_row():
    return SimpleNamespace(
        model_slug="ollama-default",
        display_name="qwen2.5:1.5b (Ollama)",
        bedrock_model_id="qwen2.5:1.5b",
        provider="ollama",
        enabled=True,
        connected=True,
    )


def test_complete_deducts_wallet_and_logs_call(monkeypatch):
    wallet = SimpleNamespace(
        id="wallet-1",
        workspace_id="workspace-1",
        balance=10,
        monthly_credits_used=0,
        total_credits_used=0,
        updated_at=None,
    )
    fake_db = _FakeDB(wallet=wallet)
    runtime = _RuntimeCall(output_text="response text", output_tokens=151)
    monkeypatch.setattr("apps.api.routers.ai.get_model_setting", lambda db, workspace_id, model: _model_row())
    monkeypatch.setattr("apps.api.routers.ai._call_runtime_model", runtime)

    current_user = SimpleNamespace(id="user-1", workspace_id="workspace-1")
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-1"))
    payload = AICompleteRequest(model="ollama-default", prompt="Summarize the contract", max_tokens=512)

    result = asyncio.run(complete(payload=payload, request=request, current_user=current_user, db=fake_db))

    assert runtime.called is True
    assert result.response_text == "response text"
    assert result.tokens_deducted == 2
    assert result.wallet_balance == 8
    assert wallet.balance == 8
    assert wallet.monthly_credits_used == 2
    assert wallet.total_credits_used == 2
    assert fake_db.committed is True
    assert any(obj.__class__.__name__ == "TokenTransaction" for obj in fake_db.added)
    assert any(obj.__class__.__name__ == "AIAuditLog" for obj in fake_db.added)


def test_complete_rejects_when_wallet_is_too_small(monkeypatch):
    wallet = SimpleNamespace(
        id="wallet-1",
        workspace_id="workspace-1",
        balance=1,
        monthly_credits_used=0,
        total_credits_used=0,
        updated_at=None,
    )
    fake_db = _FakeDB(wallet=wallet)
    runtime = _RuntimeCall()
    monkeypatch.setattr("apps.api.routers.ai.get_model_setting", lambda db, workspace_id, model: _model_row())
    monkeypatch.setattr("apps.api.routers.ai._call_runtime_model", runtime)
    current_user = SimpleNamespace(id="user-1", workspace_id="workspace-1")
    request = SimpleNamespace(state=SimpleNamespace(request_id="req-1"))
    payload = AICompleteRequest(model="ollama-default", prompt="Write a line", max_tokens=512)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(complete(payload=payload, request=request, current_user=current_user, db=fake_db))

    assert exc.value.status_code == 402
    assert exc.value.detail == "Insufficient tokens"
    assert runtime.called is False
    assert fake_db.committed is False
