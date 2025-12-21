from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums.role_enum import RoleEnum
from app.modules.file.v1.schemas import FileResponseSchema
from app.modules.user.v1.schema import UserCreate, UserResponse


class DoctorCreateSchema(BaseModel):
    specialization_department: str
    experience_years: int
    license_certificate_id: str
    hospital_id: Optional[str] = None
    user: UserCreate


class DoctorUpdateSchema(BaseModel):
    specialization_department: Optional[str] = None
    experience_years: Optional[int] = None
    license_certificate_id: Optional[str] = None
    hospital_id: Optional[str] = None


class UserToDoctorUpgradeSchema(BaseModel):
    specialization_department: str = Field(..., min_length=1, max_length=100)
    experience_years: int = Field(..., ge=0, le=50)
    license_certificate_id: str = Field(..., min_length=1, max_length=100)


class DoctorResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    specialization_department: str
    experience_years: int
    license_certificate: Optional[FileResponseSchema] = None
    hospital_id: Optional[str] = None
    user: UserResponse


class HospitalBasicInfo(BaseModel):
    """Basic hospital info for doctor response (to avoid circular references)"""

    model_config = ConfigDict(from_attributes=True)

    hospital_id: str
    name: str
    location: str


class DoctorWithHospitalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    specialization_department: str
    experience_years: int
    license_certificate: Optional[FileResponseSchema] = None
    user: UserResponse
    hospital: Optional[HospitalBasicInfo] = None


class DoctorListResponseSchema(BaseModel):
    message: str = "Doctors fetched successfully"
    data: list[DoctorResponseSchema]


class DoctorDetailResponseSchema(BaseModel):
    message: str = "Doctor fetched successfully"
    data: DoctorWithHospitalResponseSchema
