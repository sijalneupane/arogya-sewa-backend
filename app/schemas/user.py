from pydantic import BaseModel, EmailStr

from app.enums.role_enum import RoleEnum


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
    is_active: bool

    class Config:
        from_attributes = True
