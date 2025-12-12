from datetime import date
from pydantic import BaseModel


class PatientCreate(BaseModel):
    dob: date
    gender: str
    blood_group: str


class PatientResponse(BaseModel):
    patient_id: str
    dob: date
    gender: str
    blood_group: str
    user_id: str

    class Config:
        from_attributes = True
