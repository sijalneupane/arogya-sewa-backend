from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import authorize
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
from app.modules.auth.v1.schemas import JwtPayload

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
