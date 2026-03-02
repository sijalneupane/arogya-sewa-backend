from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums.role_enum import RoleEnum
from app.modules.department.v1.schema import DepartmentResponseSchema
from app.modules.file.v1.schemas import FileResponseSchema
from app.modules.hospital.v1.schema import HospitalResponseSchema
from app.modules.user.v1.schema import UserCreate, UserResponse


class DoctorCreateSchema(BaseModel):
    specialization_department: str
    experience_years: int
    license_certificate_id: str
    department_id: Optional[str] = None
    # hospital_id: Optional[str] = None
    user: UserCreate


class DoctorUpdateSchema(BaseModel):
    experience_years: Optional[int] = None
    license_certificate_id: Optional[str] = None
    department_id: Optional[str] = None
    # hospital_id: Optional[str] = None


class UserToDoctorUpgradeSchema(BaseModel):
    experience_years: int = Field(..., ge=0, le=50)
    license_certificate_id: str = Field(..., min_length=1, max_length=100)
    department_id: Optional[str] = None


class DoctorResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    experience_years: int
    license_certificate: Optional[FileResponseSchema] = None
    hospital_id: Optional[str] = None
    department: Optional[DepartmentResponseSchema] = None
    user: UserResponse


# class HospitalBasicInfo(BaseModel):
#     """Basic hospital info for doctor response (to avoid circular references)"""

#     model_config = ConfigDict(from_attributes=True)

#     hospital_id: str
#     name: str
#     location: str


class DoctorWithHospitalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    experience_years: int
    license_certificate: Optional[FileResponseSchema] = None
    department: Optional[DepartmentResponseSchema] = None
    user: UserResponse
    hospital: Optional[HospitalResponseSchema] = None


class DoctorListResponseSchema(BaseModel):
    message: str = "Doctors fetched successfully"
    data: list[DoctorResponseSchema]


class DoctorDetailResponseSchema(BaseModel):
    message: str = "Doctor fetched successfully"
    data: DoctorWithHospitalResponseSchema


class DoctorPostPatchResponse(BaseModel):
    message: str = "Doctor created successfully"
    data: DoctorResponseSchema
