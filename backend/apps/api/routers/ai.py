"""Workspace AI playground and wallet-backed completion endpoint."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from core.llm.circuit_breaker import is_open, record_failure, record_success
from core.llm.groq_fallback import GroqFallbackError, call_groq
from core.llm.ollama_client import OllamaClient, OllamaError
from core.services.workspace_gateway import (
    TOKEN_USD_RATE,
    get_model_setting,
    record_request_log,
)
from db.models import AIAuditLog, TokenTransaction, TokenWallet, User
from db.session import get_db

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

class AIMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str = Field(min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def _content_must_have_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content cannot be empty")
        return value.strip()


class AICompleteRequest(BaseModel):
    model: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1, max_length=20000)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    messages: list[AIMessage] = Field(default_factory=list, max_length=40)
    system_prompt: Optional[str] = Field(default=None, max_length=12000)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)

    @field_validator("prompt")
    @classmethod
    def _prompt_must_have_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt cannot be empty")
        return value.strip()

    @field_validator("system_prompt")
    @classmethod
    def _normalize_system_prompt(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AICompleteResponse(BaseModel):
    response_text: str
    model: str
    bedrock_model_id: str
    provider: str
    requested_provider: str
    requested_model: str
    fallback_triggered: bool
    routing_reason: str
    request_id: str
    audit_log_id: str
    audit_hash: str
    prompt_tokens: int
    tokens_deducted: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: str
    wallet_balance: int
    timestamp: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_log_hash(
    *,
    log_id: str,
    workspace_id: str,
    user_id: str,
    operation_type: str,
    provider: str,
    model: Optional[str],
    input_hash: str,
    output_hash: str,
    cost: Decimal,
    created_at: datetime,
    previous_log_hash: Optional[str],
) -> str:
    log_data = {
        "id": log_id,
        "workspace_id": workspace_id,
        "user_id": user_id,
        "operation_type": operation_type,
        "provider": provider,
        "model": model,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "cost": str(cost),
        "created_at": created_at.isoformat() if created_at else None,
        "previous_log_hash": previous_log_hash,
    }
    digest = json.dumps(log_data, sort_keys=True)
    return hmac.new(settings.secret_key.encode("utf-8"), digest.encode("utf-8"), hashlib.sha256).hexdigest()


def _get_or_create_wallet(db: Session, workspace_id: str) -> TokenWallet:
    wallet = db.query(TokenWallet).filter(TokenWallet.workspace_id == workspace_id).with_for_update().first()
    if wallet:
        return wallet

    wallet = TokenWallet(workspace_id=workspace_id, balance=0)
    db.add(wallet)
    db.flush()
    return wallet


def _conversation_messages(payload: AICompleteRequest) -> list[AIMessage]:
    msgs = [AIMessage(role=msg.role, content=msg.content) for msg in payload.messages]
    if not msgs or msgs[-1].role != "user" or msgs[-1].content != payload.prompt:
        msgs.append(AIMessage(role="user", content=payload.prompt))
    return msgs[-40:]


def _compose_prompt(payload: AICompleteRequest) -> str:
    parts: list[str] = []
    if payload.system_prompt:
        parts.append(f"System:\n{payload.system_prompt}")
    for msg in _conversation_messages(payload):
        role = "User" if msg.role == "user" else "Assistant"
        parts.append(f"{role}:\n{msg.content}")
    parts.append("Assistant:")
    return "\n\n".join(parts).strip()


def _request_input_text(payload: AICompleteRequest) -> str:
    serialized = {
        "system_prompt": payload.system_prompt,
        "messages": [{"role": msg.role, "content": msg.content} for msg in _conversation_messages(payload)],
        "prompt": payload.prompt,
        "max_tokens": payload.max_tokens,
        "temperature": payload.temperature,
    }
    return json.dumps(serialized, sort_keys=True, ensure_ascii=False)


def _circuit_scope(model_row) -> str:
    workspace_id = getattr(model_row, "workspace_id", "workspace")
    model_slug = getattr(model_row, "model_slug", None) or getattr(model_row, "bedrock_model_id", "model")
    return f"{workspace_id}:{model_slug}"


def _call_runtime_model(
    model_row,
    payload: AICompleteRequest,
) -> tuple[dict, str]:
    prompt = _compose_prompt(payload)
    temperature = payload.temperature if payload.temperature is not None else 0.7
    if model_row.provider == "ollama":
        client = OllamaClient(model=model_row.bedrock_model_id)
        circuit_scope = _circuit_scope(model_row)
        use_groq = is_open(circuit_scope)
        if not use_groq:
            try:
                result = client.generate(
                    prompt=prompt,
                    model=model_row.bedrock_model_id,
                    options={"num_predict": payload.max_tokens, "temperature": temperature},
                )
                record_success(circuit_scope)
                return result, "ollama"
            except OllamaError:
                record_failure(circuit_scope)
                use_groq = True

        if settings.llm_fallback != "groq" or not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM unavailable: Ollama down and Groq fallback not configured.",
            )
        try:
            return call_groq(prompt=prompt, max_tokens=payload.max_tokens, temperature=temperature), "groq"
        except GroqFallbackError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Both Ollama and Groq unavailable: {exc}",
            ) from exc

    if model_row.provider == "groq":
        try:
            return call_groq(
                prompt=prompt,
                model=model_row.bedrock_model_id,
                max_tokens=payload.max_tokens,
                temperature=temperature,
            ), "groq"
        except GroqFallbackError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if model_row.provider == "bedrock":
        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AWS Bedrock is not configured for this workspace runtime.",
            )
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AWS Bedrock runtime dependency is not installed in this deployment.",
            ) from exc
        kwargs = {"region_name": settings.aws_default_region}
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            kwargs["aws_access_key_id"] = settings.aws_access_key_id
            kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        bedrock_messages = [
            {"role": msg.role, "content": [{"text": msg.content}]}
            for msg in _conversation_messages(payload)
        ]
        inference_config = {"maxTokens": payload.max_tokens, "temperature": temperature}
        converse_args = {
            "modelId": model_row.bedrock_model_id,
            "messages": bedrock_messages,
            "inferenceConfig": inference_config,
        }
        if payload.system_prompt:
            converse_args["system"] = [{"text": payload.system_prompt}]
        try:
            client = boto3.client("bedrock-runtime", **kwargs)
            response = client.converse(**converse_args)
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AWS Bedrock request failed: {str(exc)[:240]}",
            ) from exc

        response_text = "".join(
            item.get("text", "")
            for item in response.get("output", {}).get("message", {}).get("content", [])
            if isinstance(item, dict)
        ).strip()
        usage = response.get("usage", {}) or {}
        prompt_tokens = int(usage.get("inputTokens", 0) or 0)
        completion_tokens = int(usage.get("outputTokens", 0) or 0)
        total_tokens = int(usage.get("totalTokens", 0) or (prompt_tokens + completion_tokens))
        return {
            "response": response_text,
            "model": model_row.bedrock_model_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }, "bedrock"

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Selected model provider is not available")


@router.post("/complete", response_model=AICompleteResponse)
async def complete(
    payload: AICompleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run a wallet-backed completion through the configured production LLM stack."""
    try:
        model_row = get_model_setting(db, current_user.workspace_id, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if not model_row.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Model disabled for this workspace")
    if not model_row.connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model is not connected")
    reservation_tokens = max(1, math.ceil(payload.max_tokens / 100))

    wallet = _get_or_create_wallet(db, current_user.workspace_id)
    if wallet.balance < reservation_tokens:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient operating reserve")

    request_id = getattr(request.state, "request_id", None) or f"ai-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    started_at = datetime.utcnow()
    try:
        llm_result, provider = _call_runtime_model(model_row, payload)
    except HTTPException:
        db.rollback()
        raise

    try:
        response_text = (llm_result.get("response") or "").strip()
        executed_model = str(llm_result.get("model") or model_row.bedrock_model_id or payload.model)
        requested_provider = str(model_row.provider or "").lower()
        fallback_triggered = provider != requested_provider
        routing_reason = "circuit_breaker_failover" if fallback_triggered else "primary_runtime"
        request_input_text = _request_input_text(payload)
        prompt_tokens = int(llm_result.get("prompt_tokens") or 0)
        output_tokens = int(llm_result.get("completion_tokens") or 0)
        total_tokens = int(llm_result.get("total_tokens") or (prompt_tokens + output_tokens))
        tokens_deducted = math.ceil(output_tokens / 100) if output_tokens > 0 else 0
        cost_usd = (Decimal(tokens_deducted) * TOKEN_USD_RATE).quantize(Decimal("0.000001"))
        latency_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)

        balance_before = wallet.balance
        if tokens_deducted > balance_before:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient operating reserve")

        previous_log = db.query(AIAuditLog).filter(
            AIAuditLog.workspace_id == current_user.workspace_id
        ).order_by(desc(AIAuditLog.created_at)).first()
        previous_log_hash = previous_log.log_hash if previous_log else None

        if tokens_deducted > 0:
            transaction = TokenTransaction(
                wallet_id=wallet.id,
                workspace_id=current_user.workspace_id,
                transaction_type="usage",
                amount=-tokens_deducted,
                balance_before=balance_before,
                balance_after=balance_before - tokens_deducted,
                endpoint_path="/api/v1/ai/complete",
                endpoint_method="POST",
                request_id=request_id,
                description=f"{provider.upper()} AI completion via {payload.model}",
                metadata_json=json.dumps(
                    {
                        "provider": provider,
                        "model": executed_model,
                        "requested_model": payload.model,
                        "requested_provider": requested_provider,
                        "fallback_triggered": fallback_triggered,
                        "routing_reason": routing_reason,
                        "output_tokens": output_tokens,
                        "tokens_deducted": tokens_deducted,
                    },
                    sort_keys=True,
                ),
            )
            db.add(transaction)
            wallet.balance = balance_before - tokens_deducted
            wallet.monthly_credits_used = (wallet.monthly_credits_used or 0) + tokens_deducted
            wallet.total_credits_used = (wallet.total_credits_used or 0) + tokens_deducted
            wallet.updated_at = datetime.utcnow()

        audit_entry = AIAuditLog(
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            operation_type="ai.complete",
            provider=provider,
            model=executed_model,
            input_hash=_sha256(request_input_text),
            output_hash=_sha256(response_text),
            input_preview=payload.prompt[:500],
            output_preview=response_text[:500],
            cost=cost_usd,
            tokens_input=prompt_tokens,
            tokens_output=output_tokens,
            routing_decision_id=None,
            routing_reasoning=routing_reason,
            pii_detected=False,
            pii_types=[],
            sensitive_data_flags={},
            created_at=datetime.utcnow(),
            log_hash="",
            previous_log_hash=previous_log_hash,
        )
        db.add(audit_entry)
        db.flush()
        audit_entry.log_hash = _build_log_hash(
            log_id=audit_entry.id,
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            operation_type="ai.complete",
            provider=provider,
            model=executed_model,
            input_hash=audit_entry.input_hash,
            output_hash=audit_entry.output_hash,
            cost=cost_usd,
            created_at=audit_entry.created_at,
            previous_log_hash=previous_log_hash,
        )
        db.commit()
        record_request_log(
            db,
            workspace_id=current_user.workspace_id,
            request_kind="ai.complete",
            request_path="/api/v1/ai/complete",
            model=executed_model,
            provider=provider,
            status="success",
            prompt_preview=payload.prompt[:500],
            response_preview=response_text[:500],
            request_json={
                "model": payload.model,
                "requested_provider": requested_provider,
                "resolved_model": executed_model,
                "prompt": payload.prompt,
                "messages": [{"role": msg.role, "content": msg.content} for msg in _conversation_messages(payload)],
                "system_prompt": payload.system_prompt,
                "max_tokens": payload.max_tokens,
                "temperature": payload.temperature,
            },
            response_json={
                "response_text": response_text,
                "runtime_model_id": executed_model,
                "provider": provider,
                "requested_provider": requested_provider,
                "requested_model": payload.model,
                "fallback_triggered": fallback_triggered,
                "routing_reason": routing_reason,
                "prompt_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "tokens_deducted": tokens_deducted,
                "wallet_balance": wallet.balance,
                "audit_hash": audit_entry.log_hash,
            },
            tokens_in=prompt_tokens,
            tokens_out=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            source_table="ai_audit_logs",
            source_id=audit_entry.id,
            user_id=current_user.id,
            error_message=None,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist AI completion audit for workspace %s", current_user.workspace_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI completion failed") from exc

    logger.info(
        "AI completion logged user_id=%s workspace_id=%s model=%s tokens_deducted=%s timestamp=%s",
        current_user.id,
        current_user.workspace_id,
        executed_model,
        tokens_deducted,
        started_at.isoformat(),
    )

    return AICompleteResponse(
        response_text=response_text,
        model=executed_model,
        bedrock_model_id=executed_model,
        provider=provider,
        requested_provider=requested_provider,
        requested_model=payload.model,
        fallback_triggered=fallback_triggered,
        routing_reason=routing_reason,
        request_id=request_id,
        audit_log_id=str(audit_entry.id),
        audit_hash=audit_entry.log_hash,
        prompt_tokens=prompt_tokens,
        tokens_deducted=tokens_deducted,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        cost_usd=str(cost_usd),
        wallet_balance=wallet.balance,
        timestamp=started_at.isoformat(),
    )
