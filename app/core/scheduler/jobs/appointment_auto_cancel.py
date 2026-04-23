import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.common.enums.appointment_status_enum import AppointmentStatusEnum
from app.common.enums.notification_type_enum import NotificationTypeEnum
from app.core import logging_config
from app.db.database import AsyncSessionLocal
from app.modules.appointment.v1.models import Appointment
from app.modules.appointment.v1.service import get_appointments_for_auto_cancellation
from app.modules.notification.v1.service import send_notification

logger = logging.getLogger(__name__)

AUTO_CANCEL_WINDOW_HOURS = 24
AUTO_CANCEL_JOB_ID = "appointment-auto-cancel-job"


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _get_effective_schedule_window(appointment: Appointment) -> tuple[datetime, datetime]:
    availability_start = _normalize_datetime(appointment.availability.start_date_time)
    availability_end = _normalize_datetime(appointment.availability.end_date_time)

    if not appointment.changed_times:
        return availability_start, availability_end

    latest_changed_time = max(
        appointment.changed_times,
        key=lambda changed_time: changed_time.changed_at,
    )
    return (
        _normalize_datetime(latest_changed_time.start_date_time),
        _normalize_datetime(latest_changed_time.end_date_time),
    )


async def _send_cancellation_notification(
    db,
    receiver_user_id: str,
    title: str,
    body: str,
    notification_data: dict[str, str],
) -> None:
    await send_notification(
        db=db,
        receiver_user_id=receiver_user_id,
        notification_type=NotificationTypeEnum.APPOINTMENT,
        title=title,
        body=body,
        notification_data=notification_data,
    )


async def _send_cancellation_notification_with_session(
    receiver_user_id: str,
    title: str,
    body: str,
    notification_data: dict[str, str],
) -> None:
    async with AsyncSessionLocal() as db:
        await _send_cancellation_notification(
            db=db,
            receiver_user_id=receiver_user_id,
            title=title,
            body=body,
            notification_data=notification_data,
        )


async def cancel_stale_appointments() -> int:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=AUTO_CANCEL_WINDOW_HOURS)
    window_end = now

    logging_config.logger.info(
        "Checking for appointments to auto-cancel between %s and %s",
        window_start.isoformat(),
        window_end.isoformat(),
    )

    async with AsyncSessionLocal() as db:
        appointments = await get_appointments_for_auto_cancellation(
            db=db,
            window_start=window_start,
            window_end=window_end,
        )

        cancelled_count = 0
        notification_jobs: list[asyncio.Task[None]] = []

        logging_config.logger.info(
            "Found %s appointments to auto-cancel", len(appointments)
        )

        for appointment in appointments:
            effective_start_time, effective_end_time = _get_effective_schedule_window(
                appointment
            )

            if not (window_start <= effective_start_time and effective_end_time <= window_end):
                continue

            doctor_user = appointment.doctor.user if appointment.doctor else None
            patient_user = appointment.patient.user if appointment.patient else None

            appointment.status = AppointmentStatusEnum.CANCELLED
            if appointment.availability:
                appointment.availability.is_booked = False

            appointment_date = effective_start_time.strftime("%Y-%m-%d")
            appointment_time = effective_start_time.strftime("%I:%M %p")
            cancelled_at = now.isoformat()

            if doctor_user:
                notification_jobs.append(
                    asyncio.create_task(
                        _send_cancellation_notification_with_session(
                            receiver_user_id=doctor_user.id,
                            title="Appointment Cancelled",
                            body=(
                                f"An appointment with {patient_user.name if patient_user else 'a patient'} "
                                f"on {appointment_date} at {appointment_time} was cancelled automatically."
                            ),
                            notification_data={
                                "appointment_id": appointment.appointment_id,
                                "appointment_date": appointment_date,
                                "appointment_time": appointment_time,
                                "appointment_status": AppointmentStatusEnum.CANCELLED.value,
                                "cancelled_at": cancelled_at,
                                "receiver_type": "doctor",
                                "reason": "Appointment remained pending payment or confirmed within the last 24 hours.",
                            },
                        )
                    )
                )

            if patient_user:
                notification_jobs.append(
                    asyncio.create_task(
                        _send_cancellation_notification_with_session(
                            receiver_user_id=patient_user.id,
                            title="Appointment Cancelled",
                            body=(
                                f"Your appointment with Dr. {doctor_user.name if doctor_user else 'your doctor'} "
                                f"on {appointment_date} at {appointment_time} was cancelled automatically."
                            ),
                            notification_data={
                                "appointment_id": appointment.appointment_id,
                                "appointment_date": appointment_date,
                                "appointment_time": appointment_time,
                                "appointment_status": AppointmentStatusEnum.CANCELLED.value,
                                "cancelled_at": cancelled_at,
                                "receiver_type": "patient",
                                "reason": "Appointment remained pending payment or confirmed within the last 24 hours.",
                            },
                        )
                    )
                )

            cancelled_count += 1

        await db.commit()

        if notification_jobs:
            results = await asyncio.gather(*notification_jobs, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Auto-cancel notification failed: %s", str(result))

        if cancelled_count:
            logger.info("Auto-cancelled %s appointment(s)", cancelled_count)

        return cancelled_count
