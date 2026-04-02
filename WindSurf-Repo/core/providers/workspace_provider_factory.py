"""Workspace-aware provider factory (BYOK support)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.ai.providers import (
    HuggingFaceProvider,
    LocalLLMProvider,
    OpenAIOptionalProvider,
    LocalWhisperProvider,
    SERPProvider,
)
from core.security.workspace_secrets import get_workspace_secrets_service


class WorkspaceProviderFactory:
    """Create provider instances with workspace-scoped credentials when available."""

    def __init__(self):
        self.secrets_service = get_workspace_secrets_service()

    def _get_api_key(self, db: Session, workspace_id: str, provider: str) -> str | None:
        return self.secrets_service.get_secret(
            db=db,
            workspace_id=workspace_id,
            provider=provider,
            secret_name="api_key",
        )

    def get_llm_provider(self, db: Session, workspace_id: str, provider_name: str):
        if provider_name == "openai":
            return OpenAIOptionalProvider(api_key=self._get_api_key(db, workspace_id, "openai"))
        if provider_name == "local_llm":
            return LocalLLMProvider()
        # Default: huggingface
        return HuggingFaceProvider(api_key=self._get_api_key(db, workspace_id, "huggingface"))

    def get_stt_provider(self, db: Session, workspace_id: str, provider_name: str):
        if provider_name == "openai":
            return OpenAIOptionalProvider(api_key=self._get_api_key(db, workspace_id, "openai"))
        if provider_name == "local_whisper":
            return LocalWhisperProvider()
        return HuggingFaceProvider(api_key=self._get_api_key(db, workspace_id, "huggingface"))

    def get_search_provider(self, db: Session, workspace_id: str, provider_name: str):
        if provider_name == "serpapi":
            return SERPProvider(api_key=self._get_api_key(db, workspace_id, "serpapi"))
        return SERPProvider(api_key=self._get_api_key(db, workspace_id, "serpapi"))


_factory = WorkspaceProviderFactory()


def get_workspace_provider_factory() -> WorkspaceProviderFactory:
    return _factory
