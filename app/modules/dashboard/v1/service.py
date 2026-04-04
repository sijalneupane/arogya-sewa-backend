from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils.string_utils import StringUtils
from app.modules.dashboard.v1.models import ActivityLog
from app.modules.dashboard.v1.schema import (
    ActivityLogCreate,
    ActivityLogResponse,
    DashboardActivityFilters,
)


async def create_activity_log(
    db: AsyncSession,
    activity_data: ActivityLogCreate,
) -> ActivityLog:
    """Create a new activity log entry."""
    # Generate activity log ID with "AL" prefix
    activity_log_id = f"AL_{StringUtils.randomAlphaNumeric(7)}"

    activity_log = ActivityLog(
        activity_log_id=activity_log_id,
        user_id=activity_data.user_id,
        hospital_id=activity_data.hospital_id,
        action_type=activity_data.action_type,
        entity_type=activity_data.entity_type,
        entity_id=activity_data.entity_id,
        description=activity_data.description,
        metadata_json=activity_data.metadata,
    )

    db.add(activity_log)
    await db.flush()  # Flush to get the ID without committing
    await db.refresh(activity_log)  # Refresh to get all fields
    return activity_log


async def get_recent_activities(
    db: AsyncSession,
    filters: DashboardActivityFilters,
    current_user_id: Optional[str] = None,
    current_user_hospital_id: Optional[str] = None,
) -> Tuple[List[ActivityLog], int]:
    """
    Get recent activities based on filters and user permissions.

    - For super admin: can see all activities
    - For hospital admin: can see activities for their hospital
    - For other users: can see their own activities
    """
    query = select(ActivityLog).options(selectinload(ActivityLog.user))

    # Apply filters
    conditions = []

    if filters.user_id:
        conditions.append(ActivityLog.user_id == filters.user_id)

    if filters.hospital_id:
        conditions.append(ActivityLog.hospital_id == filters.hospital_id)

    if filters.action_type:
        conditions.append(ActivityLog.action_type == filters.action_type)

    if filters.entity_type:
        conditions.append(ActivityLog.entity_type == filters.entity_type)

    if filters.start_date:
        conditions.append(ActivityLog.created_at >= filters.start_date)

    if filters.end_date:
        conditions.append(ActivityLog.created_at <= filters.end_date)

    # Apply permission-based filtering
    if current_user_hospital_id:
        # Hospital admin can only see activities for their hospital
        conditions.append(ActivityLog.hospital_id == current_user_hospital_id)
    elif current_user_id and not current_user_hospital_id:
        # Regular users can only see their own activities
        conditions.append(ActivityLog.user_id == current_user_id)
    # Super admin can see all activities (no additional conditions)

    if conditions:
        query = query.where(and_(*conditions))

    # Order by creation date (most recent first)
    query = query.order_by(desc(ActivityLog.created_at))

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    query = query.offset(offset).limit(filters.size)

    result = await db.execute(query)
    activities = list(result.scalars().all())

    # Get total count for pagination
    count_query = select(func.count()).select_from(ActivityLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return activities, total


async def get_system_recent_activities(
    db: AsyncSession,
    limit: int = 50,
) -> List[ActivityLog]:
    """
    Get recent activities across the entire system.
    Used for system-wide dashboard.
    """
    query = (
        select(ActivityLog)
        .options(selectinload(ActivityLog.user))
        .order_by(desc(ActivityLog.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_hospital_recent_activities(
    db: AsyncSession,
    hospital_id: str,
    limit: int = 50,
) -> List[ActivityLog]:
    """
    Get recent activities for a specific hospital.
    Used for hospital admin dashboard.
    """
    query = (
        select(ActivityLog)
        .options(selectinload(ActivityLog.user))
        .where(ActivityLog.hospital_id == hospital_id)
        .order_by(desc(ActivityLog.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


def build_activity_response(activity: ActivityLog) -> ActivityLogResponse:
    """Build ActivityLogResponse with user and hospital info."""
    response = ActivityLogResponse(
        activity_log_id=activity.activity_log_id,
        user_id=activity.user_id,
        hospital_id=activity.hospital_id,
        action_type=activity.action_type,
        entity_type=activity.entity_type,
        entity_id=activity.entity_id,
        description=activity.description,
        created_at=activity.created_at,
        metadata=activity.metadata_json,
    )

    # Add user info
    if activity.user:
        response.user_name = activity.user.name
        response.user_email = activity.user.email

    return response
