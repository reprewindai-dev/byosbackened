"""HERALD scheduler lifecycle."""
from __future__ import annotations

import asyncio
import logging

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:  # pragma: no cover - dependency is optional for import safety
    BackgroundScheduler = None

from herald.resend_sequences import process_due_messages

logger = logging.getLogger(__name__)
_scheduler = None


def _run_due_messages() -> None:
    try:
        processed = asyncio.run(process_due_messages())
        if processed:
            logger.info("HERALD processed %s scheduled email(s)", processed)
    except Exception as exc:
        logger.warning("HERALD scheduled processing failed: %s", exc)


def start_herald_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    if BackgroundScheduler is None:
        logger.warning("HERALD scheduler disabled because APScheduler is unavailable")
        return
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _run_due_messages,
        trigger="interval",
        minutes=30,
        id="herald_due_messages",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("HERALD scheduler started")


def stop_herald_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("HERALD scheduler stopped")
