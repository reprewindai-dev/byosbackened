"""Extract router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from apps.api.schemas.extract import ExtractRequest, ExtractResponse
from apps.ai.providers import HuggingFaceProvider, LocalLLMProvider, OpenAIOptionalProvider
from apps.ai.contracts import ChatMessage
from db.models import Asset, Transcript
from typing import Dict, Any

router = APIRouter(prefix="/extract", tags=["extract"])


def get_llm_provider(provider_name: str):
    """Get LLM provider instance."""
    if provider_name == "openai":
        return OpenAIOptionalProvider()
    elif provider_name == "local_llm":
        return LocalLLMProvider()
    else:
        return HuggingFaceProvider()  # Default


@router.post("", response_model=ExtractResponse)
async def extract(
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
        transcript = db.query(Transcript).filter(
            Transcript.id == request.transcript_id,
            Transcript.workspace_id == workspace_id,
        ).first()
        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found",
            )
        text = transcript.text
    elif request.asset_id:
        # Get latest transcript for asset
        transcript = db.query(Transcript).filter(
            Transcript.asset_id == request.asset_id,
            Transcript.workspace_id == workspace_id,
        ).order_by(Transcript.created_at.desc()).first()
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

    # Get provider
    provider_name = request.provider or "huggingface"
    provider = get_llm_provider(provider_name)

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
