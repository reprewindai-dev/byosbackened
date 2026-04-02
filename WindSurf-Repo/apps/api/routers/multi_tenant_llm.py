"""Multi-tenant LLM execution router with async Ollama integration."""

from datetime import datetime
from typing import List, Optional, Dict, Any
import time
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from apps.api.tenant_auth import get_tenant_info, get_tenant_from_api_key
from apps.ai.contracts import ChatMessage, ChatResult
from ai.providers.local_llm import LocalLLMProvider
from core.cache.redis_cache import cache_service
from core.config import get_settings
from db.session import get_db
from db.models.tenant import Execution
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/llm", tags=["multi-tenant-llm"])


class ChatCompletionRequest(BaseModel):
    """Chat completion request for multi-tenant execution."""
    
    messages: List[Dict[str, str]] = Field(..., min_items=1)
    model: str = Field(default="llama3.1", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: bool = Field(default=False, description="Enable streaming response")
    tenant_metadata: Optional[Dict[str, Any]] = Field(default=None)


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""
    
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    tenant_id: str


class ModelInfo(BaseModel):
    """Model information response."""
    
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelsResponse(BaseModel):
    """Available models response."""
    
    object: str = "list"
    data: List[ModelInfo]


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    tenant_id: str = Depends(get_tenant_from_api_key),
    tenant_info: dict = Depends(get_tenant_info),
    db: Session = Depends(get_db),
):
    """Execute chat completion with tenant isolation and rate limiting."""
    
    # Check tenant limits
    if tenant_info["daily_execution_count"] >= tenant_info["execution_limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily execution limit exceeded"
        )
    
    # Rate limiting check
    rate_limit_key = f"tenant:{tenant_id}:rate_limit"
    current_requests = await cache_service.get(rate_limit_key) or 0
    
    if current_requests >= 10:  # 10 requests per minute
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Increment rate limit counter
    await cache_service.set(rate_limit_key, current_requests + 1, ttl=60)
    
    # Convert messages to ChatMessage format
    chat_messages = []
    for msg in request.messages:
        if msg.get("role") and msg.get("content"):
            chat_messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
    
    if not chat_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid message required"
        )
    
    # Initialize LLM provider
    llm_provider = LocalLLMProvider()
    
    # Check cache for similar requests
    cache_key = f"tenant:{tenant_id}:chat:{hash(json.dumps([
        {"role": m.role, "content": m.content} for m in chat_messages
    ]))}"
    
    cached_response = await cache_service.get(cache_key)
    if cached_response and not request.stream:
        logger.info(f"Cache hit for tenant {tenant_id}")
        return ChatCompletionResponse(**cached_response)
    
    # Execute request
    start_time = time.time()
    
    try:
        result: ChatResult = await llm_provider.chat(
            messages=chat_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Create execution record
        execution = Execution(
            tenant_id=tenant_id,
            prompt=json.dumps([{"role": m.role, "content": m.content} for m in chat_messages]),
            response=result.content,
            model=result.model or request.model,
            tokens_generated=len(result.content.split()),  # Rough estimate
            execution_time_ms=execution_time_ms,
            created_at=datetime.utcnow(),
        )
        
        db.add(execution)
        
        # Update tenant execution count
        db.execute(
            text("UPDATE tenants SET daily_execution_count = daily_execution_count + 1 WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        
        db.commit()
        
        # Build response
        response_data = {
            "id": f"chatcmpl-{execution.execution_id.hex[:8]}",
            "created": int(datetime.utcnow().timestamp()),
            "model": result.model or request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.content,
                },
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": len(chat_messages),
                "completion_tokens": len(result.content.split()),
                "total_tokens": len(chat_messages) + len(result.content.split()),
            },
            "tenant_id": tenant_id,
        }
        
        # Cache response
        if not request.stream:
            await cache_service.set(cache_key, response_data, ttl=300)  # 5 minutes
        
        logger.info(f"Execution completed for tenant {tenant_id} in {execution_time_ms}ms")
        
        return ChatCompletionResponse(**response_data)
        
    except Exception as e:
        logger.error(f"LLM execution failed for tenant {tenant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM execution failed"
        )


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    tenant_id: str = Depends(get_tenant_from_api_key),
):
    """List available models for tenant."""
    
    # Cache model list
    cache_key = "available_models"
    cached_models = await cache_service.get(cache_key)
    
    if cached_models:
        return ModelsResponse(**cached_models)
    
    # Default models for local LLM
    models = [
        ModelInfo(
            id="llama3.1",
            created=int(datetime.utcnow().timestamp()),
            owned_by="local"
        ),
        ModelInfo(
            id="llama3.1:8b",
            created=int(datetime.utcnow().timestamp()),
            owned_by="local"
        ),
        ModelInfo(
            id="qwen2.5:7b",
            created=int(datetime.utcnow().timestamp()),
            owned_by="local"
        ),
    ]
    
    response_data = {
        "object": "list",
        "data": [model.dict() for model in models]
    }
    
    # Cache for 1 hour
    await cache_service.set(cache_key, response_data, ttl=3600)
    
    return ModelsResponse(**response_data)


@router.get("/executions")
async def list_executions(
    limit: int = Field(default=50, ge=1, le=100),
    offset: int = Field(default=0, ge=0),
    tenant_id: str = Depends(get_tenant_from_api_key),
    db: Session = Depends(get_db),
):
    """List tenant's execution history."""
    
    executions = db.query(Execution).filter(
        Execution.tenant_id == tenant_id
    ).order_by(
        Execution.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "object": "list",
        "data": [
            {
                "id": str(exec.execution_id),
                "tenant_id": str(exec.tenant_id),
                "model": exec.model,
                "tokens_generated": exec.tokens_generated,
                "execution_time_ms": exec.execution_time_ms,
                "created_at": exec.created_at.isoformat(),
                "prompt_preview": exec.prompt[:200] + "..." if len(exec.prompt) > 200 else exec.prompt,
            }
            for exec in executions
        ],
        "total": len(executions),
        "tenant_id": tenant_id,
    }


@router.get("/status")
async def get_tenant_status(
    tenant_info: dict = Depends(get_tenant_info),
):
    """Get current tenant status and usage."""
    
    return {
        "tenant_id": tenant_info["tenant_id"],
        "name": tenant_info["name"],
        "is_active": tenant_info["is_active"],
        "execution_limit": tenant_info["execution_limit"],
        "daily_execution_count": tenant_info["daily_execution_count"],
        "remaining_executions": max(0, tenant_info["execution_limit"] - tenant_info["daily_execution_count"]),
        "usage_percentage": (tenant_info["daily_execution_count"] / tenant_info["execution_limit"]) * 100 if tenant_info["execution_limit"] > 0 else 0,
    }
