"""Google Gemini LLM provider — implements LLMProvider contract."""
from typing import Optional, List
import httpx
import os

from apps.ai.contracts import LLMProvider, ChatMessage, ChatResult, EmbeddingResult


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    """Google Gemini provider via REST API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

    def get_name(self) -> str:
        return f"gemini/{self.model}"

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        """Non-streaming chat completion via Gemini generateContent."""
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = {"parts": [{"text": msg.content}]}
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{GEMINI_BASE_URL}/models/{self.model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})

        return ChatResult(
            content=text,
            model=self.model,
            usage=usage,
            metadata={"finish_reason": data["candidates"][0].get("finishReason")},
        )

    async def chat_stream(self, messages: List[ChatMessage], temperature: float = 0.7):
        """Streaming chat via Gemini streamGenerateContent — yields text chunks."""
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = {"parts": [{"text": msg.content}]}
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = (
            f"{GEMINI_BASE_URL}/models/{self.model}:streamGenerateContent"
            f"?key={self.api_key}&alt=sse"
        )

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        import json
                        raw = line[5:].strip()
                        if raw and raw != "[DONE]":
                            try:
                                chunk = json.loads(raw)
                                text = (
                                    chunk.get("candidates", [{}])[0]
                                    .get("content", {})
                                    .get("parts", [{}])[0]
                                    .get("text", "")
                                )
                                if text:
                                    yield text
                            except Exception:
                                continue

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate text embedding via Gemini."""
        embed_model = "text-embedding-004"
        url = f"{GEMINI_BASE_URL}/models/{embed_model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{embed_model}",
            "content": {"parts": [{"text": text}]},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return EmbeddingResult(
            embedding=data["embedding"]["values"],
            model=embed_model,
        )
