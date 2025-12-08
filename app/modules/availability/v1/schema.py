from datetime import date as date_type
from datetime import time
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AvailabilityCreateSchema(BaseModel):
    """Schema for creating a new availability slot"""

    doctor_id: str = Field(..., min_length=8, max_length=8)
    date: date_type
    start_time: time
    end_time: time
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("end_time")
    @classmethod
    def validate_end_time_after_start_time(cls, v, info):
        """Ensure end_time is after start_time"""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class AvailabilityUpdateSchema(BaseModel):
    """Schema for updating an existing availability slot"""

    date: Optional[date_type] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("end_time")
    @classmethod
    def validate_end_time_after_start_time(cls, v, info):
        """Ensure end_time is after start_time if both are provided"""
        if v and "start_time" in info.data and info.data["start_time"]:
            if v <= info.data["start_time"]:
                raise ValueError("end_time must be after start_time")
        return v


class DoctorBasicInfo(BaseModel):
    """Basic doctor info for availability response"""

    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    specialization_department: str
    experience_years: int


class AvailabilityResponseSchema(BaseModel):
    """Schema for availability response"""

    model_config = ConfigDict(from_attributes=True)

    availability_id: str
    doctor_id: str
    date: date_type
    start_time: time
    end_time: time
    note: Optional[str] = None
    doctor: DoctorBasicInfo


class AvailabilityListResponseSchema(BaseModel):
    """Schema for list of availabilities"""

    message: str = "Availabilities fetched successfully"
    data: list[AvailabilityResponseSchema]


class AvailabilityDetailResponseSchema(BaseModel):
    """Schema for single availability detail"""

    message: str = "Availability fetched successfully"
    data: AvailabilityResponseSchema
