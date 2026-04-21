from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, field_serializer

from app.common.enums.activity_log_action_type_enum import ActivityLogActionTypeEnum
from app.common.enums.appointment_status_enum import AppointmentStatusEnum
from app.common.enums.payment_status_enum import PaymentStatusEnum
from app.common.schema.pagination import PaginationQuery


class ActivityLogResponse(BaseModel):
    activity_log_id: str
    user_id: str
    hospital_id: Optional[str] = None
    action_type: ActivityLogActionTypeEnum
    entity_type: str
    entity_id: str
    description: str
    created_at: datetime
    metadata: Optional[dict] = None

    # Computed fields for user and hospital info
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class ActivityLogCreate(BaseModel):
    user_id: str
    hospital_id: Optional[str] = None
    action_type: ActivityLogActionTypeEnum
    entity_type: str = Field(
        ..., description="Entity type like 'Appointment', 'User', etc."
    )
    entity_id: str = Field(..., description="Raw entity ID, not a relationship")
    description: str
    metadata: Optional[dict] = None


class DashboardActivityFilters(PaginationQuery):
    user_id: Optional[str] = None
    hospital_id: Optional[str] = None
    action_type: Optional[ActivityLogActionTypeEnum] = None
    entity_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TrendDirection(StrEnum):
    INCREASED = "INCREASED"
    DECREASED = "DECREASED"
    NO_CHANGE = "NO_CHANGE"


class AppointmentMonthlyStats(BaseModel):
    last_month: int
    this_month: int
    percentage_rise: float
    trend_type: TrendDirection


class DoctorMonthlyStats(BaseModel):
    last_month: int
    this_month: int
    percentage_rise: float
    trend_type: TrendDirection


class HospitalMonthlyStats(BaseModel):
    last_month: int
    this_month: int
    percentage_rise: float
    trend_type: TrendDirection


class SuperAdminDashboardSummary(BaseModel):
    total_users: int
    total_doctors: int
    total_hospitals: int
    total_patients: int
    total_appointments: int
    appointments_monthly: AppointmentMonthlyStats
    doctors_monthly: DoctorMonthlyStats
    hospitals_monthly: HospitalMonthlyStats
    total_paid_amount: float
    available_doctors_today: int


class HospitalAdminDashboardSummary(BaseModel):
    total_doctors: int
    total_appointments: int
    total_revenue: float
    total_departments: int
    appointments_monthly: AppointmentMonthlyStats
    doctors_monthly: DoctorMonthlyStats


class DoctorAppointmentStatusCount(BaseModel):
    status: AppointmentStatusEnum
    count: int


class DoctorAppointmentOverview(BaseModel):
    total_appointments: int
    total_upcoming_appointments: int
    today_appointments: int
    status_counts: list[DoctorAppointmentStatusCount]


class DoctorPaymentOverview(BaseModel):
    total_payment_received: float
    total_advance_received: float
    total_pending_amount: float

    @field_serializer("total_payment_received")
    def serialize_total_payment_received(self, value: float) -> float:
        return round(value, 2)

    @field_serializer("total_advance_received")
    def serialize_total_advance_received(self, value: float) -> float:
        return round(value, 2)

    @field_serializer("total_pending_amount")
    def serialize_total_pending_amount(self, value: float) -> float:
        return round(value, 2)


class DoctorAvailabilityOverview(BaseModel):
    total_future_availabilities: int
    total_open_future_availabilities: int


class DoctorDashboardSummary(BaseModel):
    appointment_overview: DoctorAppointmentOverview
    payment_overview: DoctorPaymentOverview
    availability_overview: DoctorAvailabilityOverview


class DoctorDashboardSummaryResponse(BaseModel):
    message: str = "Doctor dashboard summary fetched successfully"
    data: DoctorDashboardSummary


class DoctorAppointmentFeedItem(BaseModel):
    appointment_id: str
    patient_id: str
    patient_name: str
    status: AppointmentStatusEnum
    payment_status: PaymentStatusEnum
    start_date_time: datetime
    end_date_time: datetime
    total_amount: float
    paid_amount: float
    due_amount: float
    reason: Optional[str] = None
    notes: Optional[str] = None


class DoctorAppointmentFeedResponse(BaseModel):
    message: str
    totalRecords: int
    data: list[DoctorAppointmentFeedItem]
