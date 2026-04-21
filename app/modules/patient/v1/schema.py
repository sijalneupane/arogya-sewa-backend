from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from app.modules.user.v1.schema import UserResponse, GenderEnum, BloodGroupEnum


class PatientCreate(BaseModel):
    dob: date
    gender: str
    blood_group: str


class UserUpdateForPatient(BaseModel):
    """Schema for user fields that can be updated"""

    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=5, max_length=30)
    phone_number: Optional[str] = Field(
        None, min_length=10, max_length=10, pattern=r"^9\d{9}$"
    )


class PatientUpdate(BaseModel):
    """Schema for patient profile update"""

    dob: Optional[date] = None
    gender: Optional[GenderEnum] = None
    blood_group: Optional[BloodGroupEnum] = None
    user: Optional[UserUpdateForPatient] = None


class PatientUpdateResponse(BaseModel):
    message: str
    data: Optional["PatientResponse"] = None


class PatientResponse(BaseModel):
    patient_id: str
    dob: date
    gender: GenderEnum
    blood_group: BloodGroupEnum
    user: UserResponse

    class Config:
        from_attributes = True
