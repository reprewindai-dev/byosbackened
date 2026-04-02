"""Local LLM — Ollama primary, Groq self-healing fallback, Redis circuit breaker."""
from core.llm.ollama_client import OllamaClient, OllamaError, get_ollama_client
from core.llm.circuit_breaker import get_state, record_success, record_failure, is_open, status_dict
from core.llm.groq_fallback import call_groq, GroqFallbackError

__all__ = [
    "OllamaClient", "OllamaError", "get_ollama_client",
    "get_state", "record_success", "record_failure", "is_open", "status_dict",
    "call_groq", "GroqFallbackError",
]
