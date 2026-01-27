from datetime import date, datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field

from app.common.enums.appointment_status_enum import AppointmentStatusEnum
from app.common.schema.pagination import PaginationMeta
from app.modules.appointment.v1.changed_time_schema import AppointmentChangedTimeSingleInfoSchema
from app.modules.availability.v1.schema import AvailabilityResponseSchema
from app.modules.doctor.v1.schema import DoctorResponseSchema
from app.modules.patient.v1.schema import PatientResponse
from app.modules.user.v1.schema import UserResponse


# class ChangedTimeInfo(BaseModel):
#     """Changed time information for appointment response"""

#     changed_time_id: str
#     start_date_time: datetime
#     end_date_time: datetime
#     reason: Optional[str]
#     changed_at: str

#     class Config:
#         from_attributes = True


class AppointmentCreateSchema(BaseModel):
    """Schema for creating an appointment (booking)"""

    availability_id: Annotated[str, Field(min_length=8, max_length=8)] = Field(
        ..., description="ID of the availability slot to book"
    )
    reason: Optional[str] = Field(
        None, max_length=500, description="Reason for appointment"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")


class AppointmentUpdateSchema(BaseModel):
    """Schema for updating an appointment"""

    reason: Optional[str] = Field(
        None, max_length=500, description="Reason for appointment"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")
    status: Optional[AppointmentStatusEnum] = Field(
        None, description="Appointment status"
    )


# class DoctorBasicInfo(BaseModel):
#     """Basic doctor information for appointment response"""

#     doctor_id: str
#     user: UserResponse

#     class Config:
#         from_attributes = True


# class PatientBasicInfo(BaseModel):
#     """Basic patient information for appointment response"""

#     patient_id: str
#     user: UserResponse

#     class Config:
#         from_attributes = True


# class AvailabilityBasicInfo(BaseModel):
#     """Basic availability information for appointment response"""

#     availability_id: str
#     start_date_time: datetime
#     end_date_time: datetime

#     class Config:
#         from_attributes = True


class AppointmentResponseSchema(BaseModel):
    """Schema for appointment response"""

    appointment_id: str
    patient_id: str
    doctor_id: str
    availability_id: str
    booked_by_user_id: str
    availability: AvailabilityResponseSchema
    reason: Optional[str]
    notes: Optional[str]
    status: AppointmentStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentDetailResponseSchema(BaseModel):
    """Detailed appointment response with related entities"""

    appointment_id: str
    patient: PatientResponse
    doctor: DoctorResponseSchema
    booked_by: UserResponse
    availability: AvailabilityResponseSchema
    reason: Optional[str]
    notes: Optional[str]
    status: AppointmentStatusEnum
    # booked_by_user_id: str
    changed_times: list[AppointmentChangedTimeSingleInfoSchema]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Future use cases for role-based detailed responses by removing the patient or doctor info as needed


# class ApppointmentDetailResponseSchemaForDoctorList(BaseModel):
#     """Detailed appointment response for doctor listing"""

#     appointment_id: str
#     patient: PatientResponse
#     booked_by: UserResponse
#     availability: AvailabilityResponseSchema
#     reason: Optional[str]
#     notes: Optional[str]
#     status: AppointmentStatusEnum
#     changed_times: list[ChangedTimeInfo]
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         from_attributes = True


# class AppointmentDetailResponseSchemaForPatientList(BaseModel):
#     """Detailed appointment response for patient listing"""

#     appointment_id: str
#     doctor: DoctorResponseSchema
#     booked_by: UserResponse
#     availability: AvailabilityResponseSchema
#     reason: Optional[str]
#     notes: Optional[str]
#     status: AppointmentStatusEnum
#     changed_times: list[ChangedTimeInfo]
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         from_attributes = True


# class AppointmentListResponseForDoctor(BaseModel):
#     """Response for list of appointments for doctor with pagination metadata"""

#     message: str
#     data: list[ApppointmentDetailResponseSchemaForDoctorList]
#     paginationMeta: PaginationMeta


# class AppointmentListResponseForPatient(BaseModel):
#     """Response for list of appointments for patient with pagination metadata"""

#     message: str
#     data: list[AppointmentDetailResponseSchemaForPatientList]
#     paginationMeta: PaginationMeta


class AppointmentListResponse(BaseModel):
    """Response for list of appointments with pagination metadata"""

    message: str
    data: list[AppointmentDetailResponseSchema]
    paginationMeta: PaginationMeta


class AppointmentSingleResponse(BaseModel):
    """Response for single appointment"""

    message: str
    data: AppointmentDetailResponseSchema


# Query Parameter Schemas for filtering


class SuperAdminAppointmentFilters(BaseModel):
    """Filter parameters for super admin - can filter by anything"""

    hospital_name: Optional[str] = Field(None, description="Search by hospital name")
    doctor_name: Optional[str] = Field(None, description="Search by doctor name")
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    patient_name: Optional[str] = Field(None, description="Search by patient name")
    status: Optional[AppointmentStatusEnum] = Field(
        None, description="Filter by appointment status"
    )
    date_from: Optional[date] = Field(
        None, description="Filter appointments from this date"
    )
    date_to: Optional[date] = Field(
        None, description="Filter appointments up to this date"
    )
    appointment_date: Optional[date] = Field(
        None, description="Filter by specific appointment date"
    )


class HospitalAdminAppointmentFilters(BaseModel):
    """Filter parameters for hospital admin - can filter their hospital's appointments"""

    doctor_name: Optional[str] = Field(
        None, description="Search by doctor name in their hospital"
    )
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    patient_name: Optional[str] = Field(None, description="Search by patient name")
    status: Optional[AppointmentStatusEnum] = Field(
        None, description="Filter by appointment status"
    )
    date_from: Optional[date] = Field(
        None, description="Filter appointments from this date"
    )
    date_to: Optional[date] = Field(
        None, description="Filter appointments up to this date"
    )
    appointment_date: Optional[date] = Field(
        None, description="Filter by specific appointment date"
    )


class DoctorAppointmentFilters(BaseModel):
    """Filter parameters for doctor - can only filter their own appointments"""

    status: Optional[AppointmentStatusEnum] = Field(
        None, description="Filter by appointment status"
    )
    date_from: Optional[date] = Field(
        None, description="Filter appointments from this date"
    )
    date_to: Optional[date] = Field(
        None, description="Filter appointments up to this date"
    )
    appointment_date: Optional[date] = Field(
        None, description="Filter by specific appointment date"
    )


class PatientAppointmentFilters(BaseModel):
    """Filter parameters for patient - can only filter their own appointments"""

    status: Optional[AppointmentStatusEnum] = Field(
        None, description="Filter by appointment status"
    )
    date_from: Optional[date] = Field(
        None, description="Filter appointments from this date"
    )
    date_to: Optional[date] = Field(
        None, description="Filter appointments up to this date"
    )
    appointment_date: Optional[date] = Field(
        None, description="Filter by specific appointment date"
    )
