"""Transcribe router."""
from fastapi import APIRouter, Depends, HTTPException, status
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
    request: TranscribeRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Queue a transcription job."""
    # Verify asset exists and belongs to workspace
    asset = db.query(Asset).filter(
        Asset.id == request.asset_id,
        Asset.workspace_id == workspace_id,
    ).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Create job
    job = Job(
        workspace_id=workspace_id,
        job_type=JobType.TRANSCRIBE,
        status=JobStatus.PENDING,
        input_data=json.dumps({
            "asset_id": request.asset_id,
            "language": request.language,
            "provider": request.provider or "huggingface",
        }),
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
    )
