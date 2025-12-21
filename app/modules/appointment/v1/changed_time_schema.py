from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, Field


class AppointmentChangedTimeCreateSchema(BaseModel):
    """Schema for creating a changed time record"""

    appointment_id: str = Field(..., description="ID of the appointment")
    start_time: time = Field(..., description="New start time")
    end_time: time = Field(..., description="New end time")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for change")


class AppointmentChangedTimeUpdateSchema(BaseModel):
    """Schema for updating a changed time record"""

    start_time: Optional[time] = Field(None, description="New start time")
    end_time: Optional[time] = Field(None, description="New end time")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for change")


class AppointmentChangedTimeResponseSchema(BaseModel):
    """Schema for changed time response"""

    changed_time_id: str
    appointment_id: str
    start_time: time
    end_time: time
    reason: Optional[str]
    changed_at: datetime
    changed_by_user_id: str
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
