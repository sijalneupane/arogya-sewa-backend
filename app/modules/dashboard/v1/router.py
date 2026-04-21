from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums.role_enum import RoleEnum
from app.common.schema.pagination import PaginatedResponse, PaginationMeta
from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.dashboard.v1.schema import (
    ActivityLogResponse,
    DashboardActivityFilters,
    DoctorAppointmentFeedResponse,
    DoctorDashboardSummaryResponse,
    HospitalAdminDashboardSummary,
    SuperAdminDashboardSummary,
)
from app.modules.dashboard.v1.service import (
    build_activity_response,
    get_doctor_dashboard_summary,
    get_doctor_today_appointments_feed,
    get_doctor_upcoming_appointments_feed,
    get_hospital_admin_dashboard_summary,
    get_hospital_recent_activities,
    get_recent_activities,
    get_super_admin_dashboard_summary,
    get_system_recent_activities,
)
from app.modules.hospital.v1.service import get_hospital_by_admin_id

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary")
async def get_super_admin_dashboard_details(
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _: bool = Depends(authorize),
) -> SuperAdminDashboardSummary:
    """Get consolidated dashboard summary for super admin."""
    return await get_super_admin_dashboard_summary(db)


@router.get("/activities/system")
@router.get("/hospital-admin/summary")
async def get_hospital_admin_dashboard_details(
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _: bool = Depends(authorize),
) -> HospitalAdminDashboardSummary:
    """Get consolidated dashboard summary for a hospital admin's own hospital."""
    if current_user.role != RoleEnum.HOSPITAL_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only hospital admin can view hospital dashboard summary",
        )

    hospital = await get_hospital_by_admin_id(db, current_user.sub)
    return await get_hospital_admin_dashboard_summary(db, hospital.hospital_id)


@router.get("/doctor/summary")
async def get_doctor_dashboard_details(
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _: bool = Depends(authorize),
) -> DoctorDashboardSummaryResponse:
    """Get consolidated dashboard summary for a doctor."""
    if current_user.role != RoleEnum.DOCTOR:
        raise HTTPException(
            status_code=403,
            detail="Only doctor can view doctor dashboard summary",
        )

    return await get_doctor_dashboard_summary(db, current_user.sub)


@router.get("/doctor/upcoming-appointments")
async def get_doctor_upcoming_appointments(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _: bool = Depends(authorize),
) -> DoctorAppointmentFeedResponse:
    """Get upcoming appointments for the logged-in doctor, ordered by nearest start time."""
    if current_user.role != RoleEnum.DOCTOR:
        raise HTTPException(
            status_code=403,
            detail="Only doctor can view upcoming appointments",
        )

    return await get_doctor_upcoming_appointments_feed(db, current_user.sub, limit)


@router.get("/doctor/today-appointments")
async def get_doctor_today_appointments(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _: bool = Depends(authorize),
) -> DoctorAppointmentFeedResponse:
    """Get today's appointments for the logged-in doctor, ordered by start time."""
    if current_user.role != RoleEnum.DOCTOR:
        raise HTTPException(
            status_code=403,
            detail="Only doctor can view today's appointments",
        )

    return await get_doctor_today_appointments_feed(db, current_user.sub, limit)


async def get_system_activities(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _: bool = Depends(authorize),
) -> list[ActivityLogResponse]:
    """
    Get recent activities across the entire system.
    Only accessible by super admins.
    """
    if current_user.role != RoleEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=403, detail="Only super admin can view system activities"
        )

    activities = await get_system_recent_activities(db, limit)
    return [build_activity_response(activity) for activity in activities]


@router.get("/activities/hospital/{hospital_id}")
async def get_hospital_activities(
    hospital_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _: bool = Depends(authorize),
) -> list[ActivityLogResponse]:
    """
    Get recent activities for a specific hospital.
    Accessible by super admins and the hospital admin.
    """
    if current_user.role == RoleEnum.SUPER_ADMIN:
        pass
    elif current_user.role == RoleEnum.HOSPITAL_ADMIN:
        own_hospital = await get_hospital_by_admin_id(db, current_user.sub)
        if own_hospital.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="Hospital admins can only view their own hospital activities",
            )
    else:
        raise HTTPException(
            status_code=403, detail="Only admin users can view hospital activities"
        )

    activities = await get_hospital_recent_activities(db, hospital_id, limit)
    return [build_activity_response(activity) for activity in activities]


@router.get("/activities")
async def get_activities(
    filters: DashboardActivityFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _: bool = Depends(authorize),
) -> PaginatedResponse[list[ActivityLogResponse]]:
    """
    Get paginated activities based on user permissions and filters.

    - Super admins: see all activities
    - Hospital admins: see activities for their hospital
    - Other users: see their own activities
    """
    current_user_hospital_id = None
    if current_user.role == RoleEnum.HOSPITAL_ADMIN:
        own_hospital = await get_hospital_by_admin_id(db, current_user.sub)
        current_user_hospital_id = own_hospital.hospital_id

    activities, total = await get_recent_activities(
        db,
        filters,
        None if current_user.role == RoleEnum.SUPER_ADMIN else current_user.sub,
        current_user_hospital_id,
    )

    activity_responses = [build_activity_response(activity) for activity in activities]
    total_pages = (total + filters.size - 1) // filters.size if total > 0 else 0

    return PaginatedResponse(
        message="Activities fetched successfully",
        data=activity_responses,
        paginationMeta=PaginationMeta(
            totalPage=total_pages,
            currentPage=filters.page,
            pageSize=filters.size,
            totalRecords=total,
        ),
    )
