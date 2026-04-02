"""Transcription task."""
from apps.worker.worker import celery_app
from db.session import SessionLocal
from db.models import Job, JobStatus, Transcript, Asset
from apps.ai.providers import HuggingFaceProvider, LocalWhisperProvider, OpenAIOptionalProvider
from core.config import get_settings
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def get_stt_provider(provider_name: str):
    """Get STT provider instance."""
    if provider_name == "openai":
        return OpenAIOptionalProvider()
    elif provider_name == "local_whisper":
        return LocalWhisperProvider()
    else:
        return HuggingFaceProvider()  # Default


@celery_app.task(
    name="transcribe_task",
    bind=True,  # Enable task retry and idempotency checks
    max_retries=3,
    default_retry_delay=60,  # 1 minute
)
def transcribe_task(self, job_id: str):
    """
    Transcribe audio task.
    
    IDEMPOTENT: Safe to retry - checks job status before processing.
    If job already completed/failed, returns without re-processing.
    """
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

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()

        # Parse input
        input_data = json.loads(job.input_data or "{}")
        asset_id = input_data.get("asset_id")
        language = input_data.get("language")
        provider_name = input_data.get("provider", "huggingface")

        # Get asset
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        
        # Retry on transient errors
        if self and self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        logger.error(f"Job {job_id} failed after {self.max_retries if self else 0} retries: {e}")

        # Get provider and transcribe
        provider = get_stt_provider(provider_name)
        # Build audio URL from S3
        audio_url = f"{settings.s3_endpoint_url}/{asset.s3_bucket}/{asset.s3_key}"

        # Stub: actual async transcription
        # result = await provider.transcribe(audio_url, language)
        # For now, create placeholder transcript
        result_text = "Transcription placeholder - implement actual audio processing"

        # Save transcript
        transcript = Transcript(
            workspace_id=job.workspace_id,
            asset_id=asset_id,
            text=result_text,
            language=language or "en",
            provider=provider.get_name(),
        )
        db.add(transcript)

        # Update job
        job.status = JobStatus.COMPLETED
        job.output_data = json.dumps({"transcript_id": transcript.id})
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error in transcribe_task for job {job_id}: {e}", exc_info=True)
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
