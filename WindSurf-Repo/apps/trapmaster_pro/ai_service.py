"""TrapMaster Pro AI service - HuggingFace powered music generation & analysis."""

import asyncio
import logging
import base64
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


async def generate_beat_description(
    genre: str, tempo: Optional[int] = None, mood: Optional[str] = None, key: Optional[str] = None
) -> str:
    """Generate descriptive text for a beat using Mistral."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        from apps.ai.contracts import ChatMessage
        provider = HuggingFaceProvider()

        details = f"Genre: {genre}"
        if tempo:
            details += f", Tempo: {tempo} BPM"
        if mood:
            details += f", Mood: {mood}"
        if key:
            details += f", Key: {key}"

        messages = [
            ChatMessage(role="system", content="You are a music producer and beat maker. Generate a vivid, engaging description for a beat. Keep it under 100 words. Be specific about sound, feel, and vibe."),
            ChatMessage(role="user", content=f"Describe this beat:\n{details}"),
        ]
        result = await provider.chat(messages, temperature=0.8, max_tokens=150)
        return result.content
    except Exception as e:
        logger.warning(f"HF beat description failed: {e}")
        return f"{genre} beat at {tempo or 140} BPM"


async def generate_track_tags(genre: str, mood: Optional[str] = None, description: Optional[str] = None) -> List[str]:
    """Generate searchable tags for a track."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        from apps.ai.contracts import ChatMessage
        provider = HuggingFaceProvider()

        messages = [
            ChatMessage(role="system", content="Generate exactly 8 music tags for a track. Return only tags separated by commas. No explanations. Tags should describe genre, mood, instruments, and energy."),
            ChatMessage(role="user", content=f"Genre: {genre}\nMood: {mood or 'energetic'}\nDescription: {description or ''}"),
        ]
        result = await provider.chat(messages, temperature=0.5, max_tokens=80)
        tags = [t.strip().lower() for t in result.content.split(',')]
        return [t for t in tags if t][:8]
    except Exception as e:
        logger.warning(f"HF tag generation failed: {e}")
        return [genre.lower(), "beat", "instrumental"]


async def generate_music_sample(prompt: str, duration_seconds: int = 10) -> bytes:
    """Generate a music sample using facebook/musicgen-small.
    Returns WAV audio bytes."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        provider = HuggingFaceProvider()
        return await provider.generate_music(prompt, duration_seconds)
    except Exception as e:
        logger.error(f"HF music generation failed: {e}")
        raise


async def analyze_track_sentiment(title: str, description: Optional[str] = None) -> Dict[str, Any]:
    """Analyze mood/sentiment of a track based on its metadata."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        provider = HuggingFaceProvider()
        text = f"{title} {description or ''}".strip()
        return await provider.analyze_sentiment(text)
    except Exception as e:
        logger.warning(f"HF sentiment failed: {e}")
        return {"label": "NEUTRAL", "score": 0.5}


async def suggest_similar_tracks(track_description: str) -> List[str]:
    """Suggest similar existing tracks/artists using Mistral."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        from apps.ai.contracts import ChatMessage
        provider = HuggingFaceProvider()

        messages = [
            ChatMessage(role="system", content="You are a music expert. Suggest 5 real similar tracks or artists. Return only a comma-separated list of 'Artist - Track' or just artist names."),
            ChatMessage(role="user", content=f"Find similar music to: {track_description[:200]}"),
        ]
        result = await provider.chat(messages, temperature=0.6, max_tokens=100)
        suggestions = [s.strip() for s in result.content.split(',') if s.strip()]
        return suggestions[:5]
    except Exception as e:
        logger.warning(f"HF suggestions failed: {e}")
        return []
