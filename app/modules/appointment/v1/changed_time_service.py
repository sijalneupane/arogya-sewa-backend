import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.notification_type_enum import NotificationTypeEnum
from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.appointment.v1.changed_time_models import AppointmentChangedTime
from app.modules.appointment.v1.models import Appointment
from app.modules.doctor.v1.models import Doctor
from app.modules.hospital.v1.models import Hospital
from app.modules.notification.v1.service import send_notification
from app.modules.patient.v1.models import Patient
from app.modules.user.v1.models import User

logger = logging.getLogger(__name__)


async def can_user_view_changed_time(
    db: AsyncSession,
    changed_time: AppointmentChangedTime,
    user_id: str,
    user_role: str,
) -> bool:
    """
    Check if user can view this changed time record.

    Allowed viewers:
    - Superadmin
    - Hospital admin of the doctor's hospital
    - The patient of the appointment
    - The doctor of the appointment

    Args:
        db: Database session
        changed_time: The changed time record
        user_id: ID of the user trying to view
        user_role: Role of the user

    Returns:
        True if user can view, False otherwise
    """
    # Superadmin can view all
    if user_role == RoleEnum.SUPER_ADMIN.value:
        return True

    # Load the appointment with relationships
    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.doctor).selectinload(Doctor.hospital),
        )
        .where(Appointment.appointment_id == changed_time.appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        return False

    # Check if user is the patient
    patient_result = await db.execute(select(Patient).where(Patient.user_id == user_id))
    patient = patient_result.scalar_one_or_none()
    if patient and appointment.patient_id == patient.patient_id:
        return True

    # Check if user is the doctor
    doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == user_id))
    doctor = doctor_result.scalar_one_or_none()
    if doctor and appointment.doctor_id == doctor.doctor_id:
        return True

    # Check if user is hospital admin of the doctor's hospital
    if user_role == RoleEnum.HOSPITAL_ADMIN.value and appointment.doctor.hospital:
        hospital_result = await db.execute(
            select(Hospital).where(
                Hospital.hospital_id == appointment.doctor.hospital_id,
                Hospital.admin_id == user_id,
            )
        )
        hospital = hospital_result.scalar_one_or_none()
        if hospital:
            return True

    return False


async def can_user_modify_changed_time(
    db: AsyncSession, user_id: str, user_role: str
) -> bool:
    """
    Check if user can create/edit/delete changed time records.
    Doctors, patients, and hospital admins can modify changed time records.

    Args:
        db: Database session
        user_id: ID of the user
        user_role: Role of the user

    Returns:
        True if user is a doctor, patient, or hospital admin, False otherwise
    """
    # Superadmin can modify
    if user_role == RoleEnum.SUPER_ADMIN.value:
        return True

    # Check if user has a doctor profile
    doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == user_id))
    doctor = doctor_result.scalar_one_or_none()
    if doctor:
        return True

    # Check if user has a patient profile
    patient_result = await db.execute(select(Patient).where(Patient.user_id == user_id))
    patient = patient_result.scalar_one_or_none()
    if patient:
        return True

    # Check if user is a hospital admin
    if user_role == RoleEnum.HOSPITAL_ADMIN.value:
        hospital_result = await db.execute(
            select(Hospital).where(Hospital.admin_id == user_id)
        )
        hospital = hospital_result.scalar_one_or_none()
        if hospital:
            return True

    return False


async def create_changed_time(
    db: AsyncSession,
    appointment_id: str,
    start_date_time,
    end_date_time,
    reason: Optional[str],
    user_id: str,
) -> AppointmentChangedTime:
    """
    Create a new changed time record for an appointment.
    Sets the appointment status to RESCHEDULED.

    Args:
        db: Database session
        appointment_id: ID of the appointment
        start_date_time: New start datetime
        end_date_time: New end datetime
        reason: Reason for the change
        user_id: ID of the user making the change (doctor, patient, or hospital admin)

    Returns:
        Created changed time record

    Raises:
        HTTPException: If appointment not found
    """
    # Verify appointment exists
    result = await db.execute(
        select(Appointment).where(Appointment.appointment_id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Set appointment status to RESCHEDULED
    from app.common.enums.appointment_status_enum import AppointmentStatusEnum

    appointment.status = AppointmentStatusEnum.RESCHEDULED

    # Create changed time record
    changed_time_id = StringUtils.randomAlphaNumeric(12)
    changed_time = AppointmentChangedTime(
        changed_time_id=changed_time_id,
        appointment_id=appointment_id,
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        reason=reason,
        changed_by_user_id=user_id,
    )

    db.add(changed_time)
    await db.commit()
    await db.refresh(changed_time)

    try:
        patient_result = await db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.patient_id == appointment.patient_id)
        )
        patient = patient_result.scalar_one_or_none()
        if patient and patient.user:
            await send_notification(
                db=db,
                receiver_user_id=patient.user.id,
                notification_type=NotificationTypeEnum.APPOINTMENT,
                title="Appointment Time Changed",
                body=(
                    f"Your appointment has been rescheduled to {start_date_time.strftime('%Y-%m-%d %I:%M %p')}."
                ),
                notification_data={
                    "appointment_id": appointment_id,
                    "changed_time_id": changed_time_id,
                    "new_start_date_time": start_date_time.isoformat(),
                    "new_end_date_time": end_date_time.isoformat(),
                },
            )
    except Exception as exc:
        logger.warning(
            "Appointment time change saved but patient notification failed for appointment %s: %s",
            appointment_id,
            str(exc),
        )

    # Reload with changed_by relationship to avoid lazy loading issues
    changed_time_with_relations = await get_changed_time_by_id(db, changed_time_id)
    return changed_time_with_relations


async def get_changed_time_by_id(
    db: AsyncSession, changed_time_id: str
) -> Optional[AppointmentChangedTime]:
    """Get changed time record by ID"""
    result = await db.execute(
        select(AppointmentChangedTime)
        .options(
            selectinload(AppointmentChangedTime.appointment),
            selectinload(AppointmentChangedTime.changed_by).selectinload(User.role),
            selectinload(AppointmentChangedTime.changed_by).selectinload(User.files),
        )
        .where(AppointmentChangedTime.changed_time_id == changed_time_id)
    )
    return result.scalar_one_or_none()


async def get_changed_times_for_appointment(
    db: AsyncSession, appointment_id: str
) -> list[AppointmentChangedTime]:
    """Get all changed time records for an appointment"""
    result = await db.execute(
        select(AppointmentChangedTime)
        .options(
            selectinload(AppointmentChangedTime.changed_by).selectinload(User.role),
            selectinload(AppointmentChangedTime.changed_by).selectinload(User.files),
        )
        .where(AppointmentChangedTime.appointment_id == appointment_id)
        .order_by(AppointmentChangedTime.changed_at.desc())
    )
    return list(result.scalars().all())


async def update_changed_time(
    db: AsyncSession,
    changed_time_id: str,
    start_date_time=None,
    end_date_time=None,
    reason: Optional[str] = None,
) -> AppointmentChangedTime:
    """
    Update a changed time record.

    Args:
        db: Database session
        changed_time_id: ID of the changed time record
        start_date_time: Updated new start datetime
        end_date_time: Updated new end datetime
        reason: Updated reason

    Returns:
        Updated changed time record

    Raises:
        HTTPException: If changed time not found
    """
    changed_time = await get_changed_time_by_id(db, changed_time_id)

    if not changed_time:
        raise HTTPException(status_code=404, detail="Changed time record not found")

    if start_date_time is not None:
        changed_time.start_date_time = start_date_time
    if end_date_time is not None:
        changed_time.end_date_time = end_date_time
    if reason is not None:
        changed_time.reason = reason

    await db.commit()
    await db.refresh(changed_time)

    try:
        appointment_result = await db.execute(
            select(Appointment).where(
                Appointment.appointment_id == changed_time.appointment_id
            )
        )
        appointment = appointment_result.scalar_one_or_none()
        if appointment:
            patient_result = await db.execute(
                select(Patient)
                .options(selectinload(Patient.user))
                .where(Patient.patient_id == appointment.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient and patient.user:
                await send_notification(
                    db=db,
                    receiver_user_id=patient.user.id,
                    notification_type=NotificationTypeEnum.APPOINTMENT,
                    title="Appointment Time Updated",
                    body=(
                        f"Your appointment time has been updated to {changed_time.start_date_time.strftime('%Y-%m-%d %I:%M %p')}."
                    ),
                    notification_data={
                        "appointment_id": appointment.appointment_id,
                        "changed_time_id": changed_time.changed_time_id,
                        "new_start_date_time": changed_time.start_date_time.isoformat(),
                        "new_end_date_time": changed_time.end_date_time.isoformat(),
                    },
                )
    except Exception as exc:
        logger.warning(
            "Changed time updated but patient notification failed for changed_time %s: %s",
            changed_time_id,
            str(exc),
        )

    # Reload with relationships to avoid lazy loading issues
    changed_time_with_relations = await get_changed_time_by_id(db, changed_time_id)
    return changed_time_with_relations


async def delete_changed_time(db: AsyncSession, changed_time_id: str) -> None:
    """
    Delete a changed time record.

    Args:
        db: Database session
        changed_time_id: ID of the changed time record to delete

    Raises:
        HTTPException: If changed time not found
    """
    changed_time = await get_changed_time_by_id(db, changed_time_id)

    if not changed_time:
        raise HTTPException(status_code=404, detail="Changed time record not found")

    await db.delete(changed_time)
    await db.commit()
