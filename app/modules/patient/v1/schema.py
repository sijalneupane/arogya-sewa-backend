from datetime import date
from pydantic import BaseModel

from app.modules.user.v1.schema import UserResponse


class PatientCreate(BaseModel):
    dob: date
    gender: str
    blood_group: str


class PatientResponse(BaseModel):
    patient_id: str
    dob: date
    gender: str
    blood_group: str
    user: UserResponse

    class Config:
        from_attributes = True
