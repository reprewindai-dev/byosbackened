"""
Groq fallback client for self-healing circuit breaker.
Used ONLY when Ollama circuit is open. Native httpx — no Groq SDK dependency.
"""
import time
import logging
import httpx
from typing import Optional
from functools import lru_cache
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GroqFallbackError(Exception):
    """Raised when Groq fallback also fails."""


@lru_cache(maxsize=8)
def _shared_groq_client(timeout_seconds: Optional[float] = None) -> httpx.Client:
    timeout = timeout_seconds or settings.groq_timeout_seconds
    return httpx.Client(
        timeout=timeout,
        http2=True,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )


def call_groq(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    seed: Optional[int] = None,
    timeout_seconds: Optional[float] = None,
) -> dict:
    """
    Call Groq /chat/completions synchronously.
    Returns same dict shape as OllamaClient.generate() for drop-in compatibility.
    Raises GroqFallbackError if Groq is unreachable or returns an error.
    """
    if not settings.groq_api_key:
        raise GroqFallbackError(
            "GROQ_API_KEY not set — cannot use Groq fallback. "
            "Set GROQ_API_KEY or set LLM_FALLBACK=off."
        )

    target_model = model or settings.groq_model
    payload = {
        "model": target_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens or settings.llm_max_tokens,
        "temperature": temperature if temperature is not None else 0.7,
        "stream": False,
    }
    if top_p is not None:
        payload["top_p"] = top_p
    if seed is not None:
        payload["seed"] = seed

    start = time.monotonic()
    try:
        client = _shared_groq_client(timeout_seconds)
        resp = client.post(
            f"{settings.groq_base_url}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
    except httpx.ConnectError as e:
        raise GroqFallbackError(f"Cannot reach Groq API: {e}") from e
    except httpx.TimeoutException as e:
        raise GroqFallbackError("Groq API request timed out") from e
    except httpx.HTTPStatusError as e:
        raise GroqFallbackError(
            f"Groq API returned HTTP {e.response.status_code}: {e.response.text[:300]}"
        ) from e

    latency_ms = int((time.monotonic() - start) * 1000)
    data = resp.json()

    choice = data["choices"][0]
    content = choice["message"]["content"]
    usage = data.get("usage", {})

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    logger.info(
        "[Groq Fallback] model=%s tokens=%d+%d latency=%dms",
        target_model, prompt_tokens, completion_tokens, latency_ms,
    )

    return {
        "response": content,
        "model": f"groq/{target_model}",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "latency_ms": latency_ms,
        "done": True,
        "provider": "groq",
    }
