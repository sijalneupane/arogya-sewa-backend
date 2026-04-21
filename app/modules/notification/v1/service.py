import logging
from typing import Any, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.notification_type_enum import NotificationTypeEnum
from app.core.utils.string_utils import StringUtils
from app.modules.firebase.service import send_push
from app.modules.notification.v1.models import Notification
from app.modules.user.v1.models import User

logger = logging.getLogger(__name__)


def _stringify_notification_data(data: Optional[dict[str, Any]]) -> dict[str, str]:
    if not data:
        return {}
    return {str(k): str(v) for k, v in data.items()}


async def create_notification(
    db: AsyncSession,
    receiver_user_id: str,
    notification_type: NotificationTypeEnum,
    title: str,
    body: str,
    notification_data: Optional[dict[str, Any]] = None,
) -> Notification:
    receiver_result = await db.execute(select(User).where(User.id == receiver_user_id))
    receiver = receiver_result.scalar_one_or_none()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver user not found")

    notification = Notification(
        notification_id=StringUtils.randomAlphaNumeric(12),
        type=notification_type,
        title=title,
        body=body,
        notification_data=notification_data,
        receiver_user_id=receiver_user_id,
    )

    db.add(notification)
    await db.commit()

    result = await db.execute(
        select(Notification)
        .options(
            selectinload(Notification.receiver).selectinload(User.role),
            selectinload(Notification.receiver).selectinload(User.files),
        )
        .where(Notification.notification_id == notification.notification_id)
    )
    return result.scalar_one()


async def send_notification(
    db: AsyncSession,
    receiver_user_id: str,
    notification_type: NotificationTypeEnum,
    title: str,
    body: str,
    notification_data: Optional[dict[str, Any]] = None,
) -> Notification:
    notification = await create_notification(
        db=db,
        receiver_user_id=receiver_user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        notification_data=notification_data,
    )

    receiver = notification.receiver
    fcm_token = receiver.fcm_token if receiver else None

    if fcm_token:
        try:
            send_push(
                token=fcm_token,
                title=title,
                body=body,
                data=_stringify_notification_data(notification_data),
            )
        except Exception as exc:
            logger.warning(
                "Notification saved but FCM push failed for user %s: %s",
                receiver_user_id,
                str(exc),
            )
    else:
        logger.info(
            "Notification saved but no FCM token found for user %s",
            receiver_user_id,
        )

    return notification


async def list_notifications_for_user(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    size: int = 10,
    unread_only: bool = False,
) -> Tuple[list[Notification], int]:
    base_query = (
        select(Notification)
        .options(
            selectinload(Notification.receiver).selectinload(User.role),
            selectinload(Notification.receiver).selectinload(User.files),
        )
        .where(Notification.receiver_user_id == user_id)
        .order_by(Notification.created_at.desc())
    )

    if unread_only:
        base_query = base_query.where(Notification.has_read.is_(False))

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(base_query.offset((page - 1) * size).limit(size))
    return list(result.scalars().all()), total


async def mark_notification_as_read(
    db: AsyncSession,
    notification_id: str,
    user_id: str,
) -> Notification:
    result = await db.execute(
        select(Notification)
        .options(
            selectinload(Notification.receiver).selectinload(User.role),
            selectinload(Notification.receiver).selectinload(User.files),
        )
        .where(
            Notification.notification_id == notification_id,
            Notification.receiver_user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.has_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_all_notifications_as_read(
    db: AsyncSession,
    user_id: str,
) -> int:
    """
    Mark all unread notifications as read for a user.

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        int: Count of notifications marked as read
    """
    # Get count of unread notifications
    count_result = await db.execute(
        select(func.count(Notification.notification_id)).where(
            Notification.receiver_user_id == user_id,
            Notification.has_read.is_(False),
        )
    )
    count = count_result.scalar_one()

    # Update all unread notifications to read
    await db.execute(
        select(Notification).where(
            Notification.receiver_user_id == user_id,
            Notification.has_read.is_(False),
        )
    )

    result = await db.execute(
        select(Notification).where(
            Notification.receiver_user_id == user_id,
            Notification.has_read.is_(False),
        )
    )
    notifications = result.scalars().all()

    for notification in notifications:
        notification.has_read = True

    await db.commit()

    return count
