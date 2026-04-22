from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schema.pagination import (
    PaginatedResponse,
    PaginationMeta,
    PaginationQuery,
)
from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.availability.v1.schema import (
    AvailabilityCreateSchema,
    AvailabilityDetailResponseSchema,
    DoctorFutureAvailabilityListResponseSchema,
    FutureAvailabilitySummarySchema,
    AvailabilityResponseSchema,
    AvailabilityUpdateSchema,
)
from app.modules.availability.v1.service import (
    # can_user_modify_availability,
    create_availability,
    delete_availability,
    get_availability_summary_by_doctor,
    get_all_availabilities,
    get_availabilities_by_doctor,
    get_availability_by_id,
    update_availability,
)
from app.modules.doctor.v1.service import get_doctor_by_user_id

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

    availability = await create_availability(
        db=db,
        doctor_id=data.doctor_id,
        start_date_time=data.start_date_time,
        end_date_time=data.end_date_time,
        role=user.role,
        auth_user_id=user.sub,
        note=data.note,
    )
    response = AvailabilityResponseSchema.model_validate(availability)
    return AvailabilityDetailResponseSchema(
        message="Availability created successfully", data=response
    )


@router.get("", summary="Get all availabilities")
async def get_availabilities(
    future_only: bool = Query(True, description="Filter for future dates only"),
    is_booked: Optional[bool] = Query(
        None,
        description="Filter by booking status (True for booked, False for available)",
    ),
    pagination: PaginationQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[AvailabilityResponseSchema]]:
    """Get all availability slots. Public endpoint - no authentication required."""
    availabilities, total = await get_all_availabilities(
        db=db,
        future_only=future_only,
        is_booked=is_booked,
        page=pagination.page,
        size=pagination.size,
    )
    availability_responses = [
        AvailabilityResponseSchema.model_validate(avail) for avail in availabilities
    ]
    total_pages = (total + pagination.size - 1) // pagination.size if total > 0 else 0
    return PaginatedResponse(
        message="Availabilities fetched successfully",
        data=availability_responses,
        paginationMeta=PaginationMeta(
            totalPage=total_pages,
            currentPage=pagination.page,
            pageSize=pagination.size,
            totalRecords=total,
        ),
    )


@router.get("/doctor/{doctor_id}", summary="Get availabilities for a specific doctor")
async def get_doctor_availabilities(
    doctor_id: str,
    future_only: bool = Query(True, description="Filter for future dates only"),
    is_booked: Optional[bool] = Query(
        None,
        description="Filter by booking status (True for booked, False for available)",
    ),
    pagination: PaginationQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[AvailabilityResponseSchema]]:
    """Get all availability slots for a specific doctor. Public endpoint."""
    availabilities, total = await get_availabilities_by_doctor(
        db=db,
        doctor_id=doctor_id,
        future_only=future_only,
        is_booked=is_booked,
        page=pagination.page,
        size=pagination.size,
    )
    availability_responses = [
        AvailabilityResponseSchema.model_validate(avail) for avail in availabilities
    ]
    total_pages = (total + pagination.size - 1) // pagination.size if total > 0 else 0
    return PaginatedResponse(
        message="Availabilities fetched successfully",
        data=availability_responses,
        paginationMeta=PaginationMeta(
            totalPage=total_pages,
            currentPage=pagination.page,
            pageSize=pagination.size,
            totalRecords=total,
        ),
    )


@router.get("/me", summary="Get availabilities for the logged-in doctor")
async def get_my_availabilities(
    future_only: bool = Query(True, description="Filter for future dates only"),
    is_booked: Optional[bool] = Query(
        None,
        description="Filter by booking status (True for booked, False for available)",
    ),
    pagination: PaginationQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> DoctorFutureAvailabilityListResponseSchema:
    """Get future availability slots for the logged-in doctor with summary counts."""

    doctor = await get_doctor_by_user_id(db=db, user_id=user.sub)
    availabilities, total = await get_availabilities_by_doctor(
        db=db,
        doctor_id=doctor.doctor_id,
        future_only=future_only,
        is_booked=is_booked,
        page=pagination.page,
        size=pagination.size,
    )
    future_summary = FutureAvailabilitySummarySchema.model_validate(
        await get_availability_summary_by_doctor(db=db, doctor_id=doctor.doctor_id)
    )
    availability_responses = [
        AvailabilityResponseSchema.model_validate(avail) for avail in availabilities
    ]
    total_pages = (total + pagination.size - 1) // pagination.size if total > 0 else 0
    return DoctorFutureAvailabilityListResponseSchema(
        message="Availabilities fetched successfully",
        data=availability_responses,
        future_summary=future_summary,
        paginationMeta=PaginationMeta(
            totalPage=total_pages,
            currentPage=pagination.page,
            pageSize=pagination.size,
            totalRecords=total,
        ),
    )


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

    availability = await update_availability(
        db=db,
        role=user.role,
        auth_user_id=user.sub,
        availability_id=availability_id,
        start_date_time=data.start_date_time,
        end_date_time=data.end_date_time,
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

    await delete_availability(
        db=db, availability_id=availability_id, role=user.role, auth_user_id=user.sub
    )
    return {"message": "Availability deleted successfully"}
