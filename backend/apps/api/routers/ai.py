"""Workspace AI playground and wallet-backed completion endpoint."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
from datetime import datetime
from decimal import Decimal
from typing import Optional

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

class AICompleteRequest(BaseModel):
    model: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1, max_length=20000)
    max_tokens: int = Field(default=512, ge=1, le=8192)

    @field_validator("prompt")
    @classmethod
    def _prompt_must_have_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt cannot be empty")
        return value.strip()


class AICompleteResponse(BaseModel):
    response_text: str
    model: str
    bedrock_model_id: str
    tokens_deducted: int
    output_tokens: int
    wallet_balance: int
    timestamp: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_log_hash(payload: dict, previous_log_hash: Optional[str]) -> str:
    envelope = {
        "payload": payload,
        "previous_log_hash": previous_log_hash,
    }
    digest = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    return hmac.new(settings.secret_key.encode("utf-8"), digest.encode("utf-8"), hashlib.sha256).hexdigest()


def _get_or_create_wallet(db: Session, workspace_id: str) -> TokenWallet:
    wallet = db.query(TokenWallet).filter(TokenWallet.workspace_id == workspace_id).with_for_update().first()
    if wallet:
        return wallet

    wallet = TokenWallet(workspace_id=workspace_id, balance=0)
    db.add(wallet)
    db.flush()
    return wallet


def _call_runtime_model(model_row, prompt: str, max_tokens: int) -> tuple[dict, str]:
    if model_row.provider == "ollama":
        client = OllamaClient(model=model_row.bedrock_model_id)
        use_groq = is_open()
        if not use_groq:
            try:
                result = client.generate(
                    prompt=prompt,
                    model=model_row.bedrock_model_id,
                    options={"num_predict": max_tokens},
                )
                record_success()
                return result, "ollama"
            except OllamaError:
                record_failure()
                use_groq = True

        if settings.llm_fallback != "groq" or not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM unavailable: Ollama down and Groq fallback not configured.",
            )
        try:
            return call_groq(prompt=prompt, max_tokens=max_tokens), "groq"
        except GroqFallbackError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Both Ollama and Groq unavailable: {exc}",
            ) from exc

    if model_row.provider == "groq":
        try:
            return call_groq(prompt=prompt, model=model_row.bedrock_model_id, max_tokens=max_tokens), "groq"
        except GroqFallbackError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Selected model provider is not available")


@router.post("/complete", response_model=AICompleteResponse)
async def complete(
    payload: AICompleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run a wallet-backed completion through the configured production LLM stack."""
    model_row = get_model_setting(db, current_user.workspace_id, payload.model)
    if not model_row.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Model disabled for this workspace")
    if not model_row.connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model is not connected")
    reservation_tokens = max(1, math.ceil(payload.max_tokens / 100))

    wallet = _get_or_create_wallet(db, current_user.workspace_id)
    if wallet.balance < reservation_tokens:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient tokens")

    request_id = getattr(request.state, "request_id", None) or f"ai-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    started_at = datetime.utcnow()
    try:
        llm_result, provider = _call_runtime_model(model_row, payload.prompt, payload.max_tokens)
    except HTTPException:
        db.rollback()
        raise

    try:
        response_text = (llm_result.get("response") or "").strip()
        output_tokens = int(llm_result.get("completion_tokens") or 0)
        tokens_deducted = math.ceil(output_tokens / 100) if output_tokens > 0 else 0
        cost_usd = (Decimal(tokens_deducted) * TOKEN_USD_RATE).quantize(Decimal("0.000001"))

        balance_before = wallet.balance
        if tokens_deducted > balance_before:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient tokens")

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
                        "model": payload.model,
                        "runtime_model_id": model_row.bedrock_model_id,
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

        audit_payload = {
            "user_id": current_user.id,
            "workspace_id": current_user.workspace_id,
            "model": payload.model,
            "runtime_model_id": model_row.bedrock_model_id,
            "tokens_deducted": tokens_deducted,
            "output_tokens": output_tokens,
            "timestamp": started_at.isoformat(),
            "request_id": request_id,
        }
        audit_entry = AIAuditLog(
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            operation_type="ai.complete",
            provider=provider,
            model=model_row.bedrock_model_id,
            input_hash=_sha256(payload.prompt),
            output_hash=_sha256(response_text),
            input_preview=payload.prompt[:500],
            output_preview=response_text[:500],
            cost=cost_usd,
            tokens_input=None,
            tokens_output=output_tokens,
            routing_decision_id=None,
            routing_reasoning=None,
            pii_detected=False,
            pii_types=[],
            sensitive_data_flags={},
            log_hash=_build_log_hash(audit_payload, previous_log_hash),
            previous_log_hash=previous_log_hash,
        )
        db.add(audit_entry)
        db.commit()
        record_request_log(
            db,
            workspace_id=current_user.workspace_id,
            request_kind="ai.complete",
            request_path="/api/v1/ai/complete",
            model=payload.model,
            provider=provider,
            status="success",
            prompt_preview=payload.prompt[:500],
            response_preview=response_text[:500],
            request_json={
                "model": payload.model,
                "prompt": payload.prompt,
                "max_tokens": payload.max_tokens,
            },
            response_json={
                "response_text": response_text,
                "runtime_model_id": model_row.bedrock_model_id,
                "output_tokens": output_tokens,
                "tokens_deducted": tokens_deducted,
                "wallet_balance": wallet.balance,
            },
            tokens_in=int(llm_result.get("prompt_tokens") or 0),
            tokens_out=output_tokens,
            latency_ms=int((datetime.utcnow() - started_at).total_seconds() * 1000),
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
        payload.model,
        tokens_deducted,
        started_at.isoformat(),
    )

    return AICompleteResponse(
        response_text=response_text,
        model=payload.model,
        bedrock_model_id=model_row.bedrock_model_id,
        tokens_deducted=tokens_deducted,
        output_tokens=output_tokens,
        wallet_balance=wallet.balance,
        timestamp=started_at.isoformat(),
    )
