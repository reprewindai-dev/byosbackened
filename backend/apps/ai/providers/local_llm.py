"""Local LLM provider (self-hosted, e.g., Ollama/vLLM)."""
import httpx
from typing import Optional, List
from apps.ai.contracts import LLMProvider, ChatMessage, ChatResult, EmbeddingResult
from core.config import get_settings

settings = get_settings()


class LocalLLMProvider(LLMProvider):
    """Self-hosted LLM provider (Ollama/vLLM compatible)."""

    def __init__(self):
        self.base_url = settings.llm_base_url  # Ollama: http://host.docker.internal:11434
        self.model = settings.llm_model_default

    async def chat(
        self, messages: List[ChatMessage], temperature: float = 0.7, max_tokens: Optional[int] = None
    ) -> ChatResult:
        """Chat completion using local LLM."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Stub: implement actual local LLM API call
            # Example: POST to {base_url}/v1/chat/completions (OpenAI-compatible)
            payload: dict = {
                "model": self.model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "stream": False,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return ChatResult(
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", self.model),
                provider="ollama",
            )

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding using local model."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Stub: implement actual embedding API call
            response = await client.post(
                f"{self.base_url}/v1/embeddings",
                json={"input": text},
            )
            response.raise_for_status()
            data = response.json()
            return EmbeddingResult(
                embedding=data["data"][0]["embedding"],
                model=data.get("model", "local_embed"),
                provider="local_llm",
            )

    def get_name(self) -> str:
        """Get provider name."""
        return "local_llm"
