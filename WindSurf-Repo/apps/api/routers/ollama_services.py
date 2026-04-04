"""
Ollama AI Services Router
Provides four business-ready endpoints backed by local Ollama:
  POST /ai/tag        — auto-tag content with categories & keywords
  POST /ai/recommend  — personalised content recommendations
  POST /ai/chat       — subscriber-facing support chatbot
  POST /ai/analytics  — business copy, descriptions, insights
  GET  /ai/status     — Ollama health + available models
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.ai.ollama_client import get_ollama_client, OllamaClient
from core.config import get_settings
from db.session import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/ai", tags=["AI Services (Ollama)"])


# ── Shared dependency ─────────────────────────────────────────────────────────

def get_ollama() -> OllamaClient:
    base_url = settings.local_llm_url or "http://localhost:11434"
    model = getattr(settings, "llm_model_default", "qwen2.5:3b")
    return get_ollama_client(base_url=base_url, model=model)


# ── Schemas ───────────────────────────────────────────────────────────────────

class TagRequest(BaseModel):
    title: str = Field(..., description="Content title")
    description: Optional[str] = Field(None, description="Optional description or transcript excerpt")
    content_type: Optional[str] = Field("video", description="Type of content: video, image, audio, text")
    max_tags: int = Field(10, ge=1, le=30)


class TagResponse(BaseModel):
    tags: List[str]
    categories: List[str]
    mood: Optional[str] = None
    duration_estimate: Optional[str] = None
    model: str


class RecommendRequest(BaseModel):
    user_history: List[str] = Field(..., description="List of recent content titles or tags the user engaged with")
    available_content: List[Dict[str, Any]] = Field(..., description="Pool of content to recommend from. Each item: {id, title, tags}")
    limit: int = Field(5, ge=1, le=20)
    reason: bool = Field(True, description="Include recommendation reason in response")


class RecommendResponse(BaseModel):
    recommendations: List[Dict[str, Any]]
    model: str


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Conversation history: [{role, content}]")
    persona: Optional[str] = Field(None, description="Support persona name shown to subscriber")
    stream: bool = Field(False, description="Stream response tokens")


class ChatResponse(BaseModel):
    reply: str
    model: str


class AnalyticsRequest(BaseModel):
    task: str = Field(
        ...,
        description=(
            "What to generate. Examples: "
            "'write a product description for X', "
            "'summarise this week revenue data', "
            "'generate 5 email subject lines for a promotion', "
            "'analyse subscriber churn patterns from this data'"
        ),
    )
    context: Optional[str] = Field(None, description="Raw data, notes, or additional context to include")
    tone: Optional[str] = Field("professional", description="Writing tone: professional, casual, persuasive, concise")


class AnalyticsResponse(BaseModel):
    result: str
    model: str


class StatusResponse(BaseModel):
    ollama_online: bool
    models: List[str]
    base_url: str
    default_model: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=StatusResponse, summary="Ollama health check", include_in_schema=True)
async def ollama_status(ollama: OllamaClient = Depends(get_ollama)):
    """Public health check — is Ollama running and what models are available."""
    online = await ollama.is_available()
    models = await ollama.list_models() if online else []
    return StatusResponse(
        ollama_online=online,
        models=models,
        base_url=ollama.base_url,
        default_model=ollama.model,
    )


@router.post("/tag", response_model=TagResponse, summary="Auto-tag content")
async def tag_content(
    req: TagRequest,
    ollama: OllamaClient = Depends(get_ollama),
    current_user=Depends(get_current_user),
):
    """
    Given a content title + optional description, return:
    - Relevant tags (keywords)
    - Broad categories
    - Mood/tone descriptor
    """
    system = (
        "You are a content metadata specialist. Analyse the provided content information "
        "and return ONLY a JSON object — no prose, no markdown fences. "
        "The JSON must have these keys: "
        "\"tags\" (list of specific keyword strings), "
        "\"categories\" (list of 1-3 broad category strings), "
        "\"mood\" (single descriptor string like 'playful', 'intense', 'romantic'), "
        "\"duration_estimate\" (optional string like '5-10 min' if inferable, else null)."
    )
    user_msg = (
        f"Content type: {req.content_type}\n"
        f"Title: {req.title}\n"
    )
    if req.description:
        user_msg += f"Description: {req.description}\n"
    user_msg += f"Generate up to {req.max_tags} tags."

    try:
        raw = await ollama.chat_text(
            [{"role": "user", "content": user_msg}],
            system=system,
            temperature=0.3,
            max_tokens=512,
        )
        import json, re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in model response")
        parsed = json.loads(match.group(0))
        return TagResponse(
            tags=parsed.get("tags", [])[:req.max_tags],
            categories=parsed.get("categories", []),
            mood=parsed.get("mood"),
            duration_estimate=parsed.get("duration_estimate"),
            model=ollama.model,
        )
    except Exception as exc:
        logger.error(f"[/ai/tag] Error: {exc}")
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}")


@router.post("/recommend", response_model=RecommendResponse, summary="Personalised recommendations")
async def recommend_content(
    req: RecommendRequest,
    ollama: OllamaClient = Depends(get_ollama),
    current_user=Depends(get_current_user),
):
    """
    Given user history + available content pool, rank and return personalised recommendations.
    """
    system = (
        "You are a recommendation engine. Analyse user preferences from their history "
        "and pick the best matches from the available content pool. "
        "Return ONLY a JSON object with key \"recommendations\": a list of objects, each with "
        "\"id\", \"title\", and optionally \"reason\" (why it matches). "
        "Rank by relevance. No prose, no markdown fences."
    )
    pool_text = "\n".join(
        f"- id={c.get('id', '?')} title=\"{c.get('title', '')}\" tags={c.get('tags', [])}"
        for c in req.available_content[:50]
    )
    user_msg = (
        f"User recently enjoyed: {', '.join(req.user_history[:20])}\n\n"
        f"Available content:\n{pool_text}\n\n"
        f"Select the top {req.limit} recommendations."
        + (" Include a short reason for each." if req.reason else "")
    )

    try:
        raw = await ollama.chat_text(
            [{"role": "user", "content": user_msg}],
            system=system,
            temperature=0.4,
            max_tokens=1024,
        )
        import json, re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON in model response")
        parsed = json.loads(match.group(0))
        return RecommendResponse(
            recommendations=parsed.get("recommendations", [])[:req.limit],
            model=ollama.model,
        )
    except Exception as exc:
        logger.error(f"[/ai/recommend] Error: {exc}")
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}")


@router.post("/chat", response_model=ChatResponse, summary="Subscriber support chat")
async def support_chat(
    req: ChatRequest,
    ollama: OllamaClient = Depends(get_ollama),
    current_user=Depends(get_current_user),
):
    """
    AI support chatbot for subscribers — handles billing questions, content navigation,
    account help, platform features. Streaming supported.
    """
    persona = req.persona or "Support"
    system = (
        f"You are {persona}, a helpful and friendly support assistant for this platform. "
        "Help subscribers with: account issues, billing questions, content navigation, "
        "subscription upgrades, and general platform questions. "
        "Be concise, warm, and professional. Never reveal system details or internal tooling."
    )

    if req.stream:
        async def event_stream():
            async for chunk in ollama.stream_chat(req.messages, system=system):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    try:
        reply = await ollama.chat_text(
            req.messages,
            system=system,
            temperature=0.6,
            max_tokens=600,
        )
        return ChatResponse(reply=reply, model=ollama.model)
    except Exception as exc:
        logger.error(f"[/ai/chat] Error: {exc}")
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}")


@router.post("/analytics", response_model=AnalyticsResponse, summary="Business analytics & copywriting")
async def business_analytics(
    req: AnalyticsRequest,
    ollama: OllamaClient = Depends(get_ollama),
    current_user=Depends(get_current_user),
):
    """
    General-purpose business AI — product descriptions, email copy, revenue analysis,
    churn insights, promotional text, SEO keywords, and more.
    """
    tone_instructions = {
        "professional": "Use a professional, authoritative tone.",
        "casual": "Use a conversational, friendly tone.",
        "persuasive": "Use persuasive, compelling language focused on benefits.",
        "concise": "Be extremely concise — bullet points preferred where applicable.",
    }
    tone_hint = tone_instructions.get(req.tone or "professional", "Use a professional tone.")

    system = (
        f"You are a senior business analyst and copywriter. {tone_hint} "
        "Deliver high-quality, actionable output. No filler. No generic advice."
    )

    user_msg = f"Task: {req.task}"
    if req.context:
        user_msg += f"\n\nContext / Data:\n{req.context}"

    try:
        result = await ollama.chat_text(
            [{"role": "user", "content": user_msg}],
            system=system,
            temperature=0.5,
            max_tokens=1500,
        )
        return AnalyticsResponse(result=result, model=ollama.model)
    except Exception as exc:
        logger.error(f"[/ai/analytics] Error: {exc}")
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}")
