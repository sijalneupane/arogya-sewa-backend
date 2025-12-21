from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.file.v1.schemas import FileResponseSchema
from app.modules.user.v1.schema import UserCreate, UserResponse


class HospitalCreateSchema(BaseModel):
    name: str
    location: str
    latitude: float
    longitude: float
    contact_number: list[str]
    opened_date: date = Field(
        ..., description="ISO 8601 date (YYYY-MM-DD)", examples=["2023-10-15"]
    )
    hospital_license_id: str
    admin_details: UserCreate


class HospitalUpdateSchema(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_number: Optional[list[str]] = None
    opened_date: Optional[date] = Field(
        None, description="ISO 8601 date (YYYY-MM-DD)", examples=["2023-10-15"]
    )
    hospital_license_id: Optional[str] = None


class HospitalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str
    name: str
    location: str
    latitude: float
    longitude: float
    contact_number: list[str]
    opened_date: date  # ISO 8601 date (YYYY-MM-DD)
    created_at: datetime
    updated_at: datetime
    admin: UserResponse
    hospital_license: Optional[FileResponseSchema] = None


class HospitalListResponseSchema(BaseModel):
    message: str = "Hospitals fetched successfully"
    data: list[HospitalResponseSchema]


class HospitalDetailResponseSchema(BaseModel):
    message: str = "Hospital fetched successfully"
    data: HospitalResponseSchema


class AdminHospitalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str
    name: str
    location: str
    latitude: float
    longitude: float
    contact_number: list[str]
    opened_date: date  # ISO 8601 date (YYYY-MM-DD)
    created_at: datetime
    updated_at: datetime
    hospital_license: Optional[FileResponseSchema] = None


class AdminHospitalDetailResponseSchema(BaseModel):
    message: str = "Hospital fetched successfully"
    data: AdminHospitalResponseSchema
