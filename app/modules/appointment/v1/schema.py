from datetime import date, time
from enum import StrEnum
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field, model_validator


class AppointmentStatusEnum(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


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


class DoctorBasicInfo(BaseModel):
    """Basic doctor information for appointment response"""

    doctor_id: str
    specialization_department: str
    experience_years: int
    user_name: str
    user_email: str

    class Config:
        from_attributes = True


class PatientBasicInfo(BaseModel):
    """Basic patient information for appointment response"""

    patient_id: str
    gender: str
    blood_group: str
    user_name: str
    user_email: str
    user_phone: str

    class Config:
        from_attributes = True


class AvailabilityBasicInfo(BaseModel):
    """Basic availability information for appointment response"""

    availability_id: str
    date: date
    start_time: time
    end_time: time

    class Config:
        from_attributes = True


class AppointmentResponseSchema(BaseModel):
    """Schema for appointment response"""

    appointment_id: str
    patient_id: str
    doctor_id: str
    availability_id: str
    appointment_date: date
    reason: Optional[str]
    notes: Optional[str]
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AppointmentDetailResponseSchema(BaseModel):
    """Detailed appointment response with related entities"""

    appointment_id: str
    patient: PatientBasicInfo
    doctor: DoctorBasicInfo
    availability: AvailabilityBasicInfo
    appointment_date: date
    reason: Optional[str]
    notes: Optional[str]
    status: str
    booked_by_user_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def validate_appointment(cls, data: Any) -> Any:
        """
        Validate and transform appointment data from ORM model.
        Automatically extracts nested relationships.
        """
        # If it's already a dict, return as-is
        if isinstance(data, dict):
            return data

        # If it's an ORM model, extract the data
        if hasattr(data, "__dict__"):
            # Extract patient info
            patient_info = PatientBasicInfo(
                patient_id=data.patient.patient_id,
                gender=data.patient.gender,
                blood_group=data.patient.blood_group,
                user_name=data.patient.user.name,
                user_email=data.patient.user.email,
                user_phone=data.patient.user.phone_number,
            )

            # Extract doctor info
            doctor_info = DoctorBasicInfo(
                doctor_id=data.doctor.doctor_id,
                specialization_department=data.doctor.specialization_department,
                experience_years=data.doctor.experience_years,
                user_name=data.doctor.user.name,
                user_email=data.doctor.user.email,
            )

            # Extract availability info
            availability_info = AvailabilityBasicInfo(
                availability_id=data.availability.availability_id,
                date=data.availability.date,
                start_time=data.availability.start_time,
                end_time=data.availability.end_time,
            )

            return {
                "appointment_id": data.appointment_id,
                "patient": patient_info,
                "doctor": doctor_info,
                "availability": availability_info,
                "appointment_date": data.appointment_date,
                "reason": data.reason,
                "notes": data.notes,
                "status": data.status,
                "booked_by_user_id": data.booked_by_user_id,
                "created_at": data.created_at.isoformat(),
                "updated_at": data.updated_at.isoformat(),
            }

        return data


class AppointmentListResponse(BaseModel):
    """Response for list of appointments"""

    message: str
    total: int
    data: list[AppointmentDetailResponseSchema]


class AppointmentSingleResponse(BaseModel):
    """Response for single appointment"""

    message: str
    data: AppointmentDetailResponseSchema


# Query Parameter Schemas for filtering


class SuperAdminAppointmentFilters(BaseModel):
    """Filter parameters for super admin - can filter by anything"""

    hospital_id: Optional[str] = Field(None, description="Filter by hospital ID")
    doctor_id: Optional[str] = Field(None, description="Filter by doctor ID")
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
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        100, ge=1, le=500, description="Maximum number of records to return"
    )


class HospitalAdminAppointmentFilters(BaseModel):
    """Filter parameters for hospital admin - can filter their hospital's appointments"""

    doctor_id: Optional[str] = Field(
        None, description="Filter by doctor ID in their hospital"
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
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        100, ge=1, le=500, description="Maximum number of records to return"
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
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        100, ge=1, le=500, description="Maximum number of records to return"
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
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        100, ge=1, le=500, description="Maximum number of records to return"
    )
