from pydantic import BaseModel, EmailStr, Field

from app.common.enums.role_enum import RoleEnum
from app.modules.user.v1.schema import UserResponse


class JwtPayload(BaseModel):
    sub: str
    role: RoleEnum
    name: str


class LoginData(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


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
