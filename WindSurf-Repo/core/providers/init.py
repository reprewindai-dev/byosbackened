"""Initialize default providers."""

from core.providers.registry import get_registry
from apps.ai.providers import (
    HuggingFaceProvider,
    SERPProvider,
    LocalWhisperProvider,
    LocalLLMProvider,
    OpenAIOptionalProvider,
)


def initialize_providers():
    """Register default providers."""
    registry = get_registry()

    # Register STT providers
    registry.register_stt_provider("huggingface", HuggingFaceProvider)
    registry.register_stt_provider("local_whisper", LocalWhisperProvider)
    registry.register_stt_provider("openai", OpenAIOptionalProvider)

    # Register LLM providers
    registry.register_llm_provider("huggingface", HuggingFaceProvider)
    registry.register_llm_provider("local_llm", LocalLLMProvider)
    registry.register_llm_provider("openai", OpenAIOptionalProvider)

    # Register search providers
    registry.register_search_provider("serpapi", SERPProvider)
