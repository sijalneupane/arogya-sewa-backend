import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import authorize
from app.core.configuration.mailgun_config import get_mailgun_service
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.appointment.v1.changed_time_schema import (
    AppointmentChangedTimeCreateSchema,
    AppointmentChangedTimeListResponse,
    AppointmentChangedTimeResponseSchema,
    AppointmentChangedTimeSingleResponse,
    AppointmentChangedTimeUpdateSchema,
)
from app.modules.appointment.v1.changed_time_service import (
    can_user_view_changed_time,
    create_changed_time,
    delete_changed_time,
    get_changed_time_by_id,
    get_changed_times_for_appointment,
    update_changed_time,
)
from app.modules.appointment.v1.service import get_appointment_by_id
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.email.v1.email_utils import send_appointment_time_changed_email

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/appointment-changed-times",
    tags=["Appointment Changed Times"],
)


@router.post("", summary="Create a changed time record")
async def create_appointment_changed_time(
    data: AppointmentChangedTimeCreateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentChangedTimeSingleResponse:
    """
    Create a new changed time record for an appointment.
    Doctors, patients, and hospital admins can create changed time records.
    Sets the appointment status to RESCHEDULED.
    """
    changed_time = await create_changed_time(
        db=db,
        appointment_id=data.appointment_id,
        start_date_time=data.start_date_time,
        end_date_time=data.end_date_time,
        reason=data.reason,
        user_id=user.sub,
    )

    # Send appointment time change emails to patient, doctor, and hospital admin
    try:
        appointment = await get_appointment_by_id(db, data.appointment_id)
        if (
            appointment
            and appointment.doctor
            and appointment.patient
            and appointment.availability
        ):
            mailgun_service = get_mailgun_service()

            doctor_name = (
                appointment.doctor.user.name if appointment.doctor.user else "Doctor"
            )
            patient_name = (
                appointment.patient.user.name if appointment.patient.user else "Patient"
            )

            # Format old appointment date and time
            old_appointment_date = appointment.availability.start_date_time.strftime(
                "%B %d, %Y"
            )
            old_appointment_time = appointment.availability.start_date_time.strftime(
                "%I:%M %p"
            )

            # Format new appointment date and time
            new_appointment_date = changed_time.start_date_time.strftime("%B %d, %Y")
            new_appointment_time = changed_time.start_date_time.strftime("%I:%M %p")

            # Get hospital name
            hospital_name = "Arogya Sewa"
            if appointment.doctor.hospital:
                hospital_name = appointment.doctor.hospital.name

            # Send email to patient
            await send_appointment_time_changed_email(
                service=mailgun_service,
                recipient_name=patient_name,
                recipient_email=appointment.patient.user.email,
                recipient_type="patient",
                patient_name=patient_name,
                doctor_name=doctor_name,
                hospital_name=hospital_name,
                old_appointment_date=old_appointment_date,
                old_appointment_time=old_appointment_time,
                new_appointment_date=new_appointment_date,
                new_appointment_time=new_appointment_time,
                appointment_id=data.appointment_id,
                change_reason=data.reason,
            )

            # Send email to doctor
            await send_appointment_time_changed_email(
                service=mailgun_service,
                recipient_name=doctor_name,
                recipient_email=appointment.doctor.user.email,
                recipient_type="doctor",
                patient_name=patient_name,
                doctor_name=doctor_name,
                hospital_name=hospital_name,
                old_appointment_date=old_appointment_date,
                old_appointment_time=old_appointment_time,
                new_appointment_date=new_appointment_date,
                new_appointment_time=new_appointment_time,
                appointment_id=data.appointment_id,
                change_reason=data.reason,
            )

            # Send email to hospital admin if hospital exists
            if appointment.doctor.hospital and appointment.doctor.hospital.admin:
                admin = appointment.doctor.hospital.admin
                await send_appointment_time_changed_email(
                    service=mailgun_service,
                    recipient_name=admin.name,
                    recipient_email=admin.email,
                    recipient_type="hospital_admin",
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    hospital_name=hospital_name,
                    old_appointment_date=old_appointment_date,
                    old_appointment_time=old_appointment_time,
                    new_appointment_date=new_appointment_date,
                    new_appointment_time=new_appointment_time,
                    appointment_id=data.appointment_id,
                    change_reason=data.reason,
                )
    except Exception as exc:
        logger.warning(f"Failed to send appointment time change emails: {exc}")

    response_data = AppointmentChangedTimeResponseSchema.model_validate(changed_time)

    return AppointmentChangedTimeSingleResponse(
        message="Changed time record created successfully",
        data=response_data,
    )


@router.get("/{changed_time_id}", summary="Get a changed time record by ID")
async def get_appointment_changed_time(
    changed_time_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentChangedTimeSingleResponse:
    """
    Get a changed time record by ID.

    Viewable by:
    - Superadmin
    - Hospital admin of the doctor's hospital
    - The patient of the appointment
    - The doctor of the appointment
    """
    changed_time = await get_changed_time_by_id(db, changed_time_id)

    if not changed_time:
        raise HTTPException(status_code=404, detail="Changed time record not found")

    # Check if user can view this changed time
    can_view = await can_user_view_changed_time(db, changed_time, user.sub, user.role)
    if not can_view:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this changed time record",
        )

    response_data = AppointmentChangedTimeResponseSchema.model_validate(changed_time)

    return AppointmentChangedTimeSingleResponse(
        message="Changed time record retrieved successfully",
        data=response_data,
    )


@router.get(
    "/appointment/{appointment_id}",
    summary="Get all changed time records for an appointment",
)
async def get_appointment_changed_times(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentChangedTimeListResponse:
    """
    Get all changed time records for an appointment.

    Viewable by:
    - Superadmin
    - Hospital admin of the doctor's hospital
    - The patient of the appointment
    - The doctor of the appointment
    """
    changed_times = await get_changed_times_for_appointment(db, appointment_id)

    if not changed_times:
        return AppointmentChangedTimeListResponse(
            message="No changed time records found for this appointment",
            data=[],
        )

    # Check if user can view (check on first record, applies to all for same appointment)
    can_view = await can_user_view_changed_time(
        db, changed_times[0], user.sub, user.role
    )
    if not can_view:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view changed time records for this appointment",
        )

    response_data = [
        AppointmentChangedTimeResponseSchema.model_validate(ct) for ct in changed_times
    ]

    return AppointmentChangedTimeListResponse(
        message="Changed time records retrieved successfully",
        data=response_data,
    )


@router.put("/{changed_time_id}", summary="Update a changed time record")
async def update_appointment_changed_time(
    changed_time_id: str,
    data: AppointmentChangedTimeUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentChangedTimeSingleResponse:
    """
    Update a changed time record.
    Doctors, patients, and hospital admins can update changed time records.
    """
    changed_time = await update_changed_time(
        db=db,
        changed_time_id=changed_time_id,
        start_date_time=data.start_date_time,
        end_date_time=data.end_date_time,
        reason=data.reason,
    )

    response_data = AppointmentChangedTimeResponseSchema.model_validate(changed_time)

    return AppointmentChangedTimeSingleResponse(
        message="Changed time record updated successfully",
        data=response_data,
    )


@router.delete("/{changed_time_id}", summary="Delete a changed time record")
async def delete_appointment_changed_time(
    changed_time_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> dict:
    """
    Delete a changed time record.
    Doctors, patients, and hospital admins can delete changed time records.
    """
    await delete_changed_time(db, changed_time_id)

    return {"message": "Changed time record deleted successfully"}
