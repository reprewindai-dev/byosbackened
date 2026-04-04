"""
Ollama HTTP client — connects to local Ollama server at http://localhost:11434.
Supports: chat, generate, embeddings, model list, streaming.
Automatic retry with exponential backoff. Fallback-aware (returns is_available flag).
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "qwen2.5:3b"
_TIMEOUT = 120.0
_CONNECT_TIMEOUT = 5.0
_MAX_RETRIES = 2


class OllamaClient:
    """
    Async Ollama client.

    Usage:
        client = OllamaClient()
        result = await client.chat([{"role": "user", "content": "Hello"}])
        print(result["message"]["content"])
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = _TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # ── Availability ─────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Ping Ollama — returns True if server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=_CONNECT_TIMEOUT) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Return list of locally available model names."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                return [m["name"] for m in r.json().get("models", [])]
        except Exception as exc:
            logger.warning(f"[Ollama] Could not list models: {exc}")
            return []

    # ── Chat ──────────────────────────────────────────────────────────────────

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST /api/chat — multi-turn chat.
        Returns the full Ollama response dict:
          {"model": ..., "message": {"role": "assistant", "content": ...}, ...}
        """
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + messages
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        return await self._post_with_retry("/api/chat", payload)

    async def chat_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
    ) -> str:
        """Convenience wrapper — returns just the assistant text."""
        result = await self.chat(
            messages, model=model, temperature=temperature,
            max_tokens=max_tokens, system=system,
        )
        return result["message"]["content"]

    # ── Generate (single-turn) ────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
    ) -> str:
        """
        POST /api/generate — single-turn text generation.
        Returns generated text string.
        """
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        result = await self._post_with_retry("/api/generate", payload)
        return result.get("response", "")

    # ── Embeddings ────────────────────────────────────────────────────────────

    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        POST /api/embeddings — returns embedding vector.
        Uses nomic-embed-text if available, falls back to main model.
        """
        embed_model = model or "nomic-embed-text"
        payload = {"model": embed_model, "prompt": text}
        try:
            result = await self._post_with_retry("/api/embeddings", payload)
            return result.get("embedding", [])
        except Exception:
            # Fall back to main model embedding
            payload["model"] = self.model
            result = await self._post_with_retry("/api/embeddings", payload)
            return result.get("embedding", [])

    # ── Streaming ─────────────────────────────────────────────────────────────

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Streaming chat — yields text chunks as they arrive.
        Usage:
            async for chunk in client.stream_chat([...]):
                print(chunk, end="", flush=True)
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        import json
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                        if data.get("done"):
                            break
                    except Exception:
                        continue

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _post_with_retry(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST with exponential backoff retry."""
        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(f"{self.base_url}{path}", json=payload)
                    resp.raise_for_status()
                    return resp.json()
            except httpx.ConnectError as exc:
                last_exc = exc
                logger.warning(f"[Ollama] Connection refused at {self.base_url}{path} (attempt {attempt + 1})")
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(f"[Ollama] Timeout on {path} (attempt {attempt + 1})")
            except Exception as exc:
                last_exc = exc
                logger.error(f"[Ollama] Error on {path}: {exc}")

            if attempt < _MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"Ollama unavailable after {_MAX_RETRIES + 1} attempts. "
            f"Is Ollama running? Last error: {last_exc}"
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_client: Optional[OllamaClient] = None


def get_ollama_client(base_url: str = _DEFAULT_BASE_URL, model: str = _DEFAULT_MODEL) -> OllamaClient:
    """Return a cached OllamaClient instance."""
    global _client
    if _client is None:
        _client = OllamaClient(base_url=base_url, model=model)
    return _client
