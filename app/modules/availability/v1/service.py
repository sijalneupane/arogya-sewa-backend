from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.availability.v1.models import Availability
from app.modules.doctor.v1.models import Doctor
from app.modules.hospital.v1.models import Hospital


async def create_availability(
    db: AsyncSession,
    doctor_id: str,
    start_date_time: datetime,
    end_date_time: datetime,
    role: RoleEnum,
    auth_user_id: str,
    note: Optional[str] = None,
) -> Availability:
    """Create a new availability slot for a doctor"""
    try:
        # print("----- Reached service create_availability -----")
        await can_user_modify_availability(db, auth_user_id, doctor_id, role)
        # Check for overlapping availability
        print("----- Checking for overlapping availability -----")
        overlap_result = await db.execute(
            select(Availability).where(
                Availability.doctor_id == doctor_id,
                # Check for time overlap: new slot overlaps if it starts before existing ends
                # and ends after existing starts
                Availability.start_date_time < end_date_time,
                Availability.end_date_time > start_date_time,
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
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            note=note,
        )

        db.add(availability)
        await db.commit()
        await db.refresh(availability)

        # Return with doctor relationship loaded
        result = await db.execute(
            select(Availability)
            # .options(selectinload(Availability.doctor).selectinload(Doctor.user))
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
    page: int = 1,
    size: int = 10,
) -> tuple[List[Availability], int]:
    """Get all availabilities for a specific doctor"""
    # Verify doctor exists
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.doctor_id == doctor_id)
    )
    if not doctor_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Build query
    base_query = (
        select(Availability)
        .options(selectinload(Availability.doctor).selectinload(Doctor.user))
        .where(Availability.doctor_id == doctor_id)
    )

    # Filter for future dates if requested
    if future_only:
        now = datetime.now(timezone.utc)
        base_query = base_query.where(Availability.start_date_time >= now)

    # Filter by booking status if specified
    if is_booked is not None:
        base_query = base_query.where(Availability.is_booked == is_booked)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    query = (
        base_query.order_by(Availability.start_date_time)
        .offset((page - 1) * size)
        .limit(size)
    )

    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_availability_summary_by_doctor(
    db: AsyncSession, doctor_id: str
) -> dict[str, int]:
    """Get summary counts for all availabilities belonging to a doctor."""

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(
            func.count(Availability.availability_id).label("total_slots"),
            func.coalesce(
                func.sum(case((Availability.start_date_time >= now, 1), else_=0)), 0
            ).label("total_future_slots"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Availability.start_date_time >= now,
                                Availability.is_booked.is_(True),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("future_booked_slots"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Availability.start_date_time >= now,
                                Availability.is_booked.is_(False),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("future_open_slots"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Availability.start_date_time < now,
                                Availability.is_booked.is_(True),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_booked_slots_till_now"),
        ).where(Availability.doctor_id == doctor_id)
    )

    summary = result.one()
    return {
        "total_future_slots": int(summary.total_future_slots or 0),
        "future_booked_slots": int(summary.future_booked_slots or 0),
        "future_open_slots": int(summary.future_open_slots or 0),
        "total_booked_slots_till_now": int(summary.total_booked_slots_till_now or 0),
        "total_slots": int(summary.total_slots or 0),
    }


async def get_all_availabilities(
    db: AsyncSession,
    future_only: bool = True,
    is_booked: Optional[bool] = None,
    page: int = 1,
    size: int = 10,
) -> tuple[List[Availability], int]:
    """Get all availabilities across all doctors"""
    base_query = select(Availability).options(
        selectinload(Availability.doctor).selectinload(Doctor.user)
    )

    # Filter for future dates if requested
    if future_only:
        now = datetime.now(timezone.utc)
        base_query = base_query.where(Availability.start_date_time >= now)

    # Filter by booking status if specified
    if is_booked is not None:
        base_query = base_query.where(Availability.is_booked == is_booked)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    query = (
        base_query.order_by(Availability.start_date_time)
        .offset((page - 1) * size)
        .limit(size)
    )

    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_availability(
    db: AsyncSession,
    availability_id: str,
    role: RoleEnum,
    auth_user_id: str,
    start_date_time: Optional[datetime] = None,
    end_date_time: Optional[datetime] = None,
    note: Optional[str] = None,
) -> Availability:
    """Update an existing availability slot"""
    try:
        # Get existing availability
        availability = await get_availability_by_id(db, availability_id)
        if availability.is_booked:
            raise HTTPException(
                status_code=400,
                detail="Cannot update a booked availability slot. View appointment details instead.",
            )
        await can_user_modify_availability(
            db, auth_user_id, availability.doctor_id, role
        )

        # Prepare updated values
        updated_start = (
            start_date_time if start_date_time else availability.start_date_time
        )
        updated_end = end_date_time if end_date_time else availability.end_date_time

        # Validate times
        if updated_end <= updated_start:
            raise HTTPException(
                status_code=400, detail="end_date_time must be after start_date_time"
            )

        # Check for overlapping availability (excluding current record)
        overlap_result = await db.execute(
            select(Availability).where(
                and_(
                    Availability.doctor_id == availability.doctor_id,
                    Availability.availability_id != availability_id,
                    Availability.start_date_time < updated_end,
                    Availability.end_date_time > updated_start,
                )
            )
        )
        if overlap_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Updated availability slot overlaps with an existing slot",
            )

        # Update fields
        if start_date_time:
            availability.start_date_time = start_date_time
        if end_date_time:
            availability.end_date_time = end_date_time
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


async def delete_availability(
    db: AsyncSession, availability_id: str, role: RoleEnum, auth_user_id: str
) -> None:
    """Delete an availability slot"""
    try:
        availability = await get_availability_by_id(db, availability_id)
        if availability.is_booked:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete a booked availability slot. View appointment details instead.",
            )
        await can_user_modify_availability(
            db, auth_user_id, availability.doctor_id, role
        )
        await db.delete(availability)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def can_user_modify_availability(
    db: AsyncSession, authenticated_user_id: str, doctor_id: str, role: RoleEnum
):
    """Check if the user can modify availability for the given doctor"""

    if role is RoleEnum.DOCTOR:
        # If user is the doctor themselves
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.doctor_id == doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(
                status_code=404, detail="Doctor not found for doctor_id: " + doctor_id
            )
        if doctor.user_id != authenticated_user_id:
            raise HTTPException(
                status_code=403, detail="Authenticated doctor should match doctor_id"
            )
    # If user is a hospital admin
    elif role is RoleEnum.HOSPITAL_ADMIN:
        # Check if the hospital admin is from the same hospital as the doctor
        result = await db.execute(
            select(Doctor)
            .join(Hospital, Doctor.hospital_id == Hospital.hospital_id)
            .where(
                and_(
                    Doctor.doctor_id == doctor_id,
                    Hospital.admin_id == authenticated_user_id,
                )
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail="Authenticated hospital admin and provided doctor_id do not match for the same hospital",
            )
    # User is super admin or passed checks; allow modification
