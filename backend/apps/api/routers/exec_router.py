"""
POST /v1/exec — Tenant-isolated LLM execution with self-healing circuit breaker
GET  /status  — System health: db, redis, llm, circuit_breaker

Self-healing flow:
  Ollama healthy  → CLOSED  → serve from local qwen2.5:3b
  Ollama fails ×N → OPEN    → auto-route to Groq fallback
  cooldown passes → HALF-OPEN → probe Ollama; close on success

Self-memory:
  conversation_id in request → Redis context injected before prompt
  response saved back to Redis (24h TTL, 20-message window per tenant)
"""
import hashlib
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Optional

import sqlalchemy
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import get_settings
from core.llm.circuit_breaker import record_failure, record_success, is_open, status_dict as cb_status
from core.llm.groq_fallback import call_groq, GroqFallbackError
from core.llm.ollama_client import OllamaClient, OllamaError, get_ollama_client
from core.memory.conversation import get_memory
from core.services.workspace_gateway import TOKEN_USD_RATE, record_request_log
from db.session import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["exec"])

# ── Schemas ───────────────────────────────────────────────────────────────────


class ExecRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32_000)
    model: Optional[str] = Field(None, description="Override default model")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    stream: bool = Field(False, description="Streaming not yet supported — ignored")
    conversation_id: Optional[str] = Field(
        None, description="Persist + resume conversation context (Redis, 24h TTL)"
    )
    use_memory: bool = Field(True, description="Inject conversation history into prompt")


class ExecResponse(BaseModel):
    response: str
    model: str
    provider: str  # "ollama" | "groq"
    tenant_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    conversation_id: Optional[str] = None
    log_id: Optional[str] = None


class StatusResponse(BaseModel):
    uptime_seconds: float
    db_ok: bool
    redis_ok: bool
    llm_ok: bool
    llm_base_url: str
    llm_model: str
    llm_models_available: list[str]
    groq_fallback_enabled: bool
    circuit_breaker: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

_start_time = time.monotonic()


def _resolve_api_key(raw_key: str, db: Session):
    """Validate X-API-Key → returns (tenant_id, workspace_id) or raises 401."""
    from db.models.api_key import APIKey

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.is_active == True)  # noqa: E712
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    api_key.last_used_at = datetime.utcnow()
    db.commit()
    return api_key


def _set_rls(db: Session, tenant_id: str) -> None:
    """Apply Postgres RLS for this transaction scope."""
    db.execute(sqlalchemy.text("SET LOCAL request.tenant_id = :tid"), {"tid": tenant_id})


def _log_execution(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    api_key_id: Optional[str],
    api_key_prefix: Optional[str],
    prompt: str,
    model: str,
    response: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: int,
    success: bool,
    error_message: Optional[str] = None,
) -> Optional[str]:
    """Persist execution record to DB. Returns log ID or None on failure."""
    try:
        from db.models.execution_log import ExecutionLog

        log = ExecutionLog(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            prompt=prompt[:4000],
            model=model,
            response=response[:8000] if response else None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            cost_usd=float(Decimal(total_tokens or 0) * TOKEN_USD_RATE),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return str(log.id)
    except Exception as exc:
        logger.error("[exec] Failed to persist execution log: %s", exc)
        db.rollback()
        return None


def _call_with_circuit_breaker(
    ollama: OllamaClient,
    prompt: str,
    model: str,
    options: dict,
    scope: str,
) -> tuple[dict, str, str]:
    """
    Try Ollama first, respecting circuit breaker state.
    Falls back to Groq if circuit is OPEN or Ollama fails.
    Returns (result_dict, provider_name, routing_reason).
    """
    use_groq = is_open(scope)
    routing_reason = "circuit_open" if use_groq else "primary_runtime"

    if not use_groq:
        try:
            fast_ollama = (
                OllamaClient(base_url=ollama.base_url, model=model, timeout=settings.llm_latency_budget_seconds)
                if isinstance(getattr(ollama, "base_url", None), str)
                else ollama
            )
            result = fast_ollama.generate(prompt=prompt, model=model, options=options or None)
            record_success(scope)
            return result, "ollama", "primary_runtime"
        except OllamaError as exc:
            new_state = record_failure(scope)
            logger.warning("[CB] Ollama failed (%s), state now %s", exc, new_state)
            text = str(exc).lower()
            routing_reason = "ollama_latency_budget_exceeded" if "timed out" in text or "timeout" in text else "ollama_unavailable"
            use_groq = True

    # ── Groq fallback path ────────────────────────────────────────────────────
    if use_groq:
        if settings.llm_fallback != "groq" or not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM unavailable: Ollama down and Groq fallback not configured.",
            )
        try:
            result = call_groq(
                prompt=prompt,
                max_tokens=options.get("num_predict"),
                temperature=options.get("temperature"),
                timeout_seconds=settings.groq_timeout_seconds,
            )
            return result, "groq", routing_reason
        except GroqFallbackError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Both Ollama and Groq unavailable: {exc}",
            ) from exc

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM unavailable")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/v1/exec", response_model=ExecResponse)
def exec_llm(
    body: ExecRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama_client),
):
    """
    Tenant-isolated LLM execution — self-healing + self-memory.

    1. Validate X-API-Key → resolve tenant_id
    2. Load conversation history from Redis (if conversation_id provided)
    3. Inject context into prompt
    4. Call Ollama via circuit breaker; auto-fall to Groq if circuit is OPEN
    5. Save exchange to conversation memory
    6. Log execution to DB (tenant-scoped RLS)
    7. Return response + provider info
    """
    # 1. Resolve tenant
    api_key = _resolve_api_key(x_api_key, db)
    tenant_id = api_key.workspace_id
    workspace_id = api_key.workspace_id

    # 2. RLS enforcement
    try:
        _set_rls(db, tenant_id)
    except Exception as exc:
        logger.warning("[exec] RLS set failed (non-fatal): %s", exc)

    # 3. Build prompt with conversation memory
    effective_prompt = body.prompt
    mem = None
    if body.conversation_id and body.use_memory:
        mem = get_memory(tenant_id, body.conversation_id)
        context = mem.build_context_prompt()
        if context:
            effective_prompt = f"{context}\nUser: {body.prompt}"

    # 4. Prepare model options
    model = body.model or settings.llm_model_default
    options: dict = {}
    if body.max_tokens:
        options["num_predict"] = body.max_tokens
    if body.temperature is not None:
        options["temperature"] = body.temperature

    # 5. Call LLM (Ollama → Groq via circuit breaker)
    started = time.perf_counter()
    circuit_scope = f"{workspace_id}:v1_exec:{model}"
    result, provider, routing_reason = _call_with_circuit_breaker(ollama, effective_prompt, model, options, circuit_scope)
    latency_ms = int((time.perf_counter() - started) * 1000) or result["latency_ms"]
    fallback_triggered = provider != "ollama"

    # 6. Persist conversation turn
    if mem is not None:
        mem.add("user", body.prompt)
        mem.add("assistant", result["response"])

    # 7. Log execution
    log_id = _log_execution(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        api_key_id=api_key.id,
        api_key_prefix=api_key.key_prefix,
        prompt=effective_prompt,
        model=result["model"],
        response=result["response"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
        latency_ms=latency_ms,
        success=True,
    )

    record_request_log(
        db,
        workspace_id=workspace_id,
        request_kind="exec",
        request_path="/v1/exec",
        model=result["model"],
        provider=provider,
        status="success",
        prompt_preview=effective_prompt[:500],
        response_preview=result["response"][:500],
        request_json={
            "prompt": body.prompt,
            "model": body.model,
            "requested_provider": "ollama",
            "conversation_id": body.conversation_id,
            "use_memory": body.use_memory,
            "temperature": body.temperature,
            "max_tokens": body.max_tokens,
        },
        response_json={
            "response": result["response"],
            "provider": provider,
            "requested_provider": "ollama",
            "fallback_triggered": fallback_triggered,
            "routing_reason": routing_reason if fallback_triggered else "primary_runtime",
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
        },
        tokens_in=result["prompt_tokens"],
        tokens_out=result["completion_tokens"],
        latency_ms=latency_ms,
        cost_usd=(Decimal(result["total_tokens"] or 0) * TOKEN_USD_RATE).quantize(Decimal("0.000001")),
        source_table="execution_logs",
        source_id=log_id or f"exec-{int(time.time() * 1000)}",
        user_id=None,
        api_key_id=api_key.id,
    )

    return ExecResponse(
        response=result["response"],
        model=result["model"],
        provider=provider,
        tenant_id=tenant_id,
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
        latency_ms=latency_ms,
        conversation_id=body.conversation_id,
        log_id=log_id,
    )


@router.get("/status", response_model=StatusResponse)
def system_status(
    db: Session = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama_client),
):
    """
    Full system health check — DB, Redis, Ollama, circuit breaker state.
    """
    uptime = time.monotonic() - _start_time

    # DB
    db_ok = False
    try:
        db.execute(sqlalchemy.text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.warning("[status] DB check failed: %s", exc)

    # Redis
    redis_ok = False
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        redis_ok = bool(r.ping())
    except Exception as exc:
        logger.warning("[status] Redis check failed: %s", exc)

    # Ollama
    llm_ok = ollama.health_check()
    models_available = ollama.list_models() if llm_ok else []

    return StatusResponse(
        uptime_seconds=round(uptime, 2),
        db_ok=db_ok,
        redis_ok=redis_ok,
        llm_ok=llm_ok,
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model_default,
        llm_models_available=models_available,
        groq_fallback_enabled=bool(settings.groq_api_key and settings.llm_fallback == "groq"),
        circuit_breaker=cb_status(),
    )
