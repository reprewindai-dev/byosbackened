"""
Ollama LLM Client — BYOS AI Backend
Single provider: local Ollama only. LLM_FALLBACK=off enforced.
All calls blocked if Ollama is unreachable — no silent degradation.
"""
import time
import logging
import httpx
from typing import Optional
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaError(Exception):
    """Raised when Ollama is unreachable or returns an error."""


class OllamaClient:
    """
    HTTP client for local Ollama inference.
    Endpoint: POST {LLM_BASE_URL}/api/generate
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model_default
        self.timeout = timeout or settings.llm_timeout_seconds
        self._generate_url = f"{self.base_url}/api/generate"
        self._tags_url = f"{self.base_url}/api/tags"

    # ── Public interface ──────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
        options: Optional[dict] = None,
    ) -> dict:
        """
        Call Ollama /api/generate.
        Returns: { "response": str, "model": str, "tokens": int, "latency_ms": int }
        Raises OllamaError on any failure — no fallback.
        """
        if settings.llm_fallback != "off":
            logger.warning("LLM_FALLBACK is not 'off' — enforcing local-only anyway")

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": stream,
        }
        if options:
            payload["options"] = options

        start = time.monotonic()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self._generate_url, json=payload)
                response.raise_for_status()
        except httpx.ConnectError as e:
            raise OllamaError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Ensure Ollama is running and LLM_BASE_URL is correct."
            ) from e
        except httpx.TimeoutException as e:
            raise OllamaError(
                f"Ollama request timed out after {self.timeout}s for model '{payload['model']}'"
            ) from e
        except httpx.HTTPStatusError as e:
            raise OllamaError(
                f"Ollama returned HTTP {e.response.status_code}: {e.response.text[:300]}"
            ) from e

        latency_ms = int((time.monotonic() - start) * 1000)
        data = response.json()

        text = data.get("response", "")
        tokens_eval = data.get("eval_count", 0)
        tokens_prompt = data.get("prompt_eval_count", 0)

        logger.debug(
            f"[Ollama] model={data.get('model')} "
            f"tokens={tokens_prompt}+{tokens_eval} latency={latency_ms}ms"
        )

        return {
            "response": text,
            "model": data.get("model", payload["model"]),
            "prompt_tokens": tokens_prompt,
            "completion_tokens": tokens_eval,
            "total_tokens": tokens_prompt + tokens_eval,
            "latency_ms": latency_ms,
            "done": data.get("done", True),
        }

    def health_check(self) -> bool:
        """
        Returns True if Ollama is reachable and has at least one model loaded.
        Used by GET /status.
        """
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(self._tags_url)
                r.raise_for_status()
                models = r.json().get("models", [])
                return len(models) > 0
        except Exception as e:
            logger.warning(f"[Ollama] health_check failed: {e}")
            return False

    def list_models(self) -> list[str]:
        """Return list of model names available in local Ollama."""
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(self._tags_url)
                r.raise_for_status()
                return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []


def get_ollama_client() -> OllamaClient:
    """FastAPI dependency — returns singleton-like OllamaClient."""
    return OllamaClient()
