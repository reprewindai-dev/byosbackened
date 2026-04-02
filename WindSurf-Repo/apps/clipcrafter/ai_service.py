"""ClipCrafter AI service - HuggingFace powered caption, description, analysis."""

import asyncio
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


async def generate_clip_description(video_title: str, transcript: Optional[str] = None) -> str:
    """Generate SEO description for a clip using Mistral via HuggingFace."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        from apps.ai.contracts import ChatMessage
        provider = HuggingFaceProvider()
        
        content = f"Video title: {video_title}"
        if transcript:
            content += f"\nTranscript excerpt: {transcript[:500]}"
        
        messages = [
            ChatMessage(role="system", content="You are a short-form video content expert. Generate engaging, SEO-optimized descriptions for social media clips. Keep it under 150 words."),
            ChatMessage(role="user", content=f"Generate a compelling description for this clip:\n{content}"),
        ]
        result = await provider.chat(messages, temperature=0.7, max_tokens=200)
        return result.content
    except Exception as e:
        logger.warning(f"HF clip description failed: {e}")
        return f"Clip: {video_title}"


async def generate_clip_hashtags(description: str, category: Optional[str] = None) -> List[str]:
    """Generate relevant hashtags for a clip."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        from apps.ai.contracts import ChatMessage
        provider = HuggingFaceProvider()
        
        messages = [
            ChatMessage(role="system", content="Generate exactly 10 relevant hashtags for social media. Return only the hashtags separated by spaces, each starting with #. No explanations."),
            ChatMessage(role="user", content=f"Content: {description[:300]}\nCategory: {category or 'general'}"),
        ]
        result = await provider.chat(messages, temperature=0.5, max_tokens=100)
        tags = [t.strip() for t in result.content.split() if t.startswith('#')]
        return tags[:10] if tags else ["#content", "#video", "#clips"]
    except Exception as e:
        logger.warning(f"HF hashtag generation failed: {e}")
        return ["#content", "#video", "#clips", "#shortform"]


async def caption_thumbnail(image_url: str) -> str:
    """Generate alt-text/caption for a clip thumbnail using BLIP."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        provider = HuggingFaceProvider()
        return await provider.caption_image(image_url)
    except Exception as e:
        logger.warning(f"HF thumbnail caption failed: {e}")
        return ""


async def analyze_clip_sentiment(transcript: str) -> Dict[str, Any]:
    """Analyze sentiment/tone of a clip's content."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        provider = HuggingFaceProvider()
        return await provider.analyze_sentiment(transcript[:500])
    except Exception as e:
        logger.warning(f"HF sentiment analysis failed: {e}")
        return {"label": "NEUTRAL", "score": 0.5}


async def transcribe_audio(audio_url: str, language: Optional[str] = None) -> str:
    """Transcribe audio using HuggingFace Whisper large-v3."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        provider = HuggingFaceProvider()
        result = await provider.transcribe(audio_url, language=language)
        return result.text
    except Exception as e:
        logger.warning(f"HF transcription failed: {e}")
        return ""


async def embed_clip_content(text: str) -> List[float]:
    """Get semantic embedding for clip content - for similarity search."""
    try:
        from apps.ai.providers.huggingface import HuggingFaceProvider
        provider = HuggingFaceProvider()
        result = await provider.embed(text)
        return result.embedding
    except Exception as e:
        logger.warning(f"HF embedding failed: {e}")
        return []
