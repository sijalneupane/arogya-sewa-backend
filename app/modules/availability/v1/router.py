from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.availability.v1.schema import (
    AvailabilityCreateSchema,
    AvailabilityDetailResponseSchema,
    AvailabilityListResponseSchema,
    AvailabilityResponseSchema,
    AvailabilityUpdateSchema,
)
from app.modules.availability.v1.service import (
    can_user_modify_availability,
    create_availability,
    delete_availability,
    get_all_availabilities,
    get_availabilities_by_doctor,
    get_availability_by_id,
    update_availability,
)

router = APIRouter(
    prefix="/availabilities",
    tags=["Availabilities"],
)


@router.post("", summary="Create a new availability slot")
async def create_new_availability(
    data: AvailabilityCreateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AvailabilityDetailResponseSchema:
    """
    Create a new availability slot.
    Only the doctor themselves or their hospital admin can create availability.
    """
    # Check authorization
    can_modify = await can_user_modify_availability(db, user.sub, data.doctor_id)
    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to create availability for this doctor",
        )

    availability = await create_availability(
        db=db,
        doctor_id=data.doctor_id,
        availability_date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        note=data.note,
    )
    response = AvailabilityResponseSchema.model_validate(availability)
    return AvailabilityDetailResponseSchema(
        message="Availability created successfully", data=response
    )


@router.get("", summary="Get all availabilities")
async def get_availabilities(
    future_only: bool = Query(True, description="Filter for future dates only"),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityListResponseSchema:
    """Get all availability slots. Public endpoint - no authentication required."""
    availabilities = await get_all_availabilities(db=db, future_only=future_only)
    availability_responses = [
        AvailabilityResponseSchema.model_validate(avail) for avail in availabilities
    ]
    return AvailabilityListResponseSchema(data=availability_responses)


@router.get("/doctor/{doctor_id}", summary="Get availabilities for a specific doctor")
async def get_doctor_availabilities(
    doctor_id: str,
    future_only: bool = Query(True, description="Filter for future dates only"),
    db: AsyncSession = Depends(get_db),
) -> AvailabilityListResponseSchema:
    """Get all availability slots for a specific doctor. Public endpoint."""
    availabilities = await get_availabilities_by_doctor(
        db=db, doctor_id=doctor_id, future_only=future_only
    )
    availability_responses = [
        AvailabilityResponseSchema.model_validate(avail) for avail in availabilities
    ]
    return AvailabilityListResponseSchema(data=availability_responses)


@router.get("/{availability_id}", summary="Get a specific availability by ID")
async def get_availability(
    availability_id: str,
    db: AsyncSession = Depends(get_db),
) -> AvailabilityDetailResponseSchema:
    """Get a specific availability slot by ID. Public endpoint."""
    availability = await get_availability_by_id(db=db, availability_id=availability_id)
    response = AvailabilityResponseSchema.model_validate(availability)
    return AvailabilityDetailResponseSchema(data=response)


@router.patch("/{availability_id}", summary="Update an availability slot")
async def update_availability_endpoint(
    availability_id: str,
    data: AvailabilityUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> AvailabilityDetailResponseSchema:
    """
    Update an existing availability slot.
    Only the doctor themselves or their hospital admin can update.
    """
    # Get the availability to check doctor_id
    existing = await get_availability_by_id(db, availability_id)

    # Check authorization
    can_modify = await can_user_modify_availability(db, user.sub, existing.doctor_id)
    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this availability",
        )

    availability = await update_availability(
        db=db,
        availability_id=availability_id,
        availability_date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        note=data.note,
    )
    response = AvailabilityResponseSchema.model_validate(availability)
    return AvailabilityDetailResponseSchema(
        message="Availability updated successfully", data=response
    )


@router.delete("/{availability_id}", summary="Delete an availability slot")
async def delete_availability_endpoint(
    availability_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> dict:
    """
    Delete an availability slot.
    Only the doctor themselves or their hospital admin can delete.
    """
    # Get the availability to check doctor_id
    existing = await get_availability_by_id(db, availability_id)

    # Check authorization
    can_modify = await can_user_modify_availability(db, user.sub, existing.doctor_id)
    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this availability",
        )

    await delete_availability(db=db, availability_id=availability_id)
    return {"message": "Availability deleted successfully"}
