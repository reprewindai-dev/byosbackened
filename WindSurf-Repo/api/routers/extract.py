"""Extract router."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from apps.api.schemas.extract import ExtractRequest, ExtractResponse
from apps.ai.contracts import ChatMessage
from db.models import Asset, Transcript
from typing import Dict, Any
from core.providers.workspace_provider_factory import get_workspace_provider_factory

router = APIRouter(prefix="/extract", tags=["extract"])
provider_factory = get_workspace_provider_factory()


@router.post("", response_model=ExtractResponse)
async def extract(
    http_request: Request,
    response: Response,
    request: ExtractRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Extract hooks, summaries, timestamps, titles from text/transcript."""
    # Get text source
    text = None
    if request.text:
        text = request.text
    elif request.transcript_id:
        transcript = (
            db.query(Transcript)
            .filter(
                Transcript.id == request.transcript_id,
                Transcript.workspace_id == workspace_id,
            )
            .first()
        )
        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found",
            )
        text = transcript.text
    elif request.asset_id:
        # Get latest transcript for asset
        transcript = (
            db.query(Transcript)
            .filter(
                Transcript.asset_id == request.asset_id,
                Transcript.workspace_id == workspace_id,
            )
            .order_by(Transcript.created_at.desc())
            .first()
        )
        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No transcript found for asset",
            )
        text = transcript.text

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text source provided",
        )

    # Get provider with workspace policy enforcement
    requested_provider = request.provider or "huggingface"
    resolved_provider = requested_provider
    allowed = getattr(http_request.state, "allowed_providers", None)
    enforcement_mode = getattr(http_request.state, "policy_enforcement_mode", "strict")

    was_fallback = False
    if allowed and isinstance(allowed, list) and requested_provider not in allowed:
        if enforcement_mode == "fallback":
            resolved_provider = allowed[0] if allowed else requested_provider
            was_fallback = True
            response.headers["warning"] = "ProviderNotAllowedFallbackApplied"
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "PROVIDER_NOT_ALLOWED",
                    "message": f"Provider '{requested_provider}' is not allowed by workspace policy",
                    "allowed_providers": allowed,
                },
            )

    provider = provider_factory.get_llm_provider(db, workspace_id, resolved_provider)

    # Build prompt based on task
    prompt = _build_extract_prompt(request.task, text, request.options or {})

    # Call LLM (async)
    messages = [ChatMessage(role="user", content=prompt)]
    result = await provider.chat(messages, temperature=0.7)

    # Parse result (stub - implement actual parsing based on task)
    parsed_result = _parse_extract_result(request.task, result.content)

    return ExtractResponse(
        result=parsed_result,
        provider=provider.get_name(),
        model=result.model,
        requested_provider=requested_provider,
        resolved_provider=resolved_provider,
        policy_enforcement=("fallback" if was_fallback else enforcement_mode),
        was_fallback=was_fallback,
    )


def _build_extract_prompt(task: str, text: str, options: Dict[str, Any]) -> str:
    """Build extraction prompt."""
    if task == "hooks":
        return f"Extract 3-5 engaging hooks from this text:\n\n{text[:2000]}"
    elif task == "summary":
        return f"Summarize this text in 2-3 sentences:\n\n{text[:3000]}"
    elif task == "timestamps":
        return f"Extract key moments with timestamps from this transcript:\n\n{text[:5000]}"
    elif task == "titles":
        return f"Generate 5 title options for this content:\n\n{text[:2000]}"
    else:
        return f"Process this text for task '{task}':\n\n{text[:2000]}"


def _parse_extract_result(task: str, content: str) -> Dict[str, Any]:
    """Parse extraction result."""
    # Stub - implement actual parsing
    return {"task": task, "content": content, "raw": content}
