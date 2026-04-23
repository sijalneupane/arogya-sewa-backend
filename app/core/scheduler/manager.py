import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core import logging_config
from app.core.scheduler.jobs.appointment_auto_cancel import (
    AUTO_CANCEL_JOB_ID,
    cancel_stale_appointments,
)
from app.core.scheduler.jobs.appointment_reminder import (
    REMINDER_JOB_ID,
    REMINDER_WINDOW_MINUTES,
    send_upcoming_appointment_reminders,
)

logger = logging.getLogger(__name__)

app_scheduler = AsyncIOScheduler(timezone=timezone.utc)


def register_scheduler_jobs() -> None:
    logging_config.logger.info("Registering scheduler jobs")
    app_scheduler.add_job(
        send_upcoming_appointment_reminders,
        trigger=IntervalTrigger(minutes=REMINDER_WINDOW_MINUTES),
        id=REMINDER_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
        next_run_time=datetime.now(timezone.utc),
    )
    app_scheduler.add_job(
        cancel_stale_appointments,
        trigger=CronTrigger(hour=0, minute=0),
        id=AUTO_CANCEL_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )


def start_app_scheduler() -> None:
    if app_scheduler.running:
        return

    register_scheduler_jobs()
    app_scheduler.start()
    logging_config.logger.info(
        "Application scheduler started with reminder jobs running every %s minutes and auto-cancel at 00:00 UTC",
        REMINDER_WINDOW_MINUTES,
    )


def shutdown_app_scheduler() -> None:
    if not app_scheduler.running:
        return

    app_scheduler.shutdown(wait=False)
    logger.info("Application scheduler stopped")
