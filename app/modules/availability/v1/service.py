from datetime import date, time
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.availability.v1.models import Availability
from app.modules.doctor.v1.models import Doctor
from app.modules.user.v1.models import User


async def create_availability(
    db: AsyncSession,
    doctor_id: str,
    availability_date: date,
    start_time: time,
    end_time: time,
    note: Optional[str] = None,
) -> Availability:
    """Create a new availability slot for a doctor"""
    try:
        # Verify doctor exists
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.doctor_id == doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # Check for overlapping availability on the same date
        overlap_result = await db.execute(
            select(Availability).where(
                and_(
                    Availability.doctor_id == doctor_id,
                    Availability.date == availability_date,
                    # Check for time overlap: new slot overlaps if it starts before existing ends
                    # and ends after existing starts
                    Availability.start_time < end_time,
                    Availability.end_time > start_time,
                )
            )
        )
        overlapping = overlap_result.scalar_one_or_none()
        if overlapping:
            raise HTTPException(
                status_code=400,
                detail="Availability slot overlaps with an existing slot"
                + overlapping.availability_id,
            )

        # Create availability
        availability = Availability(
            availability_id=StringUtils.randomAlphaNumeric(8),
            doctor_id=doctor_id,
            date=availability_date,
            start_time=start_time,
            end_time=end_time,
            note=note,
        )

        db.add(availability)
        await db.commit()
        await db.refresh(availability)

        # Return with doctor relationship loaded
        result = await db.execute(
            select(Availability)
            .options(selectinload(Availability.doctor).selectinload(Doctor.user))
            .where(Availability.availability_id == availability.availability_id)
        )
        return result.scalar_one()

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def get_availability_by_id(
    db: AsyncSession, availability_id: str
) -> Availability:
    """Get a specific availability by ID"""
    result = await db.execute(
        select(Availability)
        .options(selectinload(Availability.doctor).selectinload(Doctor.user))
        .where(Availability.availability_id == availability_id)
    )
    availability = result.scalar_one_or_none()
    if not availability:
        raise HTTPException(status_code=404, detail="Availability not found")
    return availability


async def get_availabilities_by_doctor(
    db: AsyncSession,
    doctor_id: str,
    future_only: bool = True,
    is_booked: Optional[bool] = None,
) -> List[Availability]:
    """Get all availabilities for a specific doctor"""
    # Verify doctor exists
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.doctor_id == doctor_id)
    )
    if not doctor_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Build query
    query = (
        select(Availability)
        .options(selectinload(Availability.doctor).selectinload(Doctor.user))
        .where(Availability.doctor_id == doctor_id)
    )

    # Filter for future dates if requested
    if future_only:
        from datetime import date as date_class

        today = date_class.today()
        query = query.where(Availability.date >= today)

    # Filter by booking status if specified
    if is_booked is not None:
        query = query.where(Availability.is_booked == is_booked)

    query = query.order_by(Availability.date, Availability.start_time)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_all_availabilities(
    db: AsyncSession, future_only: bool = True, is_booked: Optional[bool] = None
) -> List[Availability]:
    """Get all availabilities across all doctors"""
    query = select(Availability).options(
        selectinload(Availability.doctor).selectinload(Doctor.user)
    )

    # Filter for future dates if requested
    if future_only:
        from datetime import date as date_class

        today = date_class.today()
        query = query.where(Availability.date >= today)

    # Filter by booking status if specified
    if is_booked is not None:
        query = query.where(Availability.is_booked == is_booked)

    query = query.order_by(Availability.date, Availability.start_time)

    result = await db.execute(query)
    return list(result.scalars().all())


async def update_availability(
    db: AsyncSession,
    availability_id: str,
    availability_date: Optional[date] = None,
    start_time: Optional[time] = None,
    end_time: Optional[time] = None,
    note: Optional[str] = None,
) -> Availability:
    """Update an existing availability slot"""
    try:
        # Get existing availability
        availability = await get_availability_by_id(db, availability_id)

        # Prepare updated values
        updated_date = availability_date if availability_date else availability.date
        updated_start = start_time if start_time else availability.start_time
        updated_end = end_time if end_time else availability.end_time

        # Validate times
        if updated_end <= updated_start:
            raise HTTPException(
                status_code=400, detail="end_time must be after start_time"
            )

        # Check for overlapping availability (excluding current record)
        overlap_result = await db.execute(
            select(Availability).where(
                and_(
                    Availability.doctor_id == availability.doctor_id,
                    Availability.availability_id != availability_id,
                    Availability.date == updated_date,
                    Availability.start_time < updated_end,
                    Availability.end_time > updated_start,
                )
            )
        )
        if overlap_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Updated availability slot overlaps with an existing slot",
            )

        # Update fields
        if availability_date:
            availability.date = availability_date
        if start_time:
            availability.start_time = start_time
        if end_time:
            availability.end_time = end_time
        if note is not None:  # Allow clearing note by passing empty string
            availability.note = note

        await db.commit()
        await db.refresh(availability)

        # Return with relationships loaded
        result = await db.execute(
            select(Availability)
            .options(selectinload(Availability.doctor))
            .where(Availability.availability_id == availability_id)
        )
        return result.scalar_one()

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def delete_availability(db: AsyncSession, availability_id: str) -> None:
    """Delete an availability slot"""
    try:
        availability = await get_availability_by_id(db, availability_id)
        await db.delete(availability)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def can_user_modify_availability(
    db: AsyncSession, user_id: str, doctor_id: str
) -> bool:
    """
    Check if a user can modify availability for a doctor.
    Returns True if:
    - User is the doctor themselves
    - User is a hospital admin for the doctor's hospital
    """
    # Get user with role and relationships
    user_result = await db.execute(
        select(User)
        .options(
            selectinload(User.role),
            selectinload(User.doctor),
            selectinload(User.hospital),
        )
        .where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return False

    # Check if user is the doctor
    if user.doctor and user.doctor.doctor_id == doctor_id:
        return True

    # Check if user is hospital admin for doctor's hospital
    if user.hospital and user.role.role == RoleEnum.HOSPITAL_ADMIN:
        # Get the doctor's hospital
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.doctor_id == doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if doctor and doctor.hospital_id == user.hospital.hospital_id:
            return True

    return False
