"""Workspace AI playground and Operating Reserve-backed completion endpoint."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from core.llm.circuit_breaker import is_open, record_failure, record_success
from core.llm.groq_fallback import GroqFallbackError, call_groq
from core.llm.ollama_client import OllamaError, _shared_ollama_client
from core.privacy.pii_detection import detect_and_mask_pii, detect_pii
from core.services.workspace_gateway import (
    get_model_setting,
    record_request_log,
)
from db.models import AIAuditLog, Subscription, SubscriptionStatus, TokenTransaction, TokenWallet, User
from db.session import get_db

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

RESERVE_UNITS_PER_USD = Decimal("1000")
FREE_EVALUATION_GOVERNED_RUNS = 15
FREE_EVALUATION_COMPARE_RUNS = 3

BillingEventType = Literal[
    "governed_run",
    "compare_run",
    "byok_governance_call",
    "managed_governance_call",
]


EVENT_PRICING_UNITS: dict[str, dict[str, int]] = {
    "governed_run": {
        "free_evaluation": 0,
        "founding": 250,   # $0.25
        "standard": 400,   # $0.40
        "regulated": 400,  # Default until an Order Form supplies custom pricing.
    },
    "compare_run": {
        "free_evaluation": 0,
        "founding": 750,    # $0.75
        "standard": 1200,   # $1.20
        "regulated": 1200,  # Default until an Order Form supplies custom pricing.
    },
    "byok_governance_call": {
        "free_evaluation": 0,
        "founding": 6,    # $6 / 1K
        "standard": 8,    # $8 / 1K
        "regulated": 10,  # $10 / 1K
    },
    "managed_governance_call": {
        "free_evaluation": 0,
        "founding": 12,   # $12 / 1K
        "standard": 16,   # $16 / 1K
        "regulated": 20,  # $20 / 1K
    },
}


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
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    top_k: Optional[int] = Field(default=None, ge=1, le=200)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(default=None, ge=-2, le=2)
    stream: bool = False
    response_format: Literal["text", "json", "json-schema"] = "text"
    seed: Optional[int] = Field(default=None, ge=0, le=2147483647)
    session_tag: Literal["Standard", "PHI", "PII", "HIPAA", "PCI", "SOC2"] = "Standard"
    billing_event_type: BillingEventType = "governed_run"
    auto_redact: bool = True
    sign_audit_on_export: bool = True
    lock_to_on_prem: bool = False

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
    reserve_units_debited: int
    tokens_deducted: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: str
    reserve_balance_units: int
    reserve_balance_usd: str
    wallet_balance: int
    reserve_debited: int
    billing_event_type: str
    pricing_tier: str
    free_evaluation_remaining: int | None = None
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


def _active_subscription(db: Session, workspace_id: str) -> Optional[Subscription]:
    return (
        db.query(Subscription)
        .filter(Subscription.workspace_id == workspace_id)
        .filter(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]))
        .first()
    )


def _pricing_tier(db: Session, workspace_id: str) -> str:
    sub = _active_subscription(db, workspace_id)
    if not sub:
        return "free_evaluation"

    plan = getattr(sub.plan, "value", str(sub.plan or "")).lower()
    if plan == "starter":
        return "founding"
    if plan == "pro":
        return "standard"
    if plan in {"sovereign", "enterprise"}:
        return "regulated"
    return "founding"


def _reserve_units_for_event(event_type: str, pricing_tier: str) -> int:
    return EVENT_PRICING_UNITS.get(event_type, EVENT_PRICING_UNITS["governed_run"]).get(pricing_tier, 0)


def _reserve_units_to_usd(units: int) -> Decimal:
    return (Decimal(units) / RESERVE_UNITS_PER_USD).quantize(Decimal("0.000001"))


def _free_usage_count(db: Session, workspace_id: str, event_type: str) -> int:
    rows = (
        db.query(TokenTransaction)
        .filter(TokenTransaction.workspace_id == workspace_id)
        .filter(TokenTransaction.transaction_type == "usage")
        .filter(TokenTransaction.endpoint_path == "/api/v1/ai/complete")
        .all()
    )
    count = 0
    marker = f'"billing_event_type": "{event_type}"'
    for row in rows:
        metadata = row.metadata_json or ""
        if '"pricing_tier": "free_evaluation"' in metadata and marker in metadata:
            count += 1
    return count


def _free_event_limit(event_type: str) -> int | None:
    if event_type == "governed_run":
        return FREE_EVALUATION_GOVERNED_RUNS
    if event_type == "compare_run":
        return FREE_EVALUATION_COMPARE_RUNS
    return None


def _enforce_free_quota(db: Session, workspace_id: str, event_type: str) -> int | None:
    limit = _free_event_limit(event_type)
    if limit is None:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This governed execution type requires an activated workspace and funded operating reserve.",
        )
    used = _free_usage_count(db, workspace_id, event_type)
    remaining = max(0, limit - used)
    if remaining <= 0:
        label = "governed runs" if event_type == "governed_run" else "compare runs"
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Free evaluation {label} exhausted. Activate the workspace and fund operating reserve.",
        )
    return remaining - 1


def _invalidate_wallet_cache(workspace_id: str) -> None:
    try:
        from core.redis_pool import get_redis

        get_redis().delete(f"wallet:balance:{workspace_id}")
    except Exception:
        pass


def _conversation_messages(payload: AICompleteRequest) -> list[AIMessage]:
    msgs = [AIMessage(role=msg.role, content=msg.content) for msg in payload.messages]
    if not msgs or msgs[-1].role != "user" or msgs[-1].content != payload.prompt:
        msgs.append(AIMessage(role="user", content=payload.prompt))
    return msgs[-40:]


def _compose_prompt(payload: AICompleteRequest) -> str:
    parts: list[str] = []
    if payload.system_prompt:
        parts.append(f"System:\n{_safe_log_text(payload.system_prompt, payload)}")
    for msg in _conversation_messages(payload):
        role = "User" if msg.role == "user" else "Assistant"
        parts.append(f"{role}:\n{_safe_log_text(msg.content, payload)}")
    parts.append("Assistant:")
    return "\n\n".join(parts).strip()


def _request_input_text(payload: AICompleteRequest) -> str:
    serialized = {
        "system_prompt": payload.system_prompt,
        "messages": [{"role": msg.role, "content": msg.content} for msg in _conversation_messages(payload)],
        "prompt": payload.prompt,
        "max_tokens": payload.max_tokens,
        "temperature": payload.temperature,
        "top_p": payload.top_p,
        "top_k": payload.top_k,
        "frequency_penalty": payload.frequency_penalty,
        "presence_penalty": payload.presence_penalty,
        "stream": payload.stream,
        "response_format": payload.response_format,
        "seed": payload.seed,
        "session_tag": payload.session_tag,
        "auto_redact": payload.auto_redact,
        "sign_audit_on_export": payload.sign_audit_on_export,
        "lock_to_on_prem": payload.lock_to_on_prem,
    }
    return json.dumps(serialized, sort_keys=True, ensure_ascii=False)


def _circuit_scope(model_row) -> str:
    workspace_id = getattr(model_row, "workspace_id", "workspace")
    model_slug = getattr(model_row, "model_slug", None) or getattr(model_row, "bedrock_model_id", "model")
    return f"{workspace_id}:{model_slug}"


def _protected_session(payload: AICompleteRequest) -> bool:
    return payload.session_tag in {"PHI", "HIPAA"}


def _effective_on_prem_lock(payload: AICompleteRequest) -> bool:
    return payload.lock_to_on_prem or _protected_session(payload)


def _ollama_options(payload: AICompleteRequest, temperature: float) -> dict:
    options = {"num_predict": payload.max_tokens, "temperature": temperature}
    if payload.top_p is not None:
        options["top_p"] = payload.top_p
    if payload.top_k is not None:
        options["top_k"] = payload.top_k
    if payload.seed is not None:
        options["seed"] = payload.seed
    if payload.frequency_penalty is not None:
        options["repeat_penalty"] = max(0.1, 1 + payload.frequency_penalty)
    return options


def _openai_messages(payload: AICompleteRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if payload.system_prompt:
        messages.append({"role": "system", "content": _safe_log_text(payload.system_prompt, payload)})
    for msg in _conversation_messages(payload):
        messages.append({"role": msg.role, "content": _safe_log_text(msg.content, payload)})
    return messages


def _safe_preview(text: str, payload: AICompleteRequest) -> tuple[str, list[dict[str, str]]]:
    detected = detect_pii(text)
    if payload.auto_redact or _protected_session(payload):
        masked, detected_masked = detect_and_mask_pii(text, "full")
        return masked[:500], detected_masked
    return text[:500], detected


def _safe_log_text(text: str, payload: AICompleteRequest) -> str:
    if payload.auto_redact or _protected_session(payload):
        masked, _ = detect_and_mask_pii(text, "full")
        return masked
    return text


def _governance_controls(payload: AICompleteRequest) -> dict:
    return {
        "session_tag": payload.session_tag,
        "auto_redact": payload.auto_redact or _protected_session(payload),
        "sign_audit_on_export": payload.sign_audit_on_export or _protected_session(payload),
        "lock_to_on_prem": _effective_on_prem_lock(payload),
        "response_format": payload.response_format,
        "stream_requested": payload.stream,
    }


def _openai_compatible_provider_config(provider: str) -> tuple[str, str, str]:
    if provider == "openai":
        return settings.openai_api_key, settings.openai_base_url.rstrip("/"), "OpenAI"
    if provider == "gemini":
        return settings.gemini_api_key, settings.gemini_base_url.rstrip("/"), "Gemini"
    raise ValueError(f"Unsupported OpenAI-compatible provider: {provider}")


def _call_runtime_model(
    model_row,
    payload: AICompleteRequest,
) -> tuple[dict, str, str]:
    prompt = _compose_prompt(payload)
    temperature = payload.temperature if payload.temperature is not None else 0.7
    if _effective_on_prem_lock(payload) and model_row.provider != "ollama":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="On-prem lock is enabled for this request. Select an Ollama/Hetzner runtime.",
        )
    if model_row.provider == "ollama":
        timeout_seconds = settings.llm_on_prem_timeout_seconds
        client = _shared_ollama_client(model=model_row.bedrock_model_id, timeout=timeout_seconds)
        circuit_scope = _circuit_scope(model_row)
        use_groq = is_open(circuit_scope)
        routing_reason = "circuit_open" if use_groq else "primary_runtime"
        if not use_groq:
            try:
                result = client.generate(
                    prompt=prompt,
                    model=model_row.bedrock_model_id,
                    options=_ollama_options(payload, temperature),
                )
                record_success(circuit_scope)
                return result, "ollama", "primary_runtime"
            except OllamaError as exc:
                reason_text = str(exc).lower()
                record_failure(circuit_scope)
                timed_out = "timed out" in reason_text or "timeout" in reason_text
                routing_reason = (
                    "ollama_latency_budget_exceeded"
                    if timed_out
                    else "ollama_unavailable"
                )
                use_groq = True

        if _effective_on_prem_lock(payload):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="On-prem lock is enabled and the Hetzner/Ollama runtime is unavailable.",
            )
        if settings.llm_fallback != "groq" or not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM unavailable: Ollama down and Groq fallback not configured.",
            )
        try:
            return call_groq(
                prompt=prompt,
                max_tokens=payload.max_tokens,
                temperature=temperature,
                top_p=payload.top_p,
                seed=payload.seed,
                timeout_seconds=settings.groq_timeout_seconds,
            ), "groq", routing_reason
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
                top_p=payload.top_p,
                seed=payload.seed,
                timeout_seconds=settings.groq_timeout_seconds,
            ), "groq", "primary_runtime"
        except GroqFallbackError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if model_row.provider in {"openai", "gemini"}:
        provider_key, base_url, provider_label = _openai_compatible_provider_config(model_row.provider)
        if not provider_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{provider_label} is not configured for this workspace runtime.",
            )
        openai_payload: dict = {
            "model": model_row.bedrock_model_id,
            "messages": _openai_messages(payload),
            "temperature": temperature,
            "max_tokens": payload.max_tokens,
        }
        if payload.top_p is not None:
            openai_payload["top_p"] = payload.top_p
        if payload.frequency_penalty is not None:
            openai_payload["frequency_penalty"] = payload.frequency_penalty
        if payload.presence_penalty is not None:
            openai_payload["presence_penalty"] = payload.presence_penalty
        if payload.seed is not None:
            openai_payload["seed"] = payload.seed
        if payload.response_format == "json":
            openai_payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
                response = client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {provider_key}",
                        "Content-Type": "application/json",
                    },
                    json=openai_payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                detail = f"{provider_label} authentication failed. Rotate or reconnect the provider key."
            elif status_code == 429:
                detail = f"{provider_label} rate limit or quota exceeded. Check provider billing, quota, or retry later."
            else:
                detail = f"{provider_label} request failed: HTTP {status_code}"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{provider_label} request failed: {str(exc)[:240]}",
            ) from exc

        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens))
        return {
            "response": (message.get("content") or "").strip(),
            "model": data.get("model") or model_row.bedrock_model_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }, model_row.provider, "primary_runtime"

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
        if payload.top_p is not None:
            inference_config["topP"] = payload.top_p
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
        }, "bedrock", "primary_runtime"

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Selected model provider is not available")


@router.post("/complete", response_model=AICompleteResponse)
async def complete(
    payload: AICompleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run a governed completion through the configured production LLM stack."""
    try:
        model_row = get_model_setting(db, current_user.workspace_id, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if not model_row.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Model disabled for this workspace")
    if not model_row.connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model is not connected")

    pricing_tier = _pricing_tier(db, current_user.workspace_id)
    billing_event_type = payload.billing_event_type
    reserve_units_debited = _reserve_units_for_event(billing_event_type, pricing_tier)
    free_evaluation_remaining = (
        _enforce_free_quota(db, current_user.workspace_id, billing_event_type)
        if pricing_tier == "free_evaluation"
        else None
    )
    wallet = _get_or_create_wallet(db, current_user.workspace_id)
    if reserve_units_debited > wallet.balance:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient operating reserve")

    request_id = getattr(request.state, "request_id", None) or f"ai-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    started_at = datetime.utcnow()
    try:
        llm_result, provider, runtime_routing_reason = _call_runtime_model(model_row, payload)
    except HTTPException:
        db.rollback()
        raise

    try:
        raw_response_text = (llm_result.get("response") or "").strip()
        response_text = _safe_log_text(raw_response_text, payload)
        executed_model = str(llm_result.get("model") or model_row.bedrock_model_id or payload.model)
        requested_provider = str(model_row.provider or "").lower()
        fallback_triggered = provider != requested_provider
        routing_reason = runtime_routing_reason if fallback_triggered else "primary_runtime"
        request_input_text = _request_input_text(payload)
        input_preview, input_pii = _safe_preview(payload.prompt, payload)
        output_preview, output_pii = _safe_preview(response_text, payload)
        pii_types = sorted({item["type"] for item in input_pii + output_pii if item.get("type")})
        pii_detected = bool(pii_types)
        governance_controls = _governance_controls(payload)
        prompt_tokens = int(llm_result.get("prompt_tokens") or 0)
        output_tokens = int(llm_result.get("completion_tokens") or 0)
        total_tokens = int(llm_result.get("total_tokens") or (prompt_tokens + output_tokens))
        cost_usd = _reserve_units_to_usd(reserve_units_debited)
        latency_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)

        balance_before = wallet.balance
        if reserve_units_debited > balance_before:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient operating reserve")

        previous_log = db.query(AIAuditLog).filter(
            AIAuditLog.workspace_id == current_user.workspace_id
        ).order_by(desc(AIAuditLog.created_at)).first()
        previous_log_hash = previous_log.log_hash if previous_log else None

        balance_after = balance_before - reserve_units_debited
        transaction = TokenTransaction(
            wallet_id=wallet.id,
            workspace_id=current_user.workspace_id,
            transaction_type="usage",
            amount=-reserve_units_debited,
            balance_before=balance_before,
            balance_after=balance_after,
            endpoint_path="/api/v1/ai/complete",
            endpoint_method="POST",
            request_id=request_id,
            description=f"{billing_event_type.replace('_', ' ').title()} via {provider.upper()} ({pricing_tier})",
            metadata_json=json.dumps(
                {
                    "provider": provider,
                    "model": executed_model,
                    "requested_model": payload.model,
                    "requested_provider": requested_provider,
                    "fallback_triggered": fallback_triggered,
                    "routing_reason": routing_reason,
                    "prompt_tokens": prompt_tokens,
                    "output_tokens": output_tokens,
                    "billing_event_type": billing_event_type,
                    "pricing_tier": pricing_tier,
                    "reserve_units_debited": reserve_units_debited,
                    "reserve_units_per_usd": int(RESERVE_UNITS_PER_USD),
                    "cost_usd": str(cost_usd),
                    "free_evaluation_remaining": free_evaluation_remaining,
                    "governance_controls": governance_controls,
                },
                sort_keys=True,
            ),
        )
        db.add(transaction)
        wallet.balance = balance_after
        wallet.monthly_credits_used = (wallet.monthly_credits_used or 0) + reserve_units_debited
        wallet.total_credits_used = (wallet.total_credits_used or 0) + reserve_units_debited
        wallet.updated_at = datetime.utcnow()

        audit_entry = AIAuditLog(
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            operation_type="ai.complete",
            provider=provider,
            model=executed_model,
            input_hash=_sha256(request_input_text),
            output_hash=_sha256(response_text),
            input_preview=input_preview,
            output_preview=output_preview,
            cost=cost_usd,
            tokens_input=prompt_tokens,
            tokens_output=output_tokens,
            routing_decision_id=None,
            routing_reasoning=routing_reason,
            pii_detected=pii_detected,
            pii_types=pii_types,
            sensitive_data_flags=governance_controls,
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
            prompt_preview=input_preview,
            response_preview=output_preview,
            request_json={
                "model": payload.model,
                "requested_provider": requested_provider,
                "resolved_model": executed_model,
                "prompt": _safe_log_text(payload.prompt, payload),
                "messages": [
                    {"role": msg.role, "content": _safe_log_text(msg.content, payload)}
                    for msg in _conversation_messages(payload)
                ],
                "system_prompt": _safe_log_text(payload.system_prompt, payload) if payload.system_prompt else None,
                "max_tokens": payload.max_tokens,
                "temperature": payload.temperature,
                "top_p": payload.top_p,
                "top_k": payload.top_k,
                "frequency_penalty": payload.frequency_penalty,
                "presence_penalty": payload.presence_penalty,
                "stream": payload.stream,
                "response_format": payload.response_format,
                "seed": payload.seed,
                "billing_event_type": billing_event_type,
                "pricing_tier": pricing_tier,
                "reserve_units_debited": reserve_units_debited,
                "governance_controls": governance_controls,
            },
            response_json={
                "response_text": _safe_log_text(response_text, payload),
                "runtime_model_id": executed_model,
                "provider": provider,
                "requested_provider": requested_provider,
                "requested_model": payload.model,
                "fallback_triggered": fallback_triggered,
                "routing_reason": routing_reason,
                "prompt_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "reserve_units_debited": reserve_units_debited,
                "reserve_debited": reserve_units_debited,
                "reserve_balance_units": wallet.balance,
                "reserve_balance_usd": str(_reserve_units_to_usd(wallet.balance)),
                "wallet_balance": wallet.balance,
                "billing_event_type": billing_event_type,
                "pricing_tier": pricing_tier,
                "free_evaluation_remaining": free_evaluation_remaining,
                "audit_hash": audit_entry.log_hash,
                "governance_controls": governance_controls,
                "pii_detected": pii_detected,
                "pii_types": pii_types,
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
        _invalidate_wallet_cache(current_user.workspace_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist AI completion audit for workspace %s", current_user.workspace_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI completion failed") from exc

    logger.info(
        "AI completion logged user_id=%s workspace_id=%s model=%s reserve_units_debited=%s timestamp=%s",
        current_user.id,
        current_user.workspace_id,
        executed_model,
        reserve_units_debited,
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
        reserve_units_debited=reserve_units_debited,
        tokens_deducted=reserve_units_debited,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        cost_usd=str(cost_usd),
        reserve_balance_units=wallet.balance,
        reserve_balance_usd=str(_reserve_units_to_usd(wallet.balance)),
        wallet_balance=wallet.balance,
        reserve_debited=reserve_units_debited,
        billing_event_type=billing_event_type,
        pricing_tier=pricing_tier,
        free_evaluation_remaining=free_evaluation_remaining,
        timestamp=started_at.isoformat(),
    )
