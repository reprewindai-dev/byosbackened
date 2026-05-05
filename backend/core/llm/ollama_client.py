"""
Ollama LLM Client — BYOS AI Backend
Uses the official `ollama` Python library (pip install ollama).
Single provider: local Ollama only. LLM_FALLBACK=off enforced.
All calls blocked if Ollama is unreachable — no silent degradation.
"""
import time
import logging
from typing import Optional

from ollama import Client as _OllamaSDK, ResponseError as _ResponseError

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaError(Exception):
    """Raised when Ollama is unreachable or returns an error."""


class OllamaClient:
    """
    Wrapper around the official `ollama` Python SDK.
    Keeps the same dict-returning interface so exec_router.py needs no changes.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model_default
        self.timeout = timeout or settings.llm_timeout_seconds
        self._client = _OllamaSDK(host=self.base_url, timeout=self.timeout)

    # ── Public interface ──────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
        options: Optional[dict] = None,
    ) -> dict:
        """
        Call Ollama generate via official SDK.
        Returns: { response, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, done }
        Raises OllamaError on any failure — no fallback.
        """
        if settings.llm_fallback != "off":
            logger.warning("[Ollama] LLM_FALLBACK is not 'off' — enforcing local-only anyway")

        target_model = model or self.model
        start = time.monotonic()

        try:
            resp = self._client.generate(
                model=target_model,
                prompt=prompt,
                stream=stream,
                options=options or {},
            )
        except _ResponseError as e:
            raise OllamaError(f"Ollama API error ({e.status_code}): {e.error}") from e
        except Exception as e:
            # Covers httpx.ConnectError, TimeoutException, etc.
            msg = str(e)
            if "connect" in msg.lower() or "connection" in msg.lower():
                raise OllamaError(
                    f"Cannot reach Ollama at {self.base_url}. "
                    "Ensure Ollama is running and LLM_BASE_URL is correct."
                ) from e
            raise OllamaError(f"Ollama request failed: {msg}") from e

        latency_ms = int((time.monotonic() - start) * 1000)
        tokens_prompt = resp.prompt_eval_count or 0
        tokens_eval = resp.eval_count or 0

        logger.debug(
            "[Ollama] model=%s tokens=%d+%d latency=%dms",
            resp.model, tokens_prompt, tokens_eval, latency_ms,
        )

        return {
            "response": resp.response,
            "model": resp.model,
            "prompt_tokens": tokens_prompt,
            "completion_tokens": tokens_eval,
            "total_tokens": tokens_prompt + tokens_eval,
            "latency_ms": latency_ms,
            "done": resp.done,
        }

    def health_check(self) -> bool:
        """
        Returns True if Ollama is reachable and has at least one model loaded.
        """
        try:
            models = self._client.list()
            return len(models.models) > 0
        except Exception as e:
            logger.warning("[Ollama] health_check failed: %s", e)
            return False

    def list_models(self) -> list[str]:
        """Return list of model names available in local Ollama."""
        try:
            return [m.model for m in self._client.list().models]
        except Exception:
            return []


def get_ollama_client() -> OllamaClient:
    """FastAPI dependency — returns a fresh OllamaClient per request."""
    return OllamaClient()
