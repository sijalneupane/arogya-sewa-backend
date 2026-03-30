from datetime import date
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums.role_enum import RoleEnum
from app.common.schema.pagination import PaginationMeta
from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.appointment.v1.schema import (
    AppointmentCreateSchema,
    AppointmentListResponse,
    AppointmentSingleResponse,
    AppointmentUpdateSchema,
)
from app.modules.appointment.v1.service import (
    can_user_modify_appointment,
    create_appointment,
    delete_appointment,
    get_all_appointments_super_admin,
    get_appointment_by_id,
    get_doctor_appointments,
    get_hospital_admin_appointments,
    get_patient_appointments,
    update_appointment,
)
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.doctor.v1.models import Doctor
from app.modules.patient.v1.models import Patient

router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"],
)


@router.post("", summary="Book a new appointment")
async def book_appointment(
    data: AppointmentCreateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentSingleResponse:
    """
    Book a new appointment.
    Only users with a patient profile can book appointments.

    The user must be a patient to book an appointment.
    """
    # Check if user has a patient profile
    patient_result = await db.execute(
        select(Patient).where(Patient.user_id == user.sub)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=403,
            detail="Only patients can book appointments. Please create a patient profile first.",
        )

    # Create the appointment
    appointment = await create_appointment(
        db=db,
        availability_id=data.availability_id,
        user_id=user.sub,
        patient_id=patient.patient_id,
        reason=data.reason,
        notes=data.notes,
    )

    # Use Pydantic schema validation instead of format_appointment_detail
    from app.modules.appointment.v1.schema import AppointmentDetailResponseSchema

    appointment_detail = AppointmentDetailResponseSchema.model_validate(appointment)

    return AppointmentSingleResponse(
        message="Appointment booked successfully",
        data=appointment_detail,
    )


# New role-specific endpoints


@router.get("/admin/all", summary="Get all appointments (Super Admin)")
async def list_all_appointments_super_admin(
    hospital_name: Optional[str] = Query(None, description="Search by hospital name"),
    doctor_name: Optional[str] = Query(None, description="Search by doctor name"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    patient_name: Optional[str] = Query(None, description="Search by patient name"),
    status: Optional[str] = Query(None, description="Filter by appointment status"),
    date_from: Optional[date] = Query(
        None, description="Filter appointments from this date"
    ),
    date_to: Optional[date] = Query(
        None, description="Filter appointments up to this date"
    ),
    appointment_date: Optional[date] = Query(
        None, description="Filter by specific appointment date"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(100, ge=1, le=500, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentListResponse:
    """
    Get all appointments with comprehensive filters.
    **Only accessible by Super Admin.**

    Filters available:
    - Hospital name (partial search)
    - Doctor name (partial search)
    - Patient ID or name
    - Appointment status
    - Date filtering (specific date, date range)
    """
    # Verify user is super admin
    if user.role != RoleEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only super admin can access this endpoint",
        )

    # Get appointments
    appointments, total = await get_all_appointments_super_admin(
        db=db,
        hospital_name=hospital_name,
        doctor_name=doctor_name,
        patient_id=patient_id,
        patient_name=patient_name,
        status=status,
        date_from=date_from,
        date_to=date_to,
        appointment_date=appointment_date,
        page=page,
        size=size,
    )

    # Use Pydantic schema validation instead of format_appointment_detail
    from app.modules.appointment.v1.schema import AppointmentDetailResponseSchema

    appointment_details = [
        AppointmentDetailResponseSchema.model_validate(appointment)
        for appointment in appointments
    ]

    # Calculate pagination metadata
    total_pages = ceil(total / size) if total > 0 else 0
    pagination_meta = PaginationMeta(
        currentPage=page,
        totalPage=total_pages,
        pageSize=size,
        totalRecords=total,
    )

    return AppointmentListResponse(
        message="Appointments retrieved successfully",
        data=appointment_details,
        paginationMeta=pagination_meta,
    )


@router.get("/patient/my-appointments", summary="Get my appointments (Patient)")
async def list_patient_appointments(
    status: Optional[str] = Query(None, description="Filter by appointment status"),
    date_from: Optional[date] = Query(
        None, description="Filter appointments from this date"
    ),
    date_to: Optional[date] = Query(
        None, description="Filter appointments up to this date"
    ),
    appointment_date: Optional[date] = Query(
        None, description="Filter by specific appointment date"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(100, ge=1, le=500, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentListResponse:
    """
    Get patient's own appointments.
    **Only accessible by Patient.**

    Filters available:
    - Appointment status
    - Date filtering (specific date, date range)
    """
    # Verify user is patient
    if user.role != RoleEnum.PATIENT:
        raise HTTPException(
            status_code=403,
            detail="Only patients can access this endpoint",
        )

    # Get appointments
    appointments, total = await get_patient_appointments(
        db=db,
        user_id=user.sub,
        status=status,
        date_from=date_from,
        date_to=date_to,
        appointment_date=appointment_date,
        page=page,
        size=size,
    )

    # Use Pydantic schema validation instead of format_appointment_detail
    from app.modules.appointment.v1.schema import AppointmentDetailResponseSchema

    appointment_details = [
        AppointmentDetailResponseSchema.model_validate(appointment)
        for appointment in appointments
    ]

    # Calculate pagination metadata
    total_pages = ceil(total / size) if total > 0 else 0
    pagination_meta = PaginationMeta(
        currentPage=page,
        totalPage=total_pages,
        pageSize=size,
        totalRecords=total,
    )

    return AppointmentListResponse(
        message="Appointments retrieved successfully",
        data=appointment_details,
        paginationMeta=pagination_meta,
    )


@router.get("/doctor/my-appointments", summary="Get my appointments (Doctor)")
async def list_doctor_appointments(
    status: Optional[str] = Query(None, description="Filter by appointment status"),
    date_from: Optional[date] = Query(
        None, description="Filter appointments from this date"
    ),
    date_to: Optional[date] = Query(
        None, description="Filter appointments up to this date"
    ),
    appointment_date: Optional[date] = Query(
        None, description="Filter by specific appointment date"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(100, ge=1, le=500, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentListResponse:
    """
    Get doctor's own appointments.
    **Only accessible by Doctor.**

    Filters available:
    - Appointment status
    - Date filtering (specific date, date range)
    """
    # Verify user is doctor
    if user.role != RoleEnum.DOCTOR:
        raise HTTPException(
            status_code=403,
            detail="Only doctors can access this endpoint",
        )

    # Get appointments
    appointments, total = await get_doctor_appointments(
        db=db,
        user_id=user.sub,
        status=status,
        date_from=date_from,
        date_to=date_to,
        appointment_date=appointment_date,
        page=page,
        size=size,
    )

    # Use Pydantic schema validation instead of format_appointment_detail
    from app.modules.appointment.v1.schema import AppointmentDetailResponseSchema

    appointment_details = [
        AppointmentDetailResponseSchema.model_validate(appointment)
        for appointment in appointments
    ]

    # Calculate pagination metadata
    total_pages = ceil(total / size) if total > 0 else 0
    pagination_meta = PaginationMeta(
        currentPage=page,
        totalPage=total_pages,
        pageSize=size,
        totalRecords=total,
    )

    return AppointmentListResponse(
        message="Appointments retrieved successfully",
        data=appointment_details,
        paginationMeta=pagination_meta,
    )


@router.get(
    "/hospital-admin/appointments", summary="Get hospital appointments (Hospital Admin)"
)
async def list_hospital_admin_appointments(
    doctor_name: Optional[str] = Query(
        None, description="Search by doctor name in their hospital"
    ),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    patient_name: Optional[str] = Query(None, description="Search by patient name"),
    status: Optional[str] = Query(None, description="Filter by appointment status"),
    date_from: Optional[date] = Query(
        None, description="Filter appointments from this date"
    ),
    date_to: Optional[date] = Query(
        None, description="Filter appointments up to this date"
    ),
    appointment_date: Optional[date] = Query(
        None, description="Filter by specific appointment date"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(100, ge=1, le=500, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentListResponse:
    """
    Get appointments for hospital admin's hospital.
    **Only accessible by Hospital Admin.**

    Filters available:
    - Doctor name (within their hospital)
    - Patient ID or name
    - Appointment status
    - Date filtering (specific date, date range)
    """
    # Verify user is hospital admin
    if user.role != RoleEnum.HOSPITAL_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only hospital admin can access this endpoint",
        )

    # Get appointments
    appointments, total = await get_hospital_admin_appointments(
        db=db,
        user_id=user.sub,
        doctor_name=doctor_name,
        patient_id=patient_id,
        patient_name=patient_name,
        status=status,
        date_from=date_from,
        date_to=date_to,
        appointment_date=appointment_date,
        page=page,
        size=size,
    )

    # Use Pydantic schema validation instead of format_appointment_detail
    from app.modules.appointment.v1.schema import AppointmentDetailResponseSchema

    appointment_details = [
        AppointmentDetailResponseSchema.model_validate(appointment)
        for appointment in appointments
    ]

    # Calculate pagination metadata
    total_pages = ceil(total / size) if total > 0 else 0
    pagination_meta = PaginationMeta(
        currentPage=page,
        totalPage=total_pages,
        pageSize=size,
        totalRecords=total,
    )

    return AppointmentListResponse(
        message="Appointments retrieved successfully",
        data=appointment_details,
        paginationMeta=pagination_meta,
    )


@router.get("/{appointment_id}", summary="Get appointment by ID")
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentSingleResponse:
    """
    Get a specific appointment by ID.

    Authorization:
    - Super admin can view any appointment
    - Hospital admin can view appointments for doctors in their hospital
    - Doctor can view their own appointments
    - Patient can view their own appointments
    """
    appointment = await get_appointment_by_id(db, appointment_id)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Check authorization based on role
    if user.role == RoleEnum.SUPER_ADMIN:
        # Super admin can view any appointment
        pass
    elif user.role == RoleEnum.HOSPITAL_ADMIN:
        # Check if appointment's doctor belongs to admin's hospital
        can_view = await can_user_modify_appointment(
            db, user.sub, user.role, appointment
        )
        if not can_view:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this appointment",
            )
    elif user.role == RoleEnum.DOCTOR:
        # Check if this is the doctor's appointment
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == user.sub)
        )
        doctor = doctor_result.scalar_one_or_none()

        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own appointments",
            )
    elif user.role == RoleEnum.PATIENT:
        # Check if this is the patient's appointment
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == user.sub)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own appointments",
            )
    else:
        raise HTTPException(status_code=403, detail="Invalid user role")

    # Use Pydantic schema validation instead of format_appointment_detail
    from app.modules.appointment.v1.schema import AppointmentDetailResponseSchema

    appointment_detail = AppointmentDetailResponseSchema.model_validate(appointment)

    return AppointmentSingleResponse(
        message="Appointment retrieved successfully",
        data=appointment_detail,
    )


@router.patch("/{appointment_id}", summary="Update appointment")
async def update_appointment_endpoint(
    appointment_id: str,
    data: AppointmentUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AppointmentSingleResponse:
    """
    Update an appointment.

    Only hospital admin and patient can update appointments.
    - Hospital admin can update appointments for doctors in their hospital
    - Patient can update their own appointments
    """
    # Get the appointment
    appointment = await get_appointment_by_id(db, appointment_id)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Check if user can modify this appointment
    if user.role not in [RoleEnum.HOSPITAL_ADMIN, RoleEnum.PATIENT]:
        raise HTTPException(
            status_code=403,
            detail="Only hospital admin and patient can update appointments",
        )

    can_modify = await can_user_modify_appointment(db, user.sub, user.role, appointment)
    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this appointment",
        )

    # Update the appointment
    updated_appointment = await update_appointment(
        db=db,
        appointment_id=appointment_id,
        reason=data.reason,
        notes=data.notes,
        status=data.status,
    )

    # Use Pydantic schema validation instead of format_appointment_detail
    from app.modules.appointment.v1.schema import AppointmentDetailResponseSchema

    appointment_detail = AppointmentDetailResponseSchema.model_validate(
        updated_appointment
    )

    return AppointmentSingleResponse(
        message="Appointment updated successfully",
        data=appointment_detail,
    )


@router.delete("/{appointment_id}", summary="Delete appointment")
async def delete_appointment_endpoint(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> dict:
    """
    Delete an appointment (cancel booking).

    Only hospital admin and patient can delete appointments.
    - Hospital admin can delete appointments for doctors in their hospital
    - Patient can delete their own appointments

    This will also mark the availability slot as not booked.
    """
    # Get the appointment
    appointment = await get_appointment_by_id(db, appointment_id)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Check if user can modify this appointment
    if user.role not in [RoleEnum.HOSPITAL_ADMIN, RoleEnum.PATIENT]:
        raise HTTPException(
            status_code=403,
            detail="Only hospital admin and patient can delete appointments",
        )

    can_modify = await can_user_modify_appointment(db, user.sub, user.role, appointment)
    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this appointment",
        )

    # Delete the appointment
    await delete_appointment(db=db, appointment_id=appointment_id)

    return {
        "message": "Appointment deleted successfully",
        "appointment_id": appointment_id,
    }
