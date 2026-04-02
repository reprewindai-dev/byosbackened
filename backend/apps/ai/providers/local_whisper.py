"""Local Whisper provider (self-hosted)."""
import httpx
from typing import Optional
from apps.ai.contracts import STTProvider, TranscriptionResult
from core.config import get_settings

settings = get_settings()


class LocalWhisperProvider(STTProvider):
    """Self-hosted Whisper provider."""

    def __init__(self):
        self.base_url = settings.local_whisper_url or "http://whisper:8000"

    async def transcribe(
        self, audio_url: str, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using local Whisper service."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Stub: implement actual audio fetch + local Whisper API call
            # Example: POST to {base_url}/transcribe with audio file
            response = await client.post(
                f"{self.base_url}/transcribe",
                json={"audio_url": audio_url, "language": language},
            )
            response.raise_for_status()
            data = response.json()
            return TranscriptionResult(
                text=data.get("text", ""),
                language=data.get("language", language),
                provider="local_whisper",
            )

    def get_name(self) -> str:
        """Get provider name."""
        return "local_whisper"
