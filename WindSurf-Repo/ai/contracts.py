"""AI provider contracts (abstract interfaces)."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class TranscriptionResult(BaseModel):
    """Transcription result."""

    text: str
    language: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    """Chat message."""

    role: str  # "system", "user", "assistant"
    content: str


class ChatResult(BaseModel):
    """Chat completion result."""

    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingResult(BaseModel):
    """Embedding result."""

    embedding: List[float]
    model: str
    metadata: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Search result."""

    title: str
    url: str
    snippet: str
    position: int
    metadata: Optional[Dict[str, Any]] = None


class STTProvider(ABC):
    """Speech-to-text provider interface."""

    @abstractmethod
    async def transcribe(
        self, audio_url: str, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe audio file."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass


class LLMProvider(ABC):
    """LLM provider interface."""

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatResult:
        """Generate chat completion."""
        pass

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass


class SearchProvider(ABC):
    """Search provider interface."""

    @abstractmethod
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Perform search."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass
