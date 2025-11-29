from pydantic import BaseModel, EmailStr

from app.common.enums.role_enum import RoleEnum
from app.common.schema.role import RoleNameDesResponse


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: RoleEnum


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
