from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.modules.user.v1.schema import UserResponse


class HospitalCreateSchema(BaseModel):
    name: str
    address: str
    contact_number: list[str]
    opened_date: date = Field(
        ..., description="ISO 8601 date (YYYY-MM-DD)", examples=["2023-10-15"]
    )
    admin_name: str
    admin_email: str
    admin_password: str


class HospitalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str
    name: str
    address: str
    contact_number: list[str]
    opened_date: date  # ISO 8601 date (YYYY-MM-DD)
    admin: UserResponse
