import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import SchedulerAlreadyRunningError, SchedulerNotRunningError

from app.db import database_proxy as db
from app.settings import Config
from app.services.alerts import send_unacked_reminders
from app.services.db_lock import acquire_db_lock, release_db_lock


logger = logging.getLogger("oncall.scheduler")
_scheduler = None


def reminder_job():
    """
    Run reminder job under a database lock.

    The scheduler runs outside Flask request hooks, so it opens and closes
    a database connection explicitly for the APScheduler worker thread.
    """
    if db.is_closed():
        db.connect(reuse_if_open=True)

    owner = None

    try:
        owner = acquire_db_lock("reminder_job")
        if not owner:
            logger.debug("reminder job skipped because lock is busy")
            return 0

        logger.info("reminder job started")

        count = send_unacked_reminders()

        logger.info(
            "reminder job finished",
            extra={
                "extra": {
                    "event_type": "scheduler",
                    "reminders_processed": count,
                }
            },
        )

        return count

    except Exception:
        logger.exception("reminder job failed")
        return 0

    finally:
        if owner:
            release_db_lock("reminder_job", owner)

        if not db.is_closed():
            db.close()


def start_scheduler():
    """
    Start the background scheduler.

    The scheduler is kept as a module-level singleton so scheduler_worker can
    stop it cleanly during SIGTERM/SIGINT shutdown.
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.info("scheduler already running")
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        reminder_job,
        "interval",
        seconds=Config.REMINDER_INTERVAL_SECONDS,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.utcnow(),
        id="reminder_job",
        replace_existing=True,
    )

    try:
        _scheduler.start()
    except SchedulerAlreadyRunningError:
        logger.warning("scheduler was already started")

    logger.info(
        "scheduler started",
        extra={
            "extra": {
                "event_type": "scheduler",
                "reminder_interval_seconds": Config.REMINDER_INTERVAL_SECONDS,
                "lock_ttl_seconds": Config.SCHEDULER_LOCK_TTL_SECONDS,
            }
        },
    )

    return _scheduler


def stop_scheduler(wait=False):
    """
    Stop the background scheduler if it is running.
    """
    global _scheduler

    if not _scheduler:
        return

    try:
        if _scheduler.running:
            _scheduler.shutdown(wait=wait)
            logger.info("scheduler stopped")
    except SchedulerNotRunningError:
        pass
    finally:
        _scheduler = None
