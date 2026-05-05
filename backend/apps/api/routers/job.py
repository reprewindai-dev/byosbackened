"""Job router."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from apps.api.schemas.job import JobResponse
from db.models import Job, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/process")
async def process_jobs(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Run a safe background queue maintenance pass for one workspace."""
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(hours=2)
    pending_count = (
        db.query(Job)
        .filter(Job.workspace_id == workspace_id, Job.status == JobStatus.PENDING)
        .count()
    )
    stale_jobs = (
        db.query(Job)
        .filter(
            Job.workspace_id == workspace_id,
            Job.status == JobStatus.RUNNING,
            Job.started_at.isnot(None),
            Job.started_at < stale_cutoff,
        )
        .all()
    )
    for job in stale_jobs:
        job.status = JobStatus.FAILED
        job.error_message = "Marked failed by scheduled queue maintenance after timeout."
        job.completed_at = now
        job.updated_at = now
    if stale_jobs:
        db.commit()
    return {
        "status": "ok",
        "workspace_id": workspace_id,
        "triggered_at": now.isoformat() + "Z",
        "pending_jobs": pending_count,
        "stale_running_jobs_closed": len(stale_jobs),
    }


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get job status."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.workspace_id == workspace_id,
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        input_data=job.input_data,
        output_data=job.output_data,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
