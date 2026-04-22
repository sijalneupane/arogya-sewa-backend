import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.common.enums.notification_type_enum import NotificationTypeEnum
from app.db.database import AsyncSessionLocal
from app.modules.appointment.v1.models import Appointment
from app.modules.appointment.v1.service import (
    get_appointments_for_reminders,
    mark_appointments_as_reminded,
)
from app.modules.notification.v1.service import send_notification

logger = logging.getLogger(__name__)

REMINDER_LEAD_TIME_HOURS = 3
REMINDER_WINDOW_MINUTES = 15
REMINDER_JOB_ID = "appointment-reminder-job"


def _get_effective_start_time(appointment: Appointment) -> datetime:
    if appointment.changed_times:
        latest_changed_time = max(
            appointment.changed_times,
            key=lambda changed_time: changed_time.changed_at,
        )
        return latest_changed_time.start_date_time

    return appointment.availability.start_date_time


async def _send_reminder_notification(
    db,
    receiver_user_id: str,
    title: str,
    body: str,
    notification_data: dict[str, str],
) -> None:
    await send_notification(
        db=db,
        receiver_user_id=receiver_user_id,
        notification_type=NotificationTypeEnum.REMINDER,
        title=title,
        body=body,
        notification_data=notification_data,
    )


async def _send_reminder_notification_with_session(
    receiver_user_id: str,
    title: str,
    body: str,
    notification_data: dict[str, str],
) -> None:
    async with AsyncSessionLocal() as db:
        await _send_reminder_notification(
            db=db,
            receiver_user_id=receiver_user_id,
            title=title,
            body=body,
            notification_data=notification_data,
        )


async def send_upcoming_appointment_reminders() -> int:
    now = datetime.now(timezone.utc)
    reminder_start_time = now + timedelta(hours=REMINDER_LEAD_TIME_HOURS)
    reminder_end_time = reminder_start_time + timedelta(minutes=REMINDER_WINDOW_MINUTES)

    async with AsyncSessionLocal() as db:
        appointments = await get_appointments_for_reminders(
            db=db,
            reminder_start_time=reminder_start_time,
            reminder_end_time=reminder_end_time,
        )

        reminded_appointment_ids: list[str] = []
        sent_count = 0
        for appointment in appointments:
            effective_start_time = _get_effective_start_time(appointment)
            if not (reminder_start_time <= effective_start_time < reminder_end_time):
                continue

            doctor_user = appointment.doctor.user if appointment.doctor else None
            patient_user = appointment.patient.user if appointment.patient else None
            if not doctor_user or not patient_user:
                logger.warning(
                    "Skipping reminder for appointment %s because doctor or patient user is missing",
                    appointment.appointment_id,
                )
                continue

            appointment_date = effective_start_time.strftime("%Y-%m-%d")
            appointment_time = effective_start_time.strftime("%I:%M %p")

            reminder_payload = {
                "appointment_id": appointment.appointment_id,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "reminder_start_time": reminder_start_time.isoformat(),
            }

            doctor_task = _send_reminder_notification_with_session(
                receiver_user_id=doctor_user.id,
                title="Appointment Reminder",
                body=(
                    f"You have an upcoming appointment with {patient_user.name} "
                    f"on {appointment_date} at {appointment_time}."
                ),
                notification_data={
                    **reminder_payload,
                    "receiver_type": "doctor",
                },
            )
            patient_task = _send_reminder_notification_with_session(
                receiver_user_id=patient_user.id,
                title="Appointment Reminder",
                body=(
                    f"You have an upcoming appointment with Dr. {doctor_user.name} "
                    f"on {appointment_date} at {appointment_time}."
                ),
                notification_data={
                    **reminder_payload,
                    "receiver_type": "patient",
                },
            )

            results = await asyncio.gather(
                doctor_task,
                patient_task,
                return_exceptions=True,
            )
            if any(isinstance(result, Exception) for result in results):
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning(
                            "Reminder notification failed for appointment %s: %s",
                            appointment.appointment_id,
                            str(result),
                        )
                continue

            reminded_appointment_ids.append(appointment.appointment_id)
            sent_count += 1

        await mark_appointments_as_reminded(
            db=db, appointment_ids=reminded_appointment_ids
        )

        if sent_count:
            logger.info(
                "Sent upcoming appointment reminders for %s appointment(s)",
                sent_count,
            )

        return sent_count
