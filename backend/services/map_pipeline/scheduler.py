"""APScheduler setup for global compute and local warm-only jobs.

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
from services.map_pipeline.scheduler_lock import (
    DEFAULT_LOCK_TTL_SECONDS,
    acquire_global_compute_lock,
    release_global_compute_lock,
)

logger = logging.getLogger(__name__)

GLOBAL_COMPUTE_JOB_ID = "global_compute_daily_utc"
GLOBAL_COMPUTE_UTC_HOUR = 0
GLOBAL_COMPUTE_UTC_MINUTE = 0


def _rows_list(data: object) -> list[dict]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _select_global_compute_user_id() -> str | None:
    """Select deterministic profile id used to run one global compute batch."""
    sb = get_supabase_client()
    rows = _rows_list(sb.rpc("get_all_profiles", {}).execute().data)
    user_ids = [row.get("id") for row in rows if row.get("id")]
    if not user_ids:
        return None
    return sorted(user_ids)[0]


def _run_daily_global_compute() -> None:
    """Run one daily global recompute guarded by a dedupe lock."""
    acquired, owner_token = acquire_global_compute_lock(ttl_seconds=DEFAULT_LOCK_TTL_SECONDS)
    if not acquired:
        logger.info("Scheduler: skipped duplicate global compute run (lock not acquired)")
        return

    try:
        requesting_user_id = _select_global_compute_user_id()
        if requesting_user_id is None:
            logger.warning("Scheduler: skipped global compute because no profiles were found")
            return
        run_pipeline_for_user(requesting_user_id)
        logger.info("Scheduler: daily global compute completed using user %s", requesting_user_id)
    except Exception as exc:
        logger.error("Scheduler: daily global compute FAILED: %s", exc)
        raise
    finally:
        released = release_global_compute_lock(owner_token)
        if not released:
            logger.warning("Scheduler: failed to release global compute lock for owner %s", owner_token)


def _run_warm_only_for_timezone(timezone: str) -> None:
    """Fetch all users in timezone and run warm-only behavior."""
    sb = get_supabase_client()
    rows = _rows_list(sb.rpc("get_profiles_by_timezone", {"p_timezone": timezone}).execute().data)
    logger.info(
        "Scheduler: warm-only refresh for %d users in timezone %s",
        len(rows),
        timezone,
    )


def setup_scheduler() -> AsyncIOScheduler:
    """Register one UTC global compute job and local timezone warm-only jobs.

    Timezones are queried once at startup. New timezones added after startup
    require an app restart to be picked up. Users in already-registered timezones
    are always picked up at fire time (the job re-queries by timezone).

    Returns:
        Configured but not-yet-started AsyncIOScheduler (MemoryJobStore default).
    """
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        _run_daily_global_compute,
        trigger=CronTrigger(
            hour=GLOBAL_COMPUTE_UTC_HOUR,
            minute=GLOBAL_COMPUTE_UTC_MINUTE,
            timezone="UTC",
        ),
        id=GLOBAL_COMPUTE_JOB_ID,
        replace_existing=True,
    )
    logger.info("Scheduler: registered daily global compute CronTrigger at 00:00 UTC")

    sb = get_supabase_client()
    rows = _rows_list(sb.rpc("get_distinct_timezones", {}).execute().data)

    unique_timezones = {row["timezone"] for row in rows if row.get("timezone")}
    logger.info("Scheduler: found %d unique timezone(s) to register", len(unique_timezones))

    for tz in unique_timezones:
        try:
            scheduler.add_job(
                _run_warm_only_for_timezone,
                trigger=CronTrigger(hour=19, minute=0, timezone=tz),
                args=[tz],
                id=f"warm_only_{tz.replace('/', '_')}",
                replace_existing=True,
            )
            logger.info("Scheduler: registered warm-only CronTrigger at 19:00 %s", tz)
        except Exception as exc:
            # Invalid timezone string — log and skip rather than crashing startup
            logger.error("Scheduler: failed to register trigger for timezone %s: %s", tz, exc)

    return scheduler
