"""OpenAI provider (optional, only when valuable - must be documented)."""
import httpx
from typing import Optional, List
from apps.ai.contracts import STTProvider, LLMProvider, TranscriptionResult, ChatMessage, ChatResult, EmbeddingResult
from core.config import get_settings

settings = get_settings()


class OpenAIOptionalProvider(STTProvider, LLMProvider):
    """
    OpenAI provider - USE ONLY WHEN VALUABLE.

    This provider should only be used when:
    - A specific capability is required that Hugging Face/local models can't provide
    - Client requirement mandates OpenAI
    - Documented business reason exists

    Default to Hugging Face or local models first.
    """

    def __init__(self):
        self.api_key = getattr(settings, "openai_api_key", "")
        self.base_url = "https://api.openai.com/v1"
        self.chat_model = getattr(settings, "openai_model_chat", "gpt-4o-mini")
        self.whisper_model = getattr(settings, "openai_model_whisper", "whisper-1")
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def transcribe(
        self, audio_url: str, language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe using OpenAI Whisper.

        VALUABLE REASON REQUIRED: Only use if:
        - Accuracy requirement exceeds HF/local capabilities
        - Client contract requires OpenAI
        - Documented exception approved
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured (and required for this operation)")

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Stub: implement actual audio fetch + OpenAI Whisper API
            # Example: fetch audio_url, POST to /audio/transcriptions
            response = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers=self.headers,
                files={"file": "placeholder"},  # Replace with actual file handling
                data={"model": self.whisper_model, "language": language},
            )
            response.raise_for_status()
            data = response.json()
            return TranscriptionResult(
                text=data.get("text", ""),
                language=data.get("language", language),
                provider="openai",
            )

    async def chat(
        self, messages: List[ChatMessage], temperature: float = 0.7, max_tokens: Optional[int] = None
    ) -> ChatResult:
        """
        Chat completion using OpenAI.

        VALUABLE REASON REQUIRED: Only use if:
        - Specific model capability needed (e.g., function calling)
        - Client requirement
        - Documented exception
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured (and required for this operation)")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={**self.headers, "Content-Type": "application/json"},
                json={
                    "model": self.chat_model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return ChatResult(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                usage=data.get("usage"),
                provider="openai",
            )

    async def embed(self, text: str) -> EmbeddingResult:
        """
        Generate embedding using OpenAI.

        VALUABLE REASON REQUIRED: Prefer Hugging Face embeddings first.
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured (and required for this operation)")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={**self.headers, "Content-Type": "application/json"},
                json={
                    "model": "text-embedding-3-small",
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()
            return EmbeddingResult(
                embedding=data["data"][0]["embedding"],
                model=data["model"],
                provider="openai",
            )

    def get_name(self) -> str:
        """Get provider name."""
        return "openai"
