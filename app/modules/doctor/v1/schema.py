from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.enums.doctor_status_enum import DoctorStatusEnum
from app.modules.availability.v1.schema import AvailabilityResponseSchema
from app.modules.department.v1.schema import DepartmentResponseSchema
from app.modules.file.v1.schemas import FileResponseSchema
from app.modules.user.v1.schema import UserCreate, UserResponse


class DoctorUserCredentialsWithProfileImage(UserCreate):
    profile_image_id: Optional[str] = Field(
        None, description="ID of the profile image file for the doctor"
    )


class DoctorCreateSchema(BaseModel):
    """
    Schema for creating a new doctor record.

    Attributes:
        experience (str): Professional experience description of the doctor.
        experience (str): Professional experience description of the doctor.
            Defaults to "No experience."
        license_certificate_id (str): Required unique identifier for the doctor's
        license_certificate_id (str): Required unique identifier for the doctor's
            medical license certificate.
        department_id (Optional[str]): Optional identifier for the department
        department_id (Optional[str]): Optional identifier for the department
            the doctor belongs to. Defaults to None.
        bio (Optional[str]): Optional biography or description of the doctor
        bio (Optional[str]): Optional biography or description of the doctor
            with a maximum length of 1000 characters. Defaults to None.
        status (DoctorStatusEnum): Current status of the doctor account.
            Defaults to DoctorStatusEnum.ACTIVE.
        user (DoctorUserCredentialsWithProfileImage): Required nested schema containing
            the doctor's user credentials and profile image information.
    """

    experience: str = "No experience."
    license_certificate_id: str
    department_id: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=1000)
    status: DoctorStatusEnum = DoctorStatusEnum.ACTIVE
    # hospital_id: Optional[str] = None
    user: DoctorUserCredentialsWithProfileImage


class DoctorUserUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=5, max_length=30)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, min_length=10, max_length=10)
    password: Optional[str] = Field(None, min_length=6, max_length=30)
    profile_image_id: Optional[str] = None


class DoctorUpdateSchema(BaseModel):
    experience: Optional[str] = None
    license_certificate_id: Optional[str] = None
    department_id: Optional[str] = None
    status: Optional[DoctorStatusEnum] = None
    bio: Optional[str] = Field(None, max_length=1000)
    user: Optional[DoctorUserUpdateSchema] = None
    # hospital_id: Optional[str] = None


class UserToDoctorUpgradeSchema(BaseModel):
    experience: str = "No experience."
    license_certificate_id: str = Field(..., min_length=1, max_length=100)
    department_id: Optional[str] = None


class HospitalBasicInfo(BaseModel):
    """Basic hospital info for doctor response."""

    model_config = ConfigDict(from_attributes=True)

    hospital_id: str
    name: str
    location: str


class DoctorResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    experience: str
    status: DoctorStatusEnum
    bio: Optional[str] = None
    booking_fee: float
    license_certificate: Optional[FileResponseSchema] = None
    hospital_id: Optional[str] = None
    hospital: Optional[HospitalBasicInfo] = None
    department: Optional[DepartmentResponseSchema] = None
    user: UserResponse
    upcoming_availability: Optional[AvailabilityResponseSchema] = None


class DoctorWithHospitalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: str
    experience: str
    status: DoctorStatusEnum
    bio: Optional[str] = None
    license_certificate: Optional[FileResponseSchema] = None
    department: Optional[DepartmentResponseSchema] = None
    user: UserResponse
    hospital: Optional[HospitalBasicInfo] = None


class DoctorFilterSchema(BaseModel):
    name: Optional[str] = Field(
        None, description="Search by doctor name (partial match)"
    )
    status: Optional[DoctorStatusEnum] = Field(
        None, description="Filter by doctor status"
    )
    department: Optional[str] = Field(
        None, description="Filter by department ID (exact) or name (partial match)"
    )
    free_upcoming_only: bool = Field(
        False,
        description="If true, attach only unbooked upcoming availability; otherwise attach any upcoming availability.",
    )


class DoctorDetailResponseSchema(BaseModel):
    message: str = "Doctor fetched successfully"
    data: DoctorWithHospitalResponseSchema


class DoctorPostPatchResponse(BaseModel):
    message: str = "Doctor created successfully"
    data: DoctorResponseSchema
