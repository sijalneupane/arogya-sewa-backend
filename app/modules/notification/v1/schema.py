from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums.notification_type_enum import NotificationTypeEnum
from app.modules.user.v1.schema import UserResponse


class NotificationCreateSchema(BaseModel):
    type: NotificationTypeEnum
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    notification_data: Optional[dict[str, Any]] = None
    receiver_user_id: str = Field(..., min_length=8, max_length=8)


class NotificationSendSchema(NotificationCreateSchema):
    pass


class NotificationMarkReadSchema(BaseModel):
    has_read: bool = True


class NotificationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: str
    type: NotificationTypeEnum
    title: str
    body: str
    notification_data: Optional[dict[str, Any]] = None
    has_read: bool
    receiver_user_id: str
    receiver: Optional[UserResponse] = None
    created_at: datetime
    updated_at: datetime


class NotificationSingleResponse(BaseModel):
    message: str = "Notification processed successfully"
    data: NotificationResponseSchema
