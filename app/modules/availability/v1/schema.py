from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AvailabilityCreateSchema(BaseModel):
    """Schema for creating a new availability slot"""

    doctor_id: str = Field(..., min_length=8, max_length=8)
    start_date_time: datetime
    end_date_time: datetime
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("end_date_time")
    @classmethod
    def validate_end_date_time_after_start(cls, v, info):
        """Ensure end_date_time is after start_date_time"""
        if "start_date_time" in info.data and v <= info.data["start_date_time"]:
            raise ValueError("end_date_time must be after start_date_time")
        return v


class AvailabilityUpdateSchema(BaseModel):
    """Schema for updating an existing availability slot"""

    start_date_time: Optional[datetime] = None
    end_date_time: Optional[datetime] = None
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("end_date_time")
    @classmethod
    def validate_end_date_time_after_start(cls, v, info):
        """Ensure end_date_time is after start_date_time if both are provided"""
        if v and "start_date_time" in info.data and info.data["start_date_time"]:
            if v <= info.data["start_date_time"]:
                raise ValueError("end_date_time must be after start_date_time")
        return v


class DoctorBasicInfo(BaseModel):
    """Basic doctor info for availability response"""

    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    name: str

    @model_validator(mode="before")
    @classmethod
    def extract_user_name(cls, data: Any) -> Any:
        """Extract name from nested user relationship if present"""
        if isinstance(data, dict):
            return data
        # Handle SQLAlchemy model instance
        if hasattr(data, "user") and hasattr(data.user, "name"):
            return {"doctor_id": data.doctor_id, "name": data.user.name}
        return data


class AvailabilityResponseSchema(BaseModel):
    """Schema for availability response"""

    model_config = ConfigDict(from_attributes=True)

    availability_id: str
    doctor_id: str
    start_date_time: datetime
    end_date_time: datetime
    note: Optional[str] = None
    is_booked: bool = False
    # doctor: DoctorBasicInfo


class AvailabilityListResponseSchema(BaseModel):
    """Schema for list of availabilities"""

    message: str = "Availabilities fetched successfully"
    data: list[AvailabilityResponseSchema]


class AvailabilityDetailResponseSchema(BaseModel):
    """Schema for single availability detail"""

    message: str = "Availability fetched successfully"
    data: AvailabilityResponseSchema
