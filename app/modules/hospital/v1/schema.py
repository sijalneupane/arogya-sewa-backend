from pydantic import BaseModel

from app.modules.user.v1.schema import UserResponse


class HospitalCreateSchema(BaseModel):
    name: str
    address: str
    contact_number: list[str]
    opened_date: str  # ISO 8601 date (YYYY-MM-DD)
    admin_name: str
    admin_email: str
    admin_password: str


class HospitalResponseSchema(BaseModel):
    hospital_id: str
    name: str
    address: str
    contact_number: list[str]
    opened_date: str  # ISO 8601 date (YYYY-MM-DD)
    admin: UserResponse

    class Config:
        orm_mode = True
