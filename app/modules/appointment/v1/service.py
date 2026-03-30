from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.appointment_status_enum import AppointmentStatusEnum
from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.appointment.v1.models import Appointment
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

    # Check if there's already an appointment for this availability (more robust than just checking is_booked flag)
    existing_appointment = await db.execute(
        select(Appointment).where(Appointment.availability_id == availability_id)
    )
    if existing_appointment.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="This availability slot is already booked"
        )

    if availability.is_booked:
        raise HTTPException(
            status_code=400, detail="This availability slot is already booked"
        )

    if availability.start_date_time < datetime.now(timezone.utc):
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
        reason=reason,
        notes=notes,
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
            selectinload(Appointment.patient)
            .selectinload(Patient.user)
            .selectinload(User.role),
            selectinload(Appointment.patient)
            .selectinload(Patient.user)
            .selectinload(User.files),
            selectinload(Appointment.doctor)
            .selectinload(Doctor.user)
            .selectinload(User.role),
            selectinload(Appointment.doctor)
            .selectinload(Doctor.user)
            .selectinload(User.files),
            selectinload(Appointment.doctor).selectinload(Doctor.license_certificate),
            selectinload(Appointment.doctor).selectinload(Doctor.department),
            selectinload(Appointment.availability),
            selectinload(Appointment.booked_by).selectinload(User.role),
            selectinload(Appointment.booked_by).selectinload(User.files),
            selectinload(Appointment.changed_times),
        )
        .where(Appointment.appointment_id == appointment_id)
    )
    return result.scalar_one_or_none()


async def update_appointment(
    db: AsyncSession,
    appointment_id: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    status: Optional[AppointmentStatusEnum] = None,
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
    hospital_name: Optional[str] = None,
    doctor_name: Optional[str] = None,
    patient_id: Optional[str] = None,
    patient_name: Optional[str] = None,
    status: Optional[AppointmentStatusEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    appointment_date: Optional[date] = None,
    page: int = 1,
    size: int = 100,
) -> tuple[list[Appointment], int]:
    """
    Get all appointments for super admin with comprehensive filters.

    Args:
        db: Database session
        hospital_name: Search by hospital name (partial match)
        doctor_name: Search by doctor name (partial match)
        patient_id: Filter by patient ID
        patient_name: Search by patient name (partial match)
        status: Filter by appointment status
        date_from: Filter appointments from this date (inclusive)
        date_to: Filter appointments up to this date (inclusive)
        appointment_date: Filter by specific appointment date
        page: Page number (1-indexed)
        size: Number of items per page

    Returns:
        Tuple of (list of appointments, total count)
    """
    # Base query with all relationships
    query = select(Appointment).options(
        selectinload(Appointment.patient)
        .selectinload(Patient.user)
        .selectinload(User.role),
        selectinload(Appointment.patient)
        .selectinload(Patient.user)
        .selectinload(User.files),
        selectinload(Appointment.doctor)
        .selectinload(Doctor.user)
        .selectinload(User.role),
        selectinload(Appointment.doctor)
        .selectinload(Doctor.user)
        .selectinload(User.files),
        selectinload(Appointment.doctor).selectinload(Doctor.license_certificate),
        selectinload(Appointment.doctor).selectinload(Doctor.department),
        selectinload(Appointment.availability),
        selectinload(Appointment.booked_by).selectinload(User.role),
        selectinload(Appointment.booked_by).selectinload(User.files),
        selectinload(Appointment.changed_times),
    )

    # Build filter conditions
    conditions = []

    if hospital_name:
        query = query.join(Doctor).join(
            Hospital, Doctor.hospital_id == Hospital.hospital_id
        )
        conditions.append(Hospital.hospital_name.ilike(f"%{hospital_name}%"))

    if doctor_name:
        if not hospital_name:  # Only join Doctor if not already joined
            query = query.join(Doctor)
        query = query.join(User, Doctor.user_id == User.user_id)
        conditions.append(User.name.ilike(f"%{doctor_name}%"))

    if patient_id:
        conditions.append(Appointment.patient_id == patient_id)

    if patient_name:
        # Need to use an alias for User since doctor_name might have already joined User
        if doctor_name:
            from sqlalchemy.orm import aliased

            PatientUser = aliased(User)
            query = query.join(Patient).join(
                PatientUser, Patient.user_id == PatientUser.user_id
            )
            conditions.append(PatientUser.name.ilike(f"%{patient_name}%"))
        else:
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
    if hospital_name:
        count_query = count_query.join(Doctor).join(
            Hospital, Doctor.hospital_id == Hospital.hospital_id
        )
    if conditions:
        count_query = count_query.where(and_(*conditions))

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination (page is 1-indexed)
    skip = (page - 1) * size
    query = query.order_by(Appointment.appointment_date.desc())
    query = query.offset(skip).limit(size)

    # Execute query
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total


async def get_patient_appointments(
    db: AsyncSession,
    user_id: str,
    status: Optional[AppointmentStatusEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    appointment_date: Optional[date] = None,
    page: int = 1,
    size: int = 100,
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
        page: Page number (1-indexed)
        size: Number of items per page

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
        selectinload(Appointment.patient)
        .selectinload(Patient.user)
        .selectinload(User.role),
        selectinload(Appointment.patient)
        .selectinload(Patient.user)
        .selectinload(User.files),
        selectinload(Appointment.doctor)
        .selectinload(Doctor.user)
        .selectinload(User.role),
        selectinload(Appointment.doctor)
        .selectinload(Doctor.user)
        .selectinload(User.files),
        selectinload(Appointment.doctor).selectinload(Doctor.license_certificate),
        selectinload(Appointment.doctor).selectinload(Doctor.department),
        selectinload(Appointment.availability),
        selectinload(Appointment.booked_by).selectinload(User.role),
        selectinload(Appointment.booked_by).selectinload(User.files),
        selectinload(Appointment.changed_times),
    )

    # Build filter conditions
    conditions = [Appointment.patient_id == patient.patient_id]

    if status:
        conditions.append(Appointment.status == status)

    # Date filtering through availability relationship
    if appointment_date:
        query = query.join(
            Availability, Appointment.availability_id == Availability.availability_id
        )
        conditions.append(func.date(Availability.start_date_time) == appointment_date)
    elif date_from or date_to:
        query = query.join(
            Availability, Appointment.availability_id == Availability.availability_id
        )
        if date_from:
            conditions.append(func.date(Availability.start_date_time) >= date_from)
        if date_to:
            conditions.append(func.date(Availability.start_date_time) <= date_to)

    # Apply all conditions
    query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(Appointment).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination (page is 1-indexed)
    skip = (page - 1) * size
    query = query.order_by(Appointment.created_at.desc())
    query = query.offset(skip).limit(size)

    # Execute query
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total


async def get_doctor_appointments(
    db: AsyncSession,
    user_id: str,
    status: Optional[AppointmentStatusEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    appointment_date: Optional[date] = None,
    page: int = 1,
    size: int = 100,
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
        page: Page number (1-indexed)
        size: Number of items per page

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
        selectinload(Appointment.patient)
        .selectinload(Patient.user)
        .selectinload(User.role),
        selectinload(Appointment.patient)
        .selectinload(Patient.user)
        .selectinload(User.files),
        selectinload(Appointment.doctor)
        .selectinload(Doctor.user)
        .selectinload(User.role),
        selectinload(Appointment.doctor)
        .selectinload(Doctor.user)
        .selectinload(User.files),
        selectinload(Appointment.doctor).selectinload(Doctor.license_certificate),
        selectinload(Appointment.doctor).selectinload(Doctor.department),
        selectinload(Appointment.availability),
        selectinload(Appointment.booked_by).selectinload(User.role),
        selectinload(Appointment.booked_by).selectinload(User.files),
        selectinload(Appointment.changed_times),
    )

    # Build filter conditions
    conditions = [Appointment.doctor_id == doctor.doctor_id]

    if status:
        conditions.append(Appointment.status == status)

    # Date filtering through availability relationship
    if appointment_date:
        query = query.join(
            Availability, Appointment.availability_id == Availability.availability_id
        )
        conditions.append(func.date(Availability.start_date_time) == appointment_date)
    elif date_from or date_to:
        query = query.join(
            Availability, Appointment.availability_id == Availability.availability_id
        )
        if date_from:
            conditions.append(func.date(Availability.start_date_time) >= date_from)
        if date_to:
            conditions.append(func.date(Availability.start_date_time) <= date_to)

    # Apply all conditions
    query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(Appointment).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply ordering and pagination (page is 1-indexed)
    skip = (page - 1) * size
    query = query.order_by(Appointment.created_at.desc())
    query = query.offset(skip).limit(size)

    # Execute query
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total


async def get_hospital_admin_appointments(
    db: AsyncSession,
    user_id: str,
    doctor_name: Optional[str] = None,
    patient_id: Optional[str] = None,
    patient_name: Optional[str] = None,
    status: Optional[AppointmentStatusEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    appointment_date: Optional[date] = None,
    page: int = 1,
    size: int = 100,
) -> tuple[list[Appointment], int]:
    """
    Get appointments for hospital admin (their hospital's appointments only).
    Can filter by doctor and patient within their hospital.

    Args:
        db: Database session
        user_id: User ID of the hospital admin
        doctor_name: Search by doctor name (must be in their hospital)
        patient_id: Filter by patient ID
        patient_name: Search by patient name (partial match)
        status: Filter by appointment status
        date_from: Filter appointments from this date (inclusive)
        date_to: Filter appointments up to this date (inclusive)
        appointment_date: Filter by specific appointment date
        page: Page number (1-indexed)
        size: Number of items per page

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
            selectinload(Appointment.patient)
            .selectinload(Patient.user)
            .selectinload(User.role),
            selectinload(Appointment.patient)
            .selectinload(Patient.user)
            .selectinload(User.files),
            selectinload(Appointment.doctor)
            .selectinload(Doctor.user)
            .selectinload(User.role),
            selectinload(Appointment.doctor)
            .selectinload(Doctor.user)
            .selectinload(User.files),
            selectinload(Appointment.doctor).selectinload(Doctor.license_certificate),
            selectinload(Appointment.doctor).selectinload(Doctor.department),
            selectinload(Appointment.availability),
            selectinload(Appointment.booked_by).selectinload(User.role),
            selectinload(Appointment.booked_by).selectinload(User.files),
            selectinload(Appointment.changed_times),
        )
    )

    # Build filter conditions - must be in their hospital
    conditions = [Doctor.hospital_id == hospital.hospital_id]

    if doctor_name:
        from sqlalchemy.orm import aliased

        DoctorUser = aliased(User)
        query = query.join(DoctorUser, Doctor.user_id == DoctorUser.user_id)
        conditions.append(DoctorUser.name.ilike(f"%{doctor_name}%"))

    if patient_id:
        conditions.append(Appointment.patient_id == patient_id)

    if patient_name:
        # Need alias if doctor_name was used
        if doctor_name:
            from sqlalchemy.orm import aliased

            PatientUser = aliased(User)
            query = query.join(Patient).join(
                PatientUser, Patient.user_id == PatientUser.user_id
            )
            conditions.append(PatientUser.name.ilike(f"%{patient_name}%"))
        else:
            query = query.join(Patient).join(User, Patient.user_id == User.user_id)
            conditions.append(User.name.ilike(f"%{patient_name}%"))

    if status:
        conditions.append(Appointment.status == status)

    # Date filtering through availability relationship
    if appointment_date:
        query = query.join(
            Availability, Appointment.availability_id == Availability.availability_id
        )
        conditions.append(func.date(Availability.start_date_time) == appointment_date)
    elif date_from or date_to:
        query = query.join(
            Availability, Appointment.availability_id == Availability.availability_id
        )
        if date_from:
            conditions.append(func.date(Availability.start_date_time) >= date_from)
        if date_to:
            conditions.append(func.date(Availability.start_date_time) <= date_to)

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

    # Apply ordering and pagination (page is 1-indexed)
    skip = (page - 1) * size
    query = query.order_by(Appointment.created_at.desc())
    query = query.offset(skip).limit(size)

    # Execute query
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total
