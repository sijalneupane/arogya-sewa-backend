from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy import inspect

from app.common.enums.doctor_status_enum import DoctorStatusEnum
from app.common.enums.role_enum import RoleEnum
from app.modules.user.v1.schema import BloodGroupEnum, GenderEnum, UserResponse


class JwtPayload(BaseModel):
    sub: str
    role: RoleEnum
    name: str


class LoginData(BaseModel):
    access_token: str
    refresh_token: str
    user: "AuthenticatedUserResponse"


class LoginResponse(BaseModel):
    message: str = "Login successful"
    data: LoginData


class AuthMessageResponse(BaseModel):
    message: str


class SendPasswordResetOtpRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=30)
    confirm_password: str = Field(..., min_length=6, max_length=30)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=30)
    new_password: str = Field(..., min_length=6, max_length=30)
    confirm_password: str = Field(..., min_length=6, max_length=30)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenData(BaseModel):
    access_token: str
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    message: str = "Token refreshed successfully"
    data: RefreshTokenData


class DoctorAuthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    user_id: str
    experience: str
    status: DoctorStatusEnum
    bio: str | None = None
    booking_fee: float
    license_certificate_id: str | None = None
    hospital_id: str | None = None
    department_id: str | None = None
    created_at: datetime
    updated_at: datetime


class PatientAuthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    user_id: str
    dob: date
    gender: GenderEnum
    blood_group: BloodGroupEnum
    created_at: datetime
    updated_at: datetime


class AuthenticatedUserResponse(UserResponse):
    model_config = ConfigDict(from_attributes=True)

    doctor: DoctorAuthResponse | None = None
    patient: PatientAuthResponse | None = None

    @model_validator(mode="before")
    @classmethod
    def build_from_user_model(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data

        state = inspect(data)
        loaded_values = state.dict
        return {
            "id": loaded_values.get("id"),
            "email": loaded_values.get("email"),
            "name": loaded_values.get("name"),
            "phone_number": loaded_values.get("phone_number"),
            "role": loaded_values.get("role"),
            "is_active": loaded_values.get("is_active"),
            "created_at": loaded_values.get("created_at"),
            "updated_at": loaded_values.get("updated_at"),
            "files": loaded_values.get("files", []),
            "doctor": loaded_values.get("doctor"),
            "patient": loaded_values.get("patient"),
        }


class AuthUserByIdResponse(BaseModel):
    message: str = "User fetched successfully"
    data: AuthenticatedUserResponse | None = None
