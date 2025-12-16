from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.appointment.v1.models import Appointment
from app.modules.appointment.v1.schema import (
    AppointmentDetailResponseSchema,
    AvailabilityBasicInfo,
    DoctorBasicInfo,
    PatientBasicInfo,
)
from app.modules.availability.v1.models import Availability
from app.modules.doctor.v1.models import Doctor
from app.modules.hospital.v1.models import Hospital
from app.modules.patient.v1.models import Patient
from app.modules.user.v1.models import User


async def validate_availability_for_booking(
    db: AsyncSession, availability_id: str
) -> Availability:
    """
    Validate that an availability slot exists and can be booked.

    Args:
        db: Database session
        availability_id: ID of the availability slot

    Returns:
        Availability object if valid

    Raises:
        HTTPException: If availability not found, already booked, or date is in the past
    """
    result = await db.execute(
        select(Availability).where(Availability.availability_id == availability_id)
    )
    availability = result.scalar_one_or_none()

    if not availability:
        raise HTTPException(status_code=404, detail="Availability slot not found")

    if availability.is_booked:
        raise HTTPException(
            status_code=400, detail="This availability slot is already booked"
        )

    if availability.date < date.today():
        raise HTTPException(
            status_code=400, detail="Cannot book appointments for past dates"
        )

    return availability


async def create_appointment(
    db: AsyncSession,
    availability_id: str,
    user_id: str,
    patient_id: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
) -> Appointment:
    """
    Create a new appointment (book an availability slot).

    Args:
        db: Database session
        availability_id: ID of the availability slot (validated by Pydantic schema)
        user_id: ID of the user booking the appointment
        patient_id: ID of the patient
        reason: Reason for appointment
        notes: Additional notes

    Returns:
        Created appointment object

    Raises:
        HTTPException: If availability not found or already booked
    """
    # Fetch availability and validate business rules
    availability = await validate_availability_for_booking(db, availability_id)

    # Create appointment
    appointment_id = StringUtils.randomAlphaNumeric(8)
    appointment = Appointment(
        appointment_id=appointment_id,
        patient_id=patient_id,
        doctor_id=availability.doctor_id,
        availability_id=availability_id,
        booked_by_user_id=user_id,
        appointment_date=availability.date,
        reason=reason,
        notes=notes,
        status="scheduled",
    )

    # Mark availability as booked
    availability.is_booked = True

    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    # Reload with relationships to avoid lazy loading issues
    appointment_with_relations = await get_appointment_by_id(
        db, appointment.appointment_id
    )
    return appointment_with_relations


async def get_appointment_by_id(
    db: AsyncSession, appointment_id: str
) -> Optional[Appointment]:
    """Get appointment by ID with all relationships loaded"""
    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.patient).selectinload(Patient.user),
            selectinload(Appointment.doctor).selectinload(Doctor.user),
            selectinload(Appointment.availability),
            selectinload(Appointment.booked_by),
        )
        .where(Appointment.appointment_id == appointment_id)
    )
    return result.scalar_one_or_none()


def format_appointment_detail(
    appointment: Appointment,
) -> AppointmentDetailResponseSchema:
    """Format appointment object to detail response schema"""
    patient_info = PatientBasicInfo(
        patient_id=appointment.patient.patient_id,
        gender=appointment.patient.gender,
        blood_group=appointment.patient.blood_group,
        user_name=appointment.patient.user.name,
        user_email=appointment.patient.user.email,
        user_phone=appointment.patient.user.phone_number,
    )

    doctor_info = DoctorBasicInfo(
        doctor_id=appointment.doctor.doctor_id,
        specialization_department=appointment.doctor.specialization_department,
        experience_years=appointment.doctor.experience_years,
        user_name=appointment.doctor.user.name,
        user_email=appointment.doctor.user.email,
    )

    availability_info = AvailabilityBasicInfo(
        availability_id=appointment.availability.availability_id,
        date=appointment.availability.date,
        start_time=appointment.availability.start_time,
        end_time=appointment.availability.end_time,
    )

    return AppointmentDetailResponseSchema(
        appointment_id=appointment.appointment_id,
        patient=patient_info,
        doctor=doctor_info,
        availability=availability_info,
        appointment_date=appointment.appointment_date,
        reason=appointment.reason,
        notes=appointment.notes,
        status=appointment.status,
        booked_by_user_id=appointment.booked_by_user_id,
        created_at=appointment.created_at.isoformat(),
        updated_at=appointment.updated_at.isoformat(),
    )


async def get_appointments_for_user(
    db: AsyncSession,
    user_id: str,
    user_role: RoleEnum,
    hospital_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    patient_name: Optional[str] = None,
    appointment_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Appointment], int]:
    """
    Get appointments based on user role and filters.

    Authorization logic:
    - SUPER_ADMIN: Can view all appointments with filters
    - HOSPITAL_ADMIN: Can view appointments for doctors in their hospital
    - DOCTOR: Can only view their own appointments
    - PATIENT: Can only view their own appointments

    Args:
        db: Database session
        user_id: ID of the requesting user
        user_role: Role of the requesting user
        hospital_id: Filter by hospital (super admin only)
        doctor_id: Filter by doctor (super admin and hospital admin)
        patient_name: Filter by patient name (super admin)
        appointment_date: Filter by appointment date
        skip: Pagination skip
        limit: Pagination limit

    Returns:
        Tuple of (list of appointments, total count)
    """
    query = select(Appointment).options(
        selectinload(Appointment.patient).selectinload(Patient.user),
        selectinload(Appointment.doctor)
        .selectinload(Doctor.user)
        .selectinload(User.hospital),
        selectinload(Appointment.availability),
        selectinload(Appointment.booked_by),
    )

    # Apply role-based filters
    if user_role == RoleEnum.SUPER_ADMIN:
        # Super admin can see all, apply optional filters
        if hospital_id:
            query = query.join(Doctor).where(Doctor.hospital_id == hospital_id)
        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)
        if patient_name:
            query = (
                query.join(Patient)
                .join(User)
                .where(User.name.ilike(f"%{patient_name}%"))
            )
        if appointment_date:
            query = query.where(Appointment.appointment_date == appointment_date)

    elif user_role == RoleEnum.HOSPITAL_ADMIN:
        # Hospital admin can only see appointments for doctors in their hospital
        # First get the hospital admin's hospital
        hospital_result = await db.execute(
            select(Hospital).where(Hospital.admin_id == user_id)
        )
        hospital = hospital_result.scalar_one_or_none()

        if not hospital:
            raise HTTPException(
                status_code=403,
                detail="Hospital admin must be associated with a hospital",
            )

        # Filter by hospital's doctors
        query = query.join(Doctor).where(Doctor.hospital_id == hospital.hospital_id)

        # Apply optional doctor filter
        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)
        if appointment_date:
            query = query.where(Appointment.appointment_date == appointment_date)

    elif user_role == RoleEnum.DOCTOR:
        # Doctor can only see their own appointments
        # First get the doctor's doctor_id
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == user_id)
        )
        doctor = doctor_result.scalar_one_or_none()

        if not doctor:
            raise HTTPException(
                status_code=403, detail="User is not associated with a doctor profile"
            )

        query = query.where(Appointment.doctor_id == doctor.doctor_id)

        if appointment_date:
            query = query.where(Appointment.appointment_date == appointment_date)

    elif user_role == RoleEnum.PATIENT:
        # Patient can only see their own appointments
        # First get the patient's patient_id
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == user_id)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            raise HTTPException(
                status_code=403, detail="User is not associated with a patient profile"
            )

        query = query.where(Appointment.patient_id == patient.patient_id)

        if appointment_date:
            query = query.where(Appointment.appointment_date == appointment_date)

    else:
        raise HTTPException(status_code=403, detail="Invalid user role")

    # Get total count
    count_query = select(Appointment)
    # Apply the same filters to count query
    if user_role == RoleEnum.SUPER_ADMIN:
        if hospital_id:
            count_query = count_query.join(Doctor).where(
                Doctor.hospital_id == hospital_id
            )
        if doctor_id:
            count_query = count_query.where(Appointment.doctor_id == doctor_id)
        if patient_name:
            count_query = (
                count_query.join(Patient)
                .join(User)
                .where(User.name.ilike(f"%{patient_name}%"))
            )
        if appointment_date:
            count_query = count_query.where(
                Appointment.appointment_date == appointment_date
            )
    elif user_role == RoleEnum.HOSPITAL_ADMIN:
        hospital_result = await db.execute(
            select(Hospital).where(Hospital.admin_id == user_id)
        )
        hospital = hospital_result.scalar_one_or_none()
        if hospital:
            count_query = count_query.join(Doctor).where(
                Doctor.hospital_id == hospital.hospital_id
            )
            if doctor_id:
                count_query = count_query.where(Appointment.doctor_id == doctor_id)
            if appointment_date:
                count_query = count_query.where(
                    Appointment.appointment_date == appointment_date
                )
    elif user_role == RoleEnum.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if doctor:
            count_query = count_query.where(Appointment.doctor_id == doctor.doctor_id)
            if appointment_date:
                count_query = count_query.where(
                    Appointment.appointment_date == appointment_date
                )
    elif user_role == RoleEnum.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if patient:
            count_query = count_query.where(
                Appointment.patient_id == patient.patient_id
            )
            if appointment_date:
                count_query = count_query.where(
                    Appointment.appointment_date == appointment_date
                )

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Order by appointment date descending (newest first)
    query = query.order_by(Appointment.appointment_date.desc())

    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total


async def update_appointment(
    db: AsyncSession,
    appointment_id: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    status: Optional[str] = None,
) -> Appointment:
    """
    Update an appointment.

    Args:
        db: Database session
        appointment_id: ID of the appointment to update
        reason: Updated reason
        notes: Updated notes
        status: Updated status

    Returns:
        Updated appointment object

    Raises:
        HTTPException: If appointment not found
    """
    appointment = await get_appointment_by_id(db, appointment_id)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Update fields if provided
    if reason is not None:
        appointment.reason = reason
    if notes is not None:
        appointment.notes = notes
    if status is not None:
        appointment.status = status

    await db.commit()
    await db.refresh(appointment)

    # Reload with relationships to avoid lazy loading issues
    appointment_with_relations = await get_appointment_by_id(db, appointment_id)
    return appointment_with_relations


async def delete_appointment(
    db: AsyncSession,
    appointment_id: str,
) -> None:
    """
    Delete an appointment and mark the availability as not booked.

    Args:
        db: Database session
        appointment_id: ID of the appointment to delete

    Raises:
        HTTPException: If appointment not found
    """
    appointment = await get_appointment_by_id(db, appointment_id)

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Mark availability as not booked
    availability_result = await db.execute(
        select(Availability).where(
            Availability.availability_id == appointment.availability_id
        )
    )
    availability = availability_result.scalar_one_or_none()
    if availability:
        availability.is_booked = False

    await db.delete(appointment)
    await db.commit()


async def can_user_modify_appointment(
    db: AsyncSession,
    user_id: str,
    user_role: RoleEnum,
    appointment: Appointment,
) -> bool:
    """
    Check if user can modify (update/delete) an appointment.

    Rules:
    - Hospital admin can modify appointments for doctors in their hospital
    - Patient can modify their own appointments
    - Super admin has full access (but this is handled at router level)

    Args:
        db: Database session
        user_id: ID of the user requesting modification
        user_role: Role of the user
        appointment: Appointment object to modify

    Returns:
        True if user can modify, False otherwise
    """
    if user_role == RoleEnum.HOSPITAL_ADMIN:
        # Check if the appointment's doctor belongs to the admin's hospital
        hospital_result = await db.execute(
            select(Hospital).where(Hospital.admin_id == user_id)
        )
        hospital = hospital_result.scalar_one_or_none()

        if not hospital:
            return False

        # Get the doctor's hospital
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.doctor_id == appointment.doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()

        if not doctor or doctor.hospital_id != hospital.hospital_id:
            return False

        return True

    elif user_role == RoleEnum.PATIENT:
        # Check if the appointment belongs to this patient
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == user_id)
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            return False

        return appointment.patient_id == patient.patient_id

    return False


# New role-specific appointment listing services


async def get_all_appointments_super_admin(
    db: AsyncSession,
    hospital_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    patient_name: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    appointment_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Appointment], int]:
    """
    Get all appointments for super admin with comprehensive filters.

    Args:
        db: Database session
        hospital_id: Filter by hospital ID
        doctor_id: Filter by doctor ID
        patient_id: Filter by patient ID
        patient_name: Search by patient name (partial match)
        status: Filter by appointment status
        date_from: Filter appointments from this date (inclusive)
        date_to: Filter appointments up to this date (inclusive)
        appointment_date: Filter by specific appointment date
        skip: Pagination offset
        limit: Maximum number of records

    Returns:
        Tuple of (list of appointments, total count)
    """
    # Base query with all relationships
    query = select(Appointment).options(
        selectinload(Appointment.patient).selectinload(Patient.user),
        selectinload(Appointment.doctor).selectinload(Doctor.user),
        selectinload(Appointment.availability),
        selectinload(Appointment.booked_by),
    )

    # Build filter conditions
    conditions = []

    if hospital_id:
        query = query.join(Doctor)
        conditions.append(Doctor.hospital_id == hospital_id)

    if doctor_id:
        conditions.append(Appointment.doctor_id == doctor_id)

    if patient_id:
        conditions.append(Appointment.patient_id == patient_id)

    if patient_name:
        query = query.join(Patient).join(User, Patient.user_id == User.user_id)
        conditions.append(User.name.ilike(f"%{patient_name}%"))

    if status:
        conditions.append(Appointment.status == status)

    if appointment_date:
        conditions.append(Appointment.appointment_date == appointment_date)
    elif date_from or date_to:
        if date_from:
            conditions.append(Appointment.appointment_date >= date_from)
        if date_to:
            conditions.append(Appointment.appointment_date <= date_to)

    # Apply all conditions
    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(Appointment)
    if hospital_id:
        count_query = count_query.join(Doctor).where(Doctor.hospital_id == hospital_id)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(Appointment.appointment_date.desc())
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total


async def get_patient_appointments(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    appointment_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Appointment], int]:
    """
    Get appointments for a specific patient (their own appointments only).

    Args:
        db: Database session
        user_id: User ID of the patient
        status: Filter by appointment status
        date_from: Filter appointments from this date (inclusive)
        date_to: Filter appointments up to this date (inclusive)
        appointment_date: Filter by specific appointment date
        skip: Pagination offset
        limit: Maximum number of records

    Returns:
        Tuple of (list of appointments, total count)

    Raises:
        HTTPException: If user is not associated with a patient profile
    """
    # Get patient profile
    patient_result = await db.execute(select(Patient).where(Patient.user_id == user_id))
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=403, detail="User is not associated with a patient profile"
        )

    # Base query with all relationships
    query = select(Appointment).options(
        selectinload(Appointment.patient).selectinload(Patient.user),
        selectinload(Appointment.doctor).selectinload(Doctor.user),
        selectinload(Appointment.availability),
        selectinload(Appointment.booked_by),
    )

    # Build filter conditions
    conditions = [Appointment.patient_id == patient.patient_id]

    if status:
        conditions.append(Appointment.status == status)

    if appointment_date:
        conditions.append(Appointment.appointment_date == appointment_date)
    elif date_from or date_to:
        if date_from:
            conditions.append(Appointment.appointment_date >= date_from)
        if date_to:
            conditions.append(Appointment.appointment_date <= date_to)

    # Apply all conditions
    query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(Appointment).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(Appointment.appointment_date.desc())
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total


async def get_doctor_appointments(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    appointment_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Appointment], int]:
    """
    Get appointments for a specific doctor (their own appointments only).

    Args:
        db: Database session
        user_id: User ID of the doctor
        status: Filter by appointment status
        date_from: Filter appointments from this date (inclusive)
        date_to: Filter appointments up to this date (inclusive)
        appointment_date: Filter by specific appointment date
        skip: Pagination offset
        limit: Maximum number of records

    Returns:
        Tuple of (list of appointments, total count)

    Raises:
        HTTPException: If user is not associated with a doctor profile
    """
    # Get doctor profile
    doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == user_id))
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=403, detail="User is not associated with a doctor profile"
        )

    # Base query with all relationships
    query = select(Appointment).options(
        selectinload(Appointment.patient).selectinload(Patient.user),
        selectinload(Appointment.doctor).selectinload(Doctor.user),
        selectinload(Appointment.availability),
        selectinload(Appointment.booked_by),
    )

    # Build filter conditions
    conditions = [Appointment.doctor_id == doctor.doctor_id]

    if status:
        conditions.append(Appointment.status == status)

    if appointment_date:
        conditions.append(Appointment.appointment_date == appointment_date)
    elif date_from or date_to:
        if date_from:
            conditions.append(Appointment.appointment_date >= date_from)
        if date_to:
            conditions.append(Appointment.appointment_date <= date_to)

    # Apply all conditions
    query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(Appointment).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(Appointment.appointment_date.desc())
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total


async def get_hospital_admin_appointments(
    db: AsyncSession,
    user_id: str,
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    patient_name: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    appointment_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Appointment], int]:
    """
    Get appointments for hospital admin (their hospital's appointments only).
    Can filter by doctor and patient within their hospital.

    Args:
        db: Database session
        user_id: User ID of the hospital admin
        doctor_id: Filter by doctor ID (must be in their hospital)
        patient_id: Filter by patient ID
        patient_name: Search by patient name (partial match)
        status: Filter by appointment status
        date_from: Filter appointments from this date (inclusive)
        date_to: Filter appointments up to this date (inclusive)
        appointment_date: Filter by specific appointment date
        skip: Pagination offset
        limit: Maximum number of records

    Returns:
        Tuple of (list of appointments, total count)

    Raises:
        HTTPException: If user is not associated with a hospital admin profile
    """
    # Get hospital admin's hospital
    hospital_result = await db.execute(
        select(Hospital).where(Hospital.admin_id == user_id)
    )
    hospital = hospital_result.scalar_one_or_none()

    if not hospital:
        raise HTTPException(
            status_code=403,
            detail="Hospital admin must be associated with a hospital",
        )

    # Base query with all relationships
    query = (
        select(Appointment)
        .join(Doctor)
        .options(
            selectinload(Appointment.patient).selectinload(Patient.user),
            selectinload(Appointment.doctor).selectinload(Doctor.user),
            selectinload(Appointment.availability),
            selectinload(Appointment.booked_by),
        )
    )

    # Build filter conditions - must be in their hospital
    conditions = [Doctor.hospital_id == hospital.hospital_id]

    if doctor_id:
        conditions.append(Appointment.doctor_id == doctor_id)

    if patient_id:
        conditions.append(Appointment.patient_id == patient_id)

    if patient_name:
        query = query.join(Patient).join(User, Patient.user_id == User.user_id)
        conditions.append(User.name.ilike(f"%{patient_name}%"))

    if status:
        conditions.append(Appointment.status == status)

    if appointment_date:
        conditions.append(Appointment.appointment_date == appointment_date)
    elif date_from or date_to:
        if date_from:
            conditions.append(Appointment.appointment_date >= date_from)
        if date_to:
            conditions.append(Appointment.appointment_date <= date_to)

    # Apply all conditions
    query = query.where(and_(*conditions))

    # Get total count
    count_query = (
        select(func.count())
        .select_from(Appointment)
        .join(Doctor)
        .where(and_(*conditions))
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(Appointment.appointment_date.desc())
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total
