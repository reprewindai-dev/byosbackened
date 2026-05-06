from __future__ import annotations

from types import SimpleNamespace

from core.services import workspace_gateway


class _HealthyOllama:
    def health_check(self):
        return True


def _reset_bedrock_probe(monkeypatch):
    monkeypatch.setattr(workspace_gateway, "_bedrock_probe_cache", None)


def test_runtime_model_catalog_excludes_bedrock_without_credentials(monkeypatch):
    _reset_bedrock_probe(monkeypatch)
    monkeypatch.setattr(workspace_gateway, "OllamaClient", _HealthyOllama)
    monkeypatch.setattr(workspace_gateway, "settings", SimpleNamespace(
        llm_model_default="qwen2.5:1.5b",
        groq_api_key="",
        llm_fallback="off",
        groq_model_fast="llama-3.1-8b-instant",
        groq_model_smart="llama-3.3-70b-versatile",
        openai_api_key="",
        openai_model_chat="gpt-4o-mini",
        aws_access_key_id="",
        aws_secret_access_key="",
        aws_default_region="us-east-1",
    ))

    rows = workspace_gateway._runtime_model_catalog()

    assert {row["model_slug"] for row in rows} == {"ollama-default"}


def test_runtime_model_catalog_marks_bedrock_disconnected_when_probe_fails(monkeypatch):
    _reset_bedrock_probe(monkeypatch)
    monkeypatch.setattr(workspace_gateway, "OllamaClient", _HealthyOllama)
    monkeypatch.setattr(workspace_gateway, "_probe_bedrock_connectivity", lambda: False)
    monkeypatch.setattr(workspace_gateway, "settings", SimpleNamespace(
        llm_model_default="qwen2.5:1.5b",
        groq_api_key="",
        llm_fallback="off",
        groq_model_fast="llama-3.1-8b-instant",
        groq_model_smart="llama-3.3-70b-versatile",
        openai_api_key="",
        openai_model_chat="gpt-4o-mini",
        aws_access_key_id="bad-key",
        aws_secret_access_key="bad-secret",
        aws_default_region="us-east-1",
    ))

    rows = workspace_gateway._runtime_model_catalog()
    bedrock = next(row for row in rows if row["model_slug"] == "bedrock-haiku")

    assert bedrock["provider"] == "bedrock"
    assert bedrock["connected"] is False


def test_runtime_model_catalog_marks_bedrock_connected_when_probe_succeeds(monkeypatch):
    _reset_bedrock_probe(monkeypatch)
    monkeypatch.setattr(workspace_gateway, "OllamaClient", _HealthyOllama)
    monkeypatch.setattr(workspace_gateway, "_probe_bedrock_connectivity", lambda: True)
    monkeypatch.setattr(workspace_gateway, "settings", SimpleNamespace(
        llm_model_default="qwen2.5:1.5b",
        groq_api_key="",
        llm_fallback="off",
        groq_model_fast="llama-3.1-8b-instant",
        groq_model_smart="llama-3.3-70b-versatile",
        openai_api_key="",
        openai_model_chat="gpt-4o-mini",
        aws_access_key_id="valid-key",
        aws_secret_access_key="valid-secret",
        aws_default_region="us-east-1",
    ))

    rows = workspace_gateway._runtime_model_catalog()
    bedrock = next(row for row in rows if row["model_slug"] == "bedrock-haiku")

    assert bedrock["connected"] is True


def test_runtime_model_catalog_includes_openai_when_key_is_configured(monkeypatch):
    _reset_bedrock_probe(monkeypatch)
    monkeypatch.setattr(workspace_gateway, "OllamaClient", _HealthyOllama)
    monkeypatch.setattr(workspace_gateway, "settings", SimpleNamespace(
        llm_model_default="qwen2.5:1.5b",
        groq_api_key="",
        llm_fallback="off",
        groq_model_fast="llama-3.1-8b-instant",
        groq_model_smart="llama-3.3-70b-versatile",
        openai_api_key="configured",
        openai_model_chat="gpt-4o-mini",
        aws_access_key_id="",
        aws_secret_access_key="",
        aws_default_region="us-east-1",
    ))

    rows = workspace_gateway._runtime_model_catalog()
    openai = next(row for row in rows if row["model_slug"] == "openai-chat")

    assert openai["provider"] == "openai"
    assert openai["connected"] is True
    assert openai["bedrock_model_id"] == "gpt-4o-mini"
