from datetime import date
from enum import StrEnum
from pydantic import BaseModel, EmailStr, Field

from app.common.enums.role_enum import RoleEnum
from app.common.schema.role import RoleNameDesResponse


class GenderEnum(StrEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class BloodGroupEnum(StrEnum):
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=5, max_length=14)
    phone_number: str = Field(..., min_length=10, max_length=10)
    password: str = Field(..., min_length=6, max_length=20)
    role: RoleEnum


class PatientSignupSchema(BaseModel):
    """Schema for patient signup - creates both user and patient records"""

    email: EmailStr
    name: str = Field(..., min_length=5, max_length=14)
    phone_number: str = Field(..., min_length=10, max_length=10)
    password: str = Field(..., min_length=6, max_length=20)
    dob: date
    gender: GenderEnum
    blood_group: BloodGroupEnum


class DoctorSignupSchema(BaseModel):
    """Schema for doctor signup - creates both user and doctor records"""

    email: EmailStr
    name: str = Field(..., min_length=5, max_length=14)
    phone_number: str = Field(..., min_length=10, max_length=10)
    password: str = Field(..., min_length=6, max_length=20)
    specialization_department: str
    experience_years: int
    license_certificate: str


class SuperAdminSignupSchema(BaseModel):
    """Schema for super admin signup - only creates user record"""

    email: EmailStr
    name: str = Field(..., min_length=5, max_length=14)
    phone_number: str = Field(..., min_length=10, max_length=10)
    password: str = Field(..., min_length=6, max_length=20)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    phone_number: str
    role: RoleNameDesResponse
    is_active: bool

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    message: str | None = "User list fetched successfully"
    data: list[UserResponse] | None


class UserByIdResponse(BaseModel):
    message: str | None = "User fetched successfully"
    data: UserResponse | None


class SignupResponse(BaseModel):
    message: str
    data: UserResponse
