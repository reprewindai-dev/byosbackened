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
    """Register default providers.

    Primary LLM: LocalLLMProvider → Ollama (http://host.docker.internal:11434)
    Fallback: none — LLM_FALLBACK=off enforced in OllamaClient.
    Legacy providers (HuggingFace, OpenAI) remain registered but are not primary.
    """
    registry = get_registry()

    # ── LLM providers (ollama = primary) ─────────────────────────────────────
    registry.register_llm_provider("ollama", LocalLLMProvider)      # PRIMARY
    registry.register_llm_provider("local_llm", LocalLLMProvider)   # alias
    registry.register_llm_provider("huggingface", HuggingFaceProvider)
    registry.register_llm_provider("openai", OpenAIOptionalProvider)

    # ── STT providers ─────────────────────────────────────────────────────────
    registry.register_stt_provider("local_whisper", LocalWhisperProvider)
    registry.register_stt_provider("huggingface", HuggingFaceProvider)
    registry.register_stt_provider("openai", OpenAIOptionalProvider)

    # ── Search providers ──────────────────────────────────────────────────────
    registry.register_search_provider("serpapi", SERPProvider)
