"""Hugging Face provider (primary - free-ish, most tokens)."""

import httpx
from typing import Optional, List
from apps.ai.contracts import (
    STTProvider,
    LLMProvider,
    TranscriptionResult,
    ChatMessage,
    ChatResult,
    EmbeddingResult,
)
from core.config import get_settings

settings = get_settings()


class HuggingFaceProvider(STTProvider, LLMProvider):
    """Hugging Face inference provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.huggingface_api_key
        self.base_url = "https://api-inference.huggingface.co"
        self.chat_model = settings.huggingface_model_chat
        self.embed_model = settings.huggingface_model_embed
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def transcribe(
        self, audio_url: str, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using Hugging Face Whisper."""
        # Note: HF inference API for Whisper requires audio file upload
        # This is a stub - implement actual audio fetch + upload to HF
        async with httpx.AsyncClient() as client:
            # For now, return a placeholder
            # In production: fetch audio_url, upload to HF, get transcription
            response = await client.post(
                f"{self.base_url}/models/openai/whisper-large-v3",
                headers=self.headers,
                json={"inputs": "placeholder"},  # Replace with actual audio handling
            )
            response.raise_for_status()
            data = response.json()
            return TranscriptionResult(
                text=data.get("text", ""),
                language=language or "en",
                provider="huggingface",
            )

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        """Chat completion using Hugging Face."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Format messages for HF API
            prompt = self._format_messages(messages)
            response = await client.post(
                f"{self.base_url}/models/{self.chat_model}",
                headers=self.headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "temperature": temperature,
                        "max_new_tokens": max_tokens or 512,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            generated_text = (
                data[0].get("generated_text", "")
                if isinstance(data, list)
                else data.get("generated_text", "")
            )
            return ChatResult(
                content=generated_text,
                model=self.chat_model,
                provider="huggingface",
            )

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding using Hugging Face."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/models/{self.embed_model}",
                headers=self.headers,
                json={"inputs": text},
            )
            response.raise_for_status()
            data = response.json()
            embedding = data[0] if isinstance(data, list) else data
            return EmbeddingResult(
                embedding=embedding,
                model=self.embed_model,
                provider="huggingface",
            )

    def _format_messages(self, messages: List[ChatMessage]) -> str:
        """Format messages for HF API."""
        formatted = []
        for msg in messages:
            formatted.append(f"{msg.role}: {msg.content}")
        return "\n".join(formatted)

    def get_name(self) -> str:
        """Get provider name."""
        return "huggingface"
