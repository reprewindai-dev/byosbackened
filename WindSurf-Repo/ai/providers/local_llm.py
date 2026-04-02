"""Local LLM provider (self-hosted, e.g., Ollama/vLLM)."""

import httpx
import asyncio
import logging
from typing import Optional, List, Dict, Any
from apps.ai.contracts import LLMProvider, ChatMessage, ChatResult, EmbeddingResult
from core.config import get_settings
from core.cache.redis_cache import cache_service

settings = get_settings()
logger = logging.getLogger(__name__)


class LocalLLMProvider(LLMProvider):
    """Self-hosted LLM provider (Ollama/vLLM compatible)."""

    def __init__(self):
        self.base_url = settings.local_llm_url or "http://llm:8000"
        self.timeout = 120.0
        self.embedding_timeout = 30.0

    async def _check_health(self) -> bool:
        """Check if the LLM service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        """Chat completion using local LLM."""
        
        # Check cache first
        cache_key = f"llm:chat:{hash(str([m.content for m in messages]))}"
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.info("LLM chat cache hit")
            return ChatResult(**cached_result)
        
        # Verify service health
        if not await self._check_health():
            raise Exception("LLM service is unavailable")
        
        # Prepare request payload
        payload = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try OpenAI-compatible endpoint first
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                )
                
                # If OpenAI endpoint fails, try Ollama native endpoint
                if response.status_code != 200:
                    logger.warning(f"OpenAI endpoint failed, trying Ollama native: {response.status_code}")
                    ollama_payload = {
                        "model": "llama3.1",  # Default model
                        "messages": [{"role": m.role, "content": m.content} for m in messages],
                        "options": {
                            "temperature": temperature,
                        }
                    }
                    if max_tokens:
                        ollama_payload["options"]["num_predict"] = max_tokens
                    
                    response = await client.post(
                        f"{self.base_url}/api/chat",
                        json=ollama_payload,
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Both endpoints failed. Last status: {response.status_code}")
                    
                    # Parse Ollama response
                    data = response.json()
                    content = data.get("message", {}).get("content", "")
                    model = data.get("model", "local_llm")
                else:
                    # Parse OpenAI-compatible response
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    model = data.get("model", "local_llm")
                
                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                result = ChatResult(
                    content=content,
                    model=model,
                    provider="local_llm",
                )
                
                # Cache the result
                await cache_service.set(cache_key, result.dict(), ttl=300)  # 5 minutes
                
                logger.info(f"LLM chat completed in {execution_time:.2f}ms")
                return result
                
        except httpx.TimeoutException:
            logger.error("LLM request timed out")
            raise Exception("LLM request timed out")
        except httpx.ConnectError:
            logger.error("Failed to connect to LLM service")
            raise Exception("LLM service is unreachable")
        except Exception as e:
            logger.error(f"LLM chat failed: {e}")
            raise

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding using local model."""
        
        # Check cache first
        cache_key = f"llm:embed:{hash(text)}"
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.info("LLM embedding cache hit")
            return EmbeddingResult(**cached_result)
        
        # Verify service health
        if not await self._check_health():
            raise Exception("LLM service is unavailable")
        
        try:
            async with httpx.AsyncClient(timeout=self.embedding_timeout) as client:
                # Try OpenAI-compatible endpoint first
                response = await client.post(
                    f"{self.base_url}/v1/embeddings",
                    json={"input": text},
                )
                
                # If OpenAI endpoint fails, try alternative
                if response.status_code != 200:
                    logger.warning(f"OpenAI embedding endpoint failed: {response.status_code}")
                    # Try a generic embedding endpoint
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"text": text},
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Embedding generation failed: {response.status_code}")
                    
                    # Parse alternative response
                    data = response.json()
                    embedding = data.get("embedding", [])
                    model = data.get("model", "local_embed")
                else:
                    # Parse OpenAI-compatible response
                    data = response.json()
                    embedding = data["data"][0]["embedding"]
                    model = data.get("model", "local_embed")
                
                result = EmbeddingResult(
                    embedding=embedding,
                    model=model,
                    provider="local_llm",
                )
                
                # Cache the result
                await cache_service.set(cache_key, result.dict(), ttl=1800)  # 30 minutes
                
                logger.info(f"Generated embedding with {len(embedding)} dimensions")
                return result
                
        except httpx.TimeoutException:
            logger.error("Embedding request timed out")
            raise Exception("Embedding request timed out")
        except httpx.ConnectError:
            logger.error("Failed to connect to LLM service for embedding")
            raise Exception("LLM service is unreachable")
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def get_name(self) -> str:
        """Get provider name."""
        return "local_llm"

    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
        
        # Fallback to common models
        return ["llama3.1", "llama3.1:8b", "qwen2.5:7b"]
