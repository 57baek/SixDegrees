"""APScheduler setup for daily global compute.

SINGLE WORKER CONSTRAINT: always run `uvicorn app:app --reload`.
Multi-worker mode causes the job to fire N times per trigger.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config.settings as _settings
from services.map import diagnostics
from services.map import pipeline
from services.map.lock import acquire_lock, release_lock

logger = logging.getLogger(__name__)

_GLOBAL_COMPUTE_JOB_ID = "global_compute_daily_utc"
_UTC_HOUR = 2
_UTC_MINUTE = 0


async def _run_job() -> None:
    if not _settings.GLOBAL_COMPUTE_ENABLED:
        logger.info("Global compute skipped (GLOBAL_COMPUTE_ENABLED=False)")
        diagnostics.record_run(
            status="skipped",
            user_count=0,
            edge_count=0,
            duration_ms=0,
            error=None,
        )
        return
    if not acquire_lock():
        logger.info("Global compute skipped (lock already held)")
        return
    try:
        pipeline.run()
    finally:
        release_lock()


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_job,
        trigger=CronTrigger(hour=_UTC_HOUR, minute=_UTC_MINUTE, timezone="UTC"),
        id=_GLOBAL_COMPUTE_JOB_ID,
        replace_existing=True,
    )
    return scheduler
