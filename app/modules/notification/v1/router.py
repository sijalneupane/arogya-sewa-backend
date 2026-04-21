import math
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schema.pagination import (
    PaginatedResponse,
    PaginationMeta,
    PaginationQuery,
)
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload

from .schema import (
    NotificationReadAllResponse,
    NotificationResponseSchema,
    NotificationSendSchema,
    NotificationSingleResponse,
)
from .service import (
    list_notifications_for_user,
    mark_all_notifications_as_read,
    mark_notification_as_read,
    send_notification,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# @router.post("/create", summary="Create notification")
# async def create_notification_route(
#     data: NotificationCreateSchema,
#     db: AsyncSession = Depends(get_db),
#     _user: JwtPayload = Depends(get_current_user),
#     _=Depends(authorize),
# ) -> NotificationSingleResponse:
#     notification = await create_notification(
#         db=db,
#         receiver_user_id=data.receiver_user_id,
#         notification_type=data.type,
#         title=data.title,
#         body=data.body,
#         notification_data=data.notification_data,
#     )
#     response = NotificationResponseSchema.model_validate(notification)
#     return NotificationSingleResponse(
#         message="Notification created successfully",
#         data=response,
#     )


@router.post("/send", summary="Send notification")
async def send_notification_route(
    data: NotificationSendSchema,
    db: AsyncSession = Depends(get_db),
    _user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> NotificationSingleResponse:
    notification = await send_notification(
        db=db,
        receiver_user_id=data.receiver_user_id,
        notification_type=data.type,
        title=data.title,
        body=data.body,
        notification_data=data.notification_data,
    )
    response = NotificationResponseSchema.model_validate(notification)
    return NotificationSingleResponse(
        message="Notification sent successfully",
        data=response,
    )


@router.get("/me", summary="Get my notifications")
async def get_my_notifications(
    unread_only: bool = Query(False, description="Return only unread notifications"),
    pagination: PaginationQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> PaginatedResponse[List[NotificationResponseSchema]]:
    notifications, total = await list_notifications_for_user(
        db=db,
        user_id=user.sub,
        page=pagination.page,
        size=pagination.size,
        unread_only=unread_only,
    )
    data = [NotificationResponseSchema.model_validate(item) for item in notifications]
    return PaginatedResponse(
        message="Notifications fetched successfully",
        data=data,
        paginationMeta=PaginationMeta(
            totalPage=math.ceil(total / pagination.size) if total else 0,
            currentPage=pagination.page,
            pageSize=pagination.size,
            totalRecords=total,
        ),
    )


@router.patch("/{notification_id}/read", summary="Mark notification as read")
async def mark_as_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> NotificationSingleResponse:
    notification = await mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        user_id=user.sub,
    )
    response = NotificationResponseSchema.model_validate(notification)
    return NotificationSingleResponse(
        message="Notification marked as read",
        data=response,
    )


@router.patch("/read-all/me", summary="Mark all notifications as read for current user")
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> NotificationReadAllResponse:
    count = await mark_all_notifications_as_read(
        db=db,
        user_id=user.sub,
    )
    return NotificationReadAllResponse(
        message=f"{count} notification(s) marked as read",
        data={"count": count},
    )
