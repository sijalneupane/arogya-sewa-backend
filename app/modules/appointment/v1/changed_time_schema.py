from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.user.v1.schema import UserResponse


class AppointmentChangedTimeCreateSchema(BaseModel):
    """Schema for creating a changed time record"""

    appointment_id: str = Field(..., description="ID of the appointment")
    start_date_time: datetime = Field(..., description="New start datetime")
    end_date_time: datetime = Field(..., description="New end datetime")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for change")


class AppointmentChangedTimeUpdateSchema(BaseModel):
    """Schema for updating a changed time record"""

    start_date_time: Optional[datetime] = Field(None, description="New start datetime")
    end_date_time: Optional[datetime] = Field(None, description="New end datetime")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for change")


class AppointmentChangedTimeSingleInfoSchema(BaseModel):
    """Schema for single changed time info"""

    changed_time_id: str
    appointment_id: str
    start_date_time: datetime
    end_date_time: datetime
    reason: Optional[str]
    changed_at: datetime
    changed_by_user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentChangedTimeResponseSchema(BaseModel):
    """Schema for changed time response"""

    changed_time_id: str
    appointment_id: str
    start_date_time: datetime
    end_date_time: datetime
    reason: Optional[str]
    changed_at: datetime
    changed_by: UserResponse  # Full user information of who changed the time
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentChangedTimeSingleResponse(BaseModel):
    """Single changed time response wrapper"""

    message: str
    data: AppointmentChangedTimeResponseSchema


class AppointmentChangedTimeListResponse(BaseModel):
    """List of changed times response wrapper"""

    message: str
    data: list[AppointmentChangedTimeResponseSchema]
