"""Export task."""
from apps.worker.worker import celery_app
from db.session import SessionLocal
from db.models import Job, JobStatus, Export, ExportFormat, Asset, Transcript
from core.config import get_settings
from datetime import datetime
import json
import boto3
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.s3_access_key_id,
    aws_secret_access_key=settings.s3_secret_access_key,
    region_name=settings.s3_region,
    use_ssl=settings.s3_use_ssl,
)


@celery_app.task(
    name="export_task",
    bind=True,  # Enable task retry and idempotency checks
    max_retries=3,
    default_retry_delay=60,
)
def export_task(self, job_id: str):
    """Export task."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning(f"Job {job_id} not found")
            return
        
        # Idempotency check: if already completed or failed, don't retry
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            logger.info(f"Job {job_id} already {job.status.value}, skipping")
            return
        
        # Idempotency: Check if export already exists
        existing_export = db.query(Export).filter(
            Export.job_id == job_id
        ).first()
        if existing_export:
            logger.info(f"Export already exists for job {job_id}, skipping")
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()

        # Parse input
        input_data = json.loads(job.input_data or "{}")
        asset_ids = input_data.get("asset_ids", [])
        transcript_ids = input_data.get("transcript_ids", [])
        format_type = input_data.get("format", "json")
        include_metadata = input_data.get("include_metadata", True)

        # Build export data
        export_data = {}
        if asset_ids:
            assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
            export_data["assets"] = [
                {
                    "id": a.id,
                    "filename": a.filename,
                    "content_type": a.content_type,
                    "file_size": a.file_size,
                }
                for a in assets
            ]
        if transcript_ids:
            transcripts = db.query(Transcript).filter(Transcript.id.in_(transcript_ids)).all()
            export_data["transcripts"] = [
                {
                    "id": t.id,
                    "text": t.text,
                    "language": t.language,
                    "provider": t.provider,
                }
                for t in transcripts
            ]

        # Generate export file
        if format_type == "json":
            export_content = json.dumps(export_data, indent=2).encode("utf-8")
            content_type = "application/json"
        elif format_type == "csv":
            # Stub: implement CSV generation
            export_content = b"CSV placeholder"
            content_type = "text/csv"
        else:
            # ZIP stub
            export_content = b"ZIP placeholder"
            content_type = "application/zip"

        # Upload to S3
        s3_key = f"{job.workspace_id}/exports/{job.id}.{format_type}"
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=export_content,
            ContentType=content_type,
        )

        # Create export record
        export_record = Export(
            workspace_id=job.workspace_id,
            job_id=job.id,
            format=ExportFormat(format_type),
            s3_key=s3_key,
            s3_bucket=settings.s3_bucket_name,
            file_size=len(export_content),
        )
        db.add(export_record)

        # Update job
        job.status = JobStatus.COMPLETED
        job.output_data = json.dumps({"export_id": export_record.id, "s3_key": s3_key})
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error in export_task for job {job_id}: {e}", exc_info=True)
        if 'job' in locals() and job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        
        # Retry on transient errors (if task is bound)
        if 'self' in locals() and self and self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        logger.error(f"Job {job_id} failed after {self.max_retries if 'self' in locals() and self else 0} retries")
    finally:
        if 'db' in locals():
            db.close()
