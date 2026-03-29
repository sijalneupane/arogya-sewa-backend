from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.common.enums.file_type_enum import FileTypeEnum
from app.common.schema.pagination import PaginationMeta, PaginationQuery
from app.modules.file.v1.schemas import FileResponseSchema
from app.modules.user.v1.schema import UserCreate, UserResponse


class HospitalCreateSchema(BaseModel):
    name: str
    location: str
    latitude: float
    longitude: float
    contact_number: list[str]
    opened_date: date = Field(
        ..., description="ISO 8601 date (YYYY-MM-DD)", examples=["2023-10-15"]
    )
    hospital_license_id: str  # License file to be assigned to hospital
    logo_img_id: str  # Logo file to be assigned to hospital
    banner_img_id: str  # Banner file to be assigned to hospital
    admin_details: UserCreate


class HospitalUpdateSchema(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_number: Optional[list[str]] = None
    opened_date: Optional[date] = Field(
        None, description="ISO 8601 date (YYYY-MM-DD)", examples=["2023-10-15"]
    )
    hospital_license_id: Optional[str] = None
    logo_img_id: Optional[str] = None
    banner_img_id: Optional[str] = None


class HospitalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str
    name: str
    location: str
    latitude: float
    longitude: float
    contact_number: list[str]
    opened_date: date  # ISO 8601 date (YYYY-MM-DD)
    created_at: datetime
    updated_at: datetime
    admin_id: str
    # admin: Optional[UserResponse] = None
    files: Optional[list[FileResponseSchema]] = Field(default=None, exclude=True)

    @computed_field
    @property
    def logo(self) -> Optional[FileResponseSchema]:
        """Extract logo from files list based on file_type."""
        if not self.files:
            return None
        for file in self.files:
            if file.file_type == FileTypeEnum.HOSPITAL_LOGO:
                return file
        return None

    @computed_field
    @property
    def license(self) -> Optional[FileResponseSchema]:
        """Extract license from files list based on file_type."""
        if not self.files:
            return None
        for file in self.files:
            if file.file_type == FileTypeEnum.LICENSE:
                return file
        return None

    @computed_field
    @property
    def banner(self) -> Optional[FileResponseSchema]:
        """Extract banner from files list based on file_type."""
        if not self.files:
            return None
        for file in self.files:
            if file.file_type == FileTypeEnum.HOSPITAL_BANNER:
                return file
        return None


class HospitalByIdResponseSchema(HospitalResponseSchema):
    admin: Optional[UserResponse] = None


class NearestHospitalResponseSchema(HospitalResponseSchema):
    distance_km: float


class HospitalListResponseSchema(BaseModel):
    message: str = "Hospitals fetched successfully"
    data: list[HospitalResponseSchema]
    # paginationMeta: PaginationMeta


class HospitalDetailResponseSchema(BaseModel):
    message: str = "Hospital fetched successfully"
    data: HospitalByIdResponseSchema


class AdminHospitalResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hospital_id: str
    name: str
    location: str
    latitude: float
    longitude: float
    contact_number: list[str]
    opened_date: date  # ISO 8601 date (YYYY-MM-DD)
    created_at: datetime
    updated_at: datetime
    files: Optional[list[FileResponseSchema]] = Field(default=None, exclude=True)

    @computed_field
    @property
    def logo(self) -> Optional[FileResponseSchema]:
        """Extract logo from files list based on file_type."""
        if not self.files:
            return None
        for file in self.files:
            if file.file_type == FileTypeEnum.HOSPITAL_LOGO:
                return file
        return None

    @computed_field
    @property
    def license(self) -> Optional[FileResponseSchema]:
        """Extract license from files list based on file_type."""
        if not self.files:
            return None
        for file in self.files:
            if file.file_type == FileTypeEnum.LICENSE:
                return file
        return None

    @computed_field
    @property
    def banner(self) -> Optional[FileResponseSchema]:
        """Extract banner from files list based on file_type."""
        if not self.files:
            return None
        for file in self.files:
            if file.file_type == FileTypeEnum.HOSPITAL_BANNER:
                return file
        return None


class AdminHospitalDetailResponseSchema(BaseModel):
    message: str = "Hospital fetched successfully"
    data: AdminHospitalResponseSchema


class FilterHospitaList(PaginationQuery):
    """Filter parameters for listing hospitals"""

    name: Optional[str] = Field(None, description="Search by hospital name")
    address: Optional[str] = Field(None, description="Search by hospital address")
    opened_date_from: Optional[date] = Field(
        None, description="Filter hospitals opened from this date"
    )
    opened_date_to: Optional[date] = Field(
        None, description="Filter hospitals opened up to this date"
    )
