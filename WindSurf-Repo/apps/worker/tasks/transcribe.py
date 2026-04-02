"""Transcription task."""

from apps.worker.worker import celery_app
from db.session import SessionLocal
from db.models import Job, JobStatus, Transcript, Asset
from db.models import RoutingPolicy
from core.config import get_settings
from datetime import datetime
import json
import logging
from core.providers.workspace_provider_factory import get_workspace_provider_factory

logger = logging.getLogger(__name__)
settings = get_settings()
provider_factory = get_workspace_provider_factory()


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
        requested_provider = (
            input_data.get("requested_provider") or input_data.get("provider") or "huggingface"
        )
        resolved_provider = input_data.get("provider") or requested_provider

        job.requested_provider = requested_provider
        job.resolved_provider = resolved_provider

        # Enforce workspace routing policy allowlist (worker doesn't get API middleware)
        try:
            policy = (
                db.query(RoutingPolicy)
                .filter(
                    RoutingPolicy.workspace_id == job.workspace_id,
                    RoutingPolicy.enabled == True,
                )
                .first()
            )
            if policy and policy.constraints_json:
                constraints = json.loads(policy.constraints_json)
                allowed = constraints.get("allowed_providers")
                enforcement_mode = constraints.get("enforcement_mode") or "strict"

                job.policy_id = policy.id
                job.policy_version = (
                    str(policy.version) if getattr(policy, "version", None) is not None else None
                )
                job.policy_enforcement = enforcement_mode

                if allowed and isinstance(allowed, list):
                    if requested_provider not in allowed:
                        if enforcement_mode == "fallback":
                            resolved_provider = allowed[0] if allowed else requested_provider
                            job.resolved_provider = resolved_provider
                            job.was_fallback = True
                            job.policy_reason = "ProviderNotAllowedFallbackApplied"
                        else:
                            job.status = JobStatus.FAILED
                            job.error_message = f"PROVIDER_NOT_ALLOWED: Provider '{requested_provider}' is not allowed by workspace policy"
                            job.resolved_provider = None
                            job.was_fallback = False
                            job.policy_reason = "PROVIDER_NOT_ALLOWED"
                            job.completed_at = datetime.utcnow()
                            db.commit()
                            return
        except Exception:
            # If policy can't be read/parsed, do not block transcription.
            pass

        provider_name = resolved_provider

        # Get asset
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            logger.error(f"Asset {asset_id} not found for job {job_id}")
            job.status = JobStatus.FAILED
            job.error_message = f"Asset {asset_id} not found"
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        # Get provider and transcribe (workspace BYOK supported)
        provider = provider_factory.get_stt_provider(db, job.workspace_id, provider_name)
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
        if "job" in locals() and job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()

        # Retry on transient errors (if task is bound)
        if "self" in locals() and self and self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        logger.error(
            f"Job {job_id} failed after {self.max_retries if 'self' in locals() and self else 0} retries"
        )
    finally:
        if "db" in locals():
            db.close()
