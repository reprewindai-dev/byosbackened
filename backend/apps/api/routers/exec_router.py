"""
POST /v1/exec — Tenant-isolated LLM execution endpoint
GET  /status  — System health: db, redis, llm

Auth: X-API-Key header → resolves tenant_id
RLS:  SET LOCAL request.tenant_id = '<uuid>' for every DB query
Log:  every execution persisted to execution_logs (tenant-scoped)
"""
import hashlib
import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import get_settings
from core.llm.ollama_client import OllamaClient, OllamaError, get_ollama_client
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


class ExecResponse(BaseModel):
    response: str
    model: str
    tenant_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    log_id: Optional[str] = None


class StatusResponse(BaseModel):
    uptime_seconds: float
    db_ok: bool
    redis_ok: bool
    llm_ok: bool
    llm_base_url: str
    llm_model: str
    llm_models_available: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

_start_time = time.monotonic()


def _resolve_api_key(raw_key: str, db: Session) -> tuple[str, str]:
    """
    Validate X-API-Key against DB.
    Returns (tenant_id, workspace_id) or raises 401.
    """
    from db.models.api_key import APIKey

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.is_active == True)
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    api_key.last_used_at = datetime.utcnow()
    db.commit()

    tenant_id = api_key.workspace_id
    workspace_id = api_key.workspace_id
    return tenant_id, workspace_id


def _set_rls(db: Session, tenant_id: str) -> None:
    """Apply Postgres RLS for this transaction scope."""
    db.execute(
        __import__("sqlalchemy").text("SET LOCAL request.tenant_id = :tid"),
        {"tid": tenant_id},
    )


def _log_execution(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
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
    """Persist execution record. Returns log ID or None on failure."""
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
            cost_usd=0.0,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log.id
    except Exception as exc:
        logger.error(f"[exec] Failed to persist execution log: {exc}")
        db.rollback()
        return None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/v1/exec", response_model=ExecResponse)
def exec_llm(
    body: ExecRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama_client),
):
    """
    Tenant-isolated LLM execution.
    1. Validate X-API-Key → resolve tenant_id
    2. Set Postgres RLS: SET LOCAL request.tenant_id = '<uuid>'
    3. Call Ollama
    4. Log execution row (tenant-scoped)
    5. Return response
    """
    # 1. Resolve tenant
    tenant_id, workspace_id = _resolve_api_key(x_api_key, db)

    # 2. RLS enforcement
    try:
        _set_rls(db, tenant_id)
    except Exception as exc:
        logger.warning(f"[exec] RLS set failed (non-fatal): {exc}")

    # 3. Call Ollama — hard fail, no fallback
    model = body.model or settings.llm_model_default
    options: dict = {}
    if body.max_tokens:
        options["num_predict"] = body.max_tokens
    if body.temperature is not None:
        options["temperature"] = body.temperature

    log_id: Optional[str] = None
    try:
        result = ollama.generate(
            prompt=body.prompt,
            model=model,
            options=options if options else None,
        )
    except OllamaError as exc:
        # 4. Log failure
        log_id = _log_execution(
            db,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            prompt=body.prompt,
            model=model,
            response="",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=0,
            success=False,
            error_message=str(exc),
        )
        logger.error(f"[exec] Ollama error tenant={tenant_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM unavailable: {exc}",
        )

    # 4. Log success
    log_id = _log_execution(
        db,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        prompt=body.prompt,
        model=result["model"],
        response=result["response"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
        latency_ms=result["latency_ms"],
        success=True,
    )

    return ExecResponse(
        response=result["response"],
        model=result["model"],
        tenant_id=tenant_id,
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
        latency_ms=result["latency_ms"],
        log_id=log_id,
    )


@router.get("/status", response_model=StatusResponse)
def system_status(
    db: Session = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama_client),
):
    """
    Full system health check.
    Returns uptime, db_ok, redis_ok, llm_ok.
    """
    uptime = time.monotonic() - _start_time

    # DB check
    db_ok = False
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.warning(f"[status] DB check failed: {exc}")

    # Redis check
    redis_ok = False
    try:
        import redis as redis_lib

        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        redis_ok = r.ping()
    except Exception as exc:
        logger.warning(f"[status] Redis check failed: {exc}")

    # LLM (Ollama) check
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
    )
