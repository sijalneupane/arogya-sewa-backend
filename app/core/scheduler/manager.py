import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.scheduler.jobs.appointment_reminder import (
    REMINDER_JOB_ID,
    REMINDER_WINDOW_MINUTES,
    send_upcoming_appointment_reminders,
)

logger = logging.getLogger(__name__)

app_scheduler = AsyncIOScheduler(timezone=timezone.utc)


def register_scheduler_jobs() -> None:
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


def start_app_scheduler() -> None:
    if app_scheduler.running:
        return

    register_scheduler_jobs()
    app_scheduler.start()
    logger.info(
        "Application scheduler started with reminder jobs running every %s minutes",
        REMINDER_WINDOW_MINUTES,
    )


def shutdown_app_scheduler() -> None:
    if not app_scheduler.running:
        return

    app_scheduler.shutdown(wait=False)
    logger.info("Application scheduler stopped")
