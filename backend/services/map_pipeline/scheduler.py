"""APScheduler setup for timezone-grouped daily pipeline runs.

SINGLE WORKER CONSTRAINT:
    APScheduler runs in-process. If uvicorn is started with multiple workers
    (e.g., --workers 2), each worker process gets its own scheduler instance,
    causing each pipeline job to fire N times per trigger.

    ALWAYS run with:
        uvicorn app:app --reload
    NEVER use:
        uvicorn app:app --workers 2  (or any N > 1)

    This is a known limitation for this milestone. A persistent job store
    (e.g., APScheduler SQLAlchemyJobStore) would be required for multi-worker
    safety but is out of scope.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config.supabase import get_supabase_client
from services.map_pipeline import run_pipeline_for_user

logger = logging.getLogger(__name__)


def _run_pipeline_for_timezone(timezone: str) -> None:
    """Fetch all users in this timezone and run the pipeline for each.

    Each user's pipeline is wrapped in try/except so that one failure does not
    abort the rest of the batch. Errors are logged at ERROR level.
    """
    sb = get_supabase_client()
    rows = sb.rpc("get_profiles_by_timezone", {"p_timezone": timezone}).execute().data
    logger.info("Scheduler: running pipeline for %d users in timezone %s", len(rows), timezone)
    for row in rows:
        try:
            run_pipeline_for_user(row["id"])
            logger.info("Scheduler: pipeline complete for user %s", row["id"])
        except Exception as exc:
            logger.error(
                "Scheduler: pipeline FAILED for user %s in timezone %s: %s",
                row["id"],
                timezone,
                exc,
            )


def setup_scheduler() -> AsyncIOScheduler:
    """Query profiles for unique timezones and register one CronTrigger each.

    Timezones are queried once at startup. New timezones added after startup
    require an app restart to be picked up. Users in already-registered timezones
    are always picked up at fire time (the job re-queries by timezone).

    Returns:
        Configured but not-yet-started AsyncIOScheduler (MemoryJobStore default).
    """
    scheduler = AsyncIOScheduler()

    sb = get_supabase_client()
    rows = sb.rpc("get_distinct_timezones", {}).execute().data

    unique_timezones = {row["timezone"] for row in rows if row.get("timezone")}
    logger.info("Scheduler: found %d unique timezone(s) to register", len(unique_timezones))

    for tz in unique_timezones:
        try:
            scheduler.add_job(
                _run_pipeline_for_timezone,
                trigger=CronTrigger(hour=19, minute=0, timezone=tz),
                args=[tz],
                id=f"pipeline_{tz.replace('/', '_')}",
                replace_existing=True,
            )
            logger.info("Scheduler: registered CronTrigger at 19:00 %s", tz)
        except Exception as exc:
            # Invalid timezone string — log and skip rather than crashing startup
            logger.error("Scheduler: failed to register trigger for timezone %s: %s", tz, exc)

    return scheduler
