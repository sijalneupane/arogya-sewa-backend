from pydantic import BaseModel

from app.common.enums.role_enum import RoleEnum


class RoleNameDesResponse(BaseModel):
    role: RoleEnum
    description: str | None = None

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: str
    role: RoleEnum
    description: str | None = None

    class Config:
        from_attributes = True
