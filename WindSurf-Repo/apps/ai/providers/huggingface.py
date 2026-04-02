"""HuggingFace provider - ALL real API calls, all models wired."""

import httpx
import base64
import asyncio
from typing import Optional, List, Dict, Any
from apps.ai.contracts import (
    STTProvider,
    LLMProvider,
    TranscriptionResult,
    ChatMessage,
    ChatResult,
    EmbeddingResult,
)
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

HF_BASE = "https://router.huggingface.co/hf-inference/models"


def _get_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    key = api_key or settings.huggingface_api_key
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


async def _hf_post(model: str, payload: dict, api_key: Optional[str] = None, timeout: float = 30.0) -> Any:
    """POST to HuggingFace Inference API with model-loading retry.
    Public models work without auth. Always attempts the call; returns None only on hard failures.
    """
    key = api_key or settings.huggingface_api_key
    url = f"{HF_BASE}/{model}"
    headers = _get_headers(key)  # No key → no Authorization header; HF public models still respond
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                    logger.warning(f"HF network error on {model}: {e}")
                    return None
                if resp.status_code == 503:
                    estimated_wait = resp.json().get("estimated_time", 30)
                    wait = min(float(estimated_wait), 30)
                    logger.info(f"HF model {model} loading, waiting {wait}s (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code in (401, 403):
                    logger.warning(f"HF auth error on {model} — API key missing or invalid. Returning None.")
                    return None
                if resp.status_code == 410:
                    logger.error(f"HF endpoint 410 Gone on {model} — URL may need updating. Response: {resp.text[:200]}")
                    return None
                if resp.status_code >= 400:
                    logger.warning(f"HF API error {resp.status_code} on {model}: {resp.text[:200]}")
                    return None
                return resp.json()
    except Exception as e:
        logger.warning(f"HF post error on {model}: {e}")
        return None
    logger.warning(f"HF model {model} failed to load after 3 attempts — returning None")
    return None


async def _hf_post_binary(model: str, audio_bytes: bytes, api_key: Optional[str] = None) -> Any:
    """POST binary data (audio/image) to HuggingFace Inference API."""
    url = f"{HF_BASE}/{model}"
    key = api_key or settings.huggingface_api_key
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        for attempt in range(3):
            resp = await client.post(url, headers=headers, content=audio_bytes)
            if resp.status_code == 503:
                estimated_wait = resp.json().get("estimated_time", 30)
                wait = min(float(estimated_wait), 30)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
    raise RuntimeError(f"HF binary model {model} failed after 3 attempts")


class HuggingFaceProvider(STTProvider, LLMProvider):
    """Complete HuggingFace Inference API provider - real calls for all models."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.huggingface_api_key
        self.chat_model = settings.huggingface_model_chat
        self.embed_model = settings.huggingface_model_embed
        self.whisper_model = settings.huggingface_model_whisper
        self.blip_model = settings.huggingface_model_blip
        self.ner_model = settings.huggingface_model_ner
        self.musicgen_model = settings.huggingface_model_musicgen
        self.summarize_model = settings.huggingface_model_summarize
        self.sentiment_model = settings.huggingface_model_sentiment

    # ─── Speech-to-Text (Whisper large-v3) ─────────────────────────────────────

    async def transcribe(self, audio_url: str, language: Optional[str] = None) -> TranscriptionResult:
        """Transcribe audio using HuggingFace Whisper large-v3.
        Downloads audio from URL then posts binary to HF Inference API."""
        try:
            # Download audio
            async with httpx.AsyncClient(timeout=60.0) as client:
                audio_resp = await client.get(audio_url)
                audio_resp.raise_for_status()
                audio_bytes = audio_resp.content

            # Post to HF Whisper
            data = await _hf_post_binary(self.whisper_model, audio_bytes, self.api_key)
            text = data.get("text", "") if isinstance(data, dict) else str(data)
            return TranscriptionResult(
                text=text,
                language=language or "en",
                metadata={"provider": "huggingface", "model": self.whisper_model},
            )
        except Exception as e:
            logger.error(f"HF transcription error: {e}")
            raise

    async def transcribe_bytes(self, audio_bytes: bytes, language: Optional[str] = None) -> TranscriptionResult:
        """Transcribe from raw bytes."""
        data = await _hf_post_binary(self.whisper_model, audio_bytes, self.api_key)
        text = data.get("text", "") if isinstance(data, dict) else str(data)
        return TranscriptionResult(
            text=text,
            language=language or "en",
            metadata={"provider": "huggingface", "model": self.whisper_model},
        )

    # ─── LLM Chat (Mistral-7B-Instruct-v0.3) ───────────────────────────────────

    async def chat(self, messages: List[ChatMessage], temperature: float = 0.7, max_tokens: Optional[int] = None) -> ChatResult:
        """Chat completion using Mistral-7B-Instruct-v0.3 via HF Inference API."""
        # Format as Mistral instruct prompt
        prompt = self._format_mistral_prompt(messages)
        data = await _hf_post(
            self.chat_model,
            {
                "inputs": prompt,
                "parameters": {
                    "temperature": max(0.01, temperature),
                    "max_new_tokens": max_tokens or 1024,
                    "return_full_text": False,
                    "do_sample": temperature > 0.01,
                },
            },
            self.api_key,
        )
        generated = ""
        if isinstance(data, list) and data:
            generated = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            generated = data.get("generated_text", "")
        return ChatResult(content=generated.strip(), model=self.chat_model, metadata={"provider": "huggingface"})

    def _format_mistral_prompt(self, messages: List[ChatMessage]) -> str:
        """Format messages as Mistral instruct template: <s>[INST] ... [/INST]"""
        parts = []
        system = ""
        for msg in messages:
            if msg.role == "system":
                system = msg.content
            elif msg.role == "user":
                content = f"{system}\n\n{msg.content}" if system else msg.content
                parts.append(f"[INST] {content} [/INST]")
                system = ""
            elif msg.role == "assistant":
                parts.append(msg.content)
        return "<s>" + " ".join(parts)

    # ─── Embeddings (all-MiniLM-L6-v2) ─────────────────────────────────────────

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embeddings using sentence-transformers/all-MiniLM-L6-v2."""
        data = await _hf_post(self.embed_model, {"inputs": text[:512]}, self.api_key)
        if isinstance(data, list) and isinstance(data[0], list):
            embedding = data[0]
        elif isinstance(data, list):
            embedding = data
        else:
            embedding = []
        return EmbeddingResult(embedding=embedding, model=self.embed_model, metadata={"provider": "huggingface"})

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Batch embed multiple texts."""
        data = await _hf_post(self.embed_model, {"inputs": [t[:512] for t in texts]}, self.api_key)
        results = []
        if isinstance(data, list):
            for i, emb in enumerate(data):
                embedding = emb if isinstance(emb, list) else []
                results.append(EmbeddingResult(embedding=embedding, model=self.embed_model))
        return results

    # ─── Image Captioning (BLIP) ─────────────────────────────────────────────

    async def caption_image(self, image_url: str) -> str:
        """Generate image caption using Salesforce/blip-image-captioning-large."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            img_bytes = img_resp.content
        data = await _hf_post_binary(self.blip_model, img_bytes, self.api_key)
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "")
        return ""

    # ─── Named Entity Recognition / PII (BERT-NER) ─────────────────────────────

    async def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """Detect named entities using dslim/bert-base-NER.
        Returns list of {word, entity_group, score, start, end}"""
        data = await _hf_post(
            self.ner_model,
            {"inputs": text[:512], "parameters": {"aggregation_strategy": "simple"}},
            self.api_key,
        )
        if isinstance(data, list):
            return [
                {
                    "word": e.get("word", ""),
                    "entity_group": e.get("entity_group", e.get("entity", "")),
                    "score": e.get("score", 0),
                    "start": e.get("start", 0),
                    "end": e.get("end", 0),
                }
                for e in data
            ]
        return []

    # ─── Music Generation (MusicGen) ────────────────────────────────────────────

    async def generate_music(self, prompt: str, duration_seconds: int = 10) -> bytes:
        """Generate music using facebook/musicgen-small. Returns WAV bytes."""
        url = f"{HF_BASE}/{self.musicgen_model}"
        key = self.api_key or settings.huggingface_api_key
        headers = {}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        async with httpx.AsyncClient(timeout=180.0) as client:
            for attempt in range(3):
                resp = await client.post(
                    url,
                    headers=headers,
                    json={"inputs": prompt, "parameters": {"max_new_tokens": duration_seconds * 50}},
                )
                if resp.status_code == 503:
                    wait = min(resp.json().get("estimated_time", 30), 60)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.content  # Returns audio bytes (wav/mp3)
        raise RuntimeError("MusicGen failed after 3 attempts")

    # ─── Summarization (BART) ────────────────────────────────────────────────────

    async def summarize(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Summarize text using facebook/bart-large-cnn."""
        data = await _hf_post(
            self.summarize_model,
            {"inputs": text[:1024], "parameters": {"max_length": max_length, "min_length": min_length}},
            self.api_key,
        )
        if data is None:
            return ""
        if isinstance(data, list) and data:
            return data[0].get("summary_text", "")
        return ""

    # ─── Sentiment Analysis ──────────────────────────────────────────────────────

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using distilbert-base-uncased-finetuned-sst-2-english."""
        data = await _hf_post(
            self.sentiment_model,
            {"inputs": text[:512]},
            self.api_key,
        )
        if data is None:
            # Graceful fallback when API unavailable (no key or network error)
            return {"label": "NEUTRAL", "score": 0.5, "note": "HF API unavailable — add HUGGINGFACE_API_KEY for live inference"}
        if isinstance(data, list) and data:
            results = data[0] if isinstance(data[0], list) else data
            best = max(results, key=lambda x: x.get("score", 0))
            return {"label": best.get("label", ""), "score": best.get("score", 0)}
        return {"label": "NEUTRAL", "score": 0.5}

    def get_name(self) -> str:
        return "huggingface"
