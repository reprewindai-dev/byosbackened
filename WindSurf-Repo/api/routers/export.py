"""Export router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from apps.api.schemas.export import ExportRequest, ExportResponse
from db.models import Job, JobType, JobStatus
from apps.worker.tasks import export_task
import json

router = APIRouter(prefix="/export", tags=["export"])


@router.post("", response_model=ExportResponse)
async def export(
    request: ExportRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Queue an export job."""
    # Create job
    job = Job(
        workspace_id=workspace_id,
        job_type=JobType.EXPORT,
        status=JobStatus.PENDING,
        input_data=json.dumps(
            {
                "asset_ids": request.asset_ids or [],
                "transcript_ids": request.transcript_ids or [],
                "format": request.format,
                "include_metadata": request.include_metadata,
            }
        ),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue task
    export_task.delay(job.id)

    return ExportResponse(
        job_id=job.id,
        status=job.status,
        message="Export job queued",
    )
