"""Local LLM client — Ollama only. No external provider fallback."""
from core.llm.ollama_client import OllamaClient, get_ollama_client

__all__ = ["OllamaClient", "get_ollama_client"]
