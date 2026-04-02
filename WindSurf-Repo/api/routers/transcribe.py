"""Transcribe router."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from apps.api.schemas.transcribe import TranscribeRequest, TranscribeResponse
from db.models import Job, Asset, JobType, JobStatus
from apps.worker.tasks import transcribe_task
import json

router = APIRouter(prefix="/transcribe", tags=["transcribe"])


@router.post("", response_model=TranscribeResponse)
async def transcribe(
    http_request: Request,
    response: Response,
    request: TranscribeRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Queue a transcription job."""
    # Verify asset exists and belongs to workspace
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == request.asset_id,
            Asset.workspace_id == workspace_id,
        )
        .first()
    )
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Create job
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

    job = Job(
        workspace_id=workspace_id,
        job_type=JobType.TRANSCRIBE,
        status=JobStatus.PENDING,
        requested_provider=requested_provider,
        resolved_provider=resolved_provider,
        policy_id=getattr(http_request.state, "policy_id", None),
        policy_version=getattr(http_request.state, "policy_version", None),
        policy_enforcement=enforcement_mode,
        policy_reason=("ProviderNotAllowedFallbackApplied" if was_fallback else None),
        was_fallback=was_fallback,
        input_data=json.dumps(
            {
                "asset_id": request.asset_id,
                "language": request.language,
                "provider": resolved_provider,
                "requested_provider": requested_provider,
                "policy_id": getattr(http_request.state, "policy_id", None),
                "policy_version": getattr(http_request.state, "policy_version", None),
                "policy_enforcement": enforcement_mode,
                "was_fallback": was_fallback,
            }
        ),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue task
    transcribe_task.delay(job.id)

    return TranscribeResponse(
        job_id=job.id,
        status=job.status,
        message="Transcription job queued",
        requested_provider=requested_provider,
        resolved_provider=resolved_provider,
        policy_enforcement=("fallback" if was_fallback else enforcement_mode),
        was_fallback=was_fallback,
    )
