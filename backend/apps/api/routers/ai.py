"""Amazon Bedrock AI playground and wallet-backed completion endpoint."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from db.models import AIAuditLog, TokenTransaction, TokenWallet, User
from db.session import get_db

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

MODEL_MAP = {
    "claude-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "llama3": "meta.llama3-8b-instruct-v1:0",
    "mistral": "mistral.mistral-7b-instruct-v0:2",
}


class AICompleteRequest(BaseModel):
    model: Literal["claude-haiku", "llama3", "mistral"]
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


def _resolve_model(model_slug: str) -> str:
    try:
        return MODEL_MAP[model_slug]
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported model") from exc


def _get_bedrock_client():
    client_kwargs = {}
    region = settings.aws_default_region or "us-east-1"
    if region:
        client_kwargs["region_name"] = region
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("bedrock-runtime", **client_kwargs)


def _get_or_create_wallet(db: Session, workspace_id: str) -> TokenWallet:
    wallet = db.query(TokenWallet).filter(TokenWallet.workspace_id == workspace_id).with_for_update().first()
    if wallet:
        return wallet

    wallet = TokenWallet(workspace_id=workspace_id, balance=0)
    db.add(wallet)
    db.flush()
    return wallet


@router.post("/complete", response_model=AICompleteResponse)
async def complete(
    payload: AICompleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run a wallet-backed Bedrock completion and record the audit trail."""
    model_id = _resolve_model(payload.model)
    reservation_tokens = max(1, math.ceil(payload.max_tokens / 100))

    wallet = _get_or_create_wallet(db, current_user.workspace_id)
    if wallet.balance < reservation_tokens:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient tokens")

    request_id = getattr(request.state, "request_id", None) or f"ai-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    client = _get_bedrock_client()
    started_at = datetime.utcnow()
    try:
        response = client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": payload.prompt,
                        }
                    ],
                }
            ],
            inferenceConfig={
                "maxTokens": payload.max_tokens,
            },
        )
    except (ClientError, BotoCoreError) as exc:
        db.rollback()
        logger.exception("Bedrock completion failed for workspace %s model %s", current_user.workspace_id, model_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bedrock request failed") from exc

    try:
        response_text = "".join(
            item.get("text", "")
            for item in response.get("output", {}).get("message", {}).get("content", [])
            if isinstance(item, dict)
        ).strip()
        usage = response.get("usage", {}) or {}
        output_tokens = int(usage.get("outputTokens") or 0)
        tokens_deducted = math.ceil(output_tokens / 100) if output_tokens > 0 else 0

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
                description=f"Bedrock AI completion via {payload.model}",
                metadata_json=json.dumps(
                    {
                        "provider": "bedrock",
                        "model": payload.model,
                        "bedrock_model_id": model_id,
                        "output_tokens": output_tokens,
                        "tokens_deducted": tokens_deducted,
                    },
                    sort_keys=True,
                ),
            )
            db.add(transaction)
            wallet.balance = balance_before - tokens_deducted
            wallet.total_credits_used = (wallet.total_credits_used or 0) + tokens_deducted
            wallet.updated_at = datetime.utcnow()

        audit_payload = {
            "user_id": current_user.id,
            "workspace_id": current_user.workspace_id,
            "model": payload.model,
            "bedrock_model_id": model_id,
            "tokens_deducted": tokens_deducted,
            "output_tokens": output_tokens,
            "timestamp": started_at.isoformat(),
            "request_id": request_id,
        }
        audit_entry = AIAuditLog(
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            operation_type="ai.complete",
            provider="bedrock",
            model=model_id,
            input_hash=_sha256(payload.prompt),
            output_hash=_sha256(response_text),
            input_preview=payload.prompt[:500],
            output_preview=response_text[:500],
            cost=Decimal(tokens_deducted),
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
        bedrock_model_id=model_id,
        tokens_deducted=tokens_deducted,
        output_tokens=output_tokens,
        wallet_balance=wallet.balance,
        timestamp=started_at.isoformat(),
    )
