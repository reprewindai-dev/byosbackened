"""Celery task for training ML models."""

from apps.worker.worker import celery_app
from core.autonomous.training.pipeline import get_training_pipeline
import logging

logger = logging.getLogger(__name__)
training_pipeline = get_training_pipeline()


@celery_app.task(name="train_models_all_workspaces")
def train_models_all_workspaces(min_samples: int = 100):
    """
    Train ML models for all workspaces.

    This runs weekly/monthly via cron to keep models up-to-date.
    This is what makes the system "get better over time."
    """
    logger.info(f"Starting model training for all workspaces (min_samples={min_samples})")

    results = training_pipeline.train_all_workspaces(min_samples=min_samples)

    logger.info(
        f"Training complete: {len(results['trained'])} trained, "
        f"{len(results['skipped'])} skipped, {len(results['errors'])} errors"
    )

    return results
