from datetime import datetime, time, timedelta, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, case, desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.appointment_status_enum import AppointmentStatusEnum
from app.common.enums.doctor_status_enum import DoctorStatusEnum
from app.common.enums.payment_transaction_status_enum import (
    PaymentTransactionStatusEnum,
)
from app.common.enums.payment_type_enum import PaymentTypeEnum
from app.core import logging_config
from app.core.utils.string_utils import StringUtils
from app.modules.appointment.v1.models import Appointment
from app.modules.availability.v1.models import Availability
from app.modules.dashboard.v1.models import ActivityLog
from app.modules.dashboard.v1.schema import (
    ActivityLogCreate,
    ActivityLogResponse,
    AppointmentMonthlyStats,
    DashboardActivityFilters,
    DoctorAppointmentFeedItem,
    DoctorAppointmentFeedResponse,
    DoctorAppointmentOverview,
    DoctorAppointmentStatusCount,
    DoctorAvailabilityOverview,
    DoctorDashboardSummary,
    DoctorDashboardSummaryResponse,
    DoctorMonthlyStats,
    DoctorPaymentOverview,
    HospitalAdminDashboardSummary,
    HospitalMonthlyStats,
    SuperAdminDashboardSummary,
    TrendDirection,
)
from app.modules.department.v1.models import Department
from app.modules.doctor.v1.models import Doctor
from app.modules.hospital.v1.models import Hospital
from app.modules.patient.v1.models import Patient
from app.modules.payment.v1.models import Payment
from app.modules.user.v1.models import User


async def create_activity_log(
    db: AsyncSession,
    activity_data: ActivityLogCreate,
) -> ActivityLog:
    """Create a new activity log entry."""
    # Generate activity log ID with "AL" prefix
    activity_log_id = f"AL_{StringUtils.randomAlphaNumeric(7)}"

    activity_log = ActivityLog(
        activity_log_id=activity_log_id,
        user_id=activity_data.user_id,
        hospital_id=activity_data.hospital_id,
        action_type=activity_data.action_type,
        entity_type=activity_data.entity_type,
        entity_id=activity_data.entity_id,
        description=activity_data.description,
        metadata_json=activity_data.metadata,
    )

    db.add(activity_log)
    await db.flush()  # Flush to get the ID without committing
    await db.refresh(activity_log)  # Refresh to get all fields
    return activity_log


async def get_recent_activities(
    db: AsyncSession,
    filters: DashboardActivityFilters,
    current_user_id: Optional[str] = None,
    current_user_hospital_id: Optional[str] = None,
) -> Tuple[List[ActivityLog], int]:
    """
    Get recent activities based on filters and user permissions.

    - For super admin: can see all activities
    - For hospital admin: can see activities for their hospital
    - For other users: can see their own activities
    """
    query = select(ActivityLog).options(selectinload(ActivityLog.user))

    # Apply filters
    conditions = []

    if filters.user_id:
        conditions.append(ActivityLog.user_id == filters.user_id)

    if filters.hospital_id:
        conditions.append(ActivityLog.hospital_id == filters.hospital_id)

    if filters.action_type:
        conditions.append(ActivityLog.action_type == filters.action_type)

    if filters.entity_type:
        conditions.append(ActivityLog.entity_type == filters.entity_type)

    if filters.start_date:
        conditions.append(ActivityLog.created_at >= filters.start_date)

    if filters.end_date:
        conditions.append(ActivityLog.created_at <= filters.end_date)

    # Apply permission-based filtering
    if current_user_hospital_id:
        # Hospital admin can only see activities for their hospital
        conditions.append(ActivityLog.hospital_id == current_user_hospital_id)
    elif current_user_id and not current_user_hospital_id:
        # Regular users can only see their own activities
        conditions.append(ActivityLog.user_id == current_user_id)
    # Super admin can see all activities (no additional conditions)

    if conditions:
        query = query.where(and_(*conditions))

    # Order by creation date (most recent first)
    query = query.order_by(desc(ActivityLog.created_at))

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    query = query.offset(offset).limit(filters.size)

    result = await db.execute(query)
    activities = list(result.scalars().all())

    # Get total count for pagination
    count_query = select(func.count()).select_from(ActivityLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return activities, total


async def get_system_recent_activities(
    db: AsyncSession,
    limit: int = 50,
) -> List[ActivityLog]:
    """
    Get recent activities across the entire system.
    Used for system-wide dashboard.
    """
    query = (
        select(ActivityLog)
        .options(selectinload(ActivityLog.user))
        .order_by(desc(ActivityLog.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_hospital_recent_activities(
    db: AsyncSession,
    hospital_id: str,
    limit: int = 50,
) -> List[ActivityLog]:
    """
    Get recent activities for a specific hospital.
    Used for hospital admin dashboard.
    """
    query = (
        select(ActivityLog)
        .options(selectinload(ActivityLog.user))
        .where(ActivityLog.hospital_id == hospital_id)
        .order_by(desc(ActivityLog.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


def build_activity_response(activity: ActivityLog) -> ActivityLogResponse:
    """Build ActivityLogResponse with user and hospital info."""
    response = ActivityLogResponse(
        activity_log_id=activity.activity_log_id,
        user_id=activity.user_id,
        hospital_id=activity.hospital_id,
        action_type=activity.action_type,
        entity_type=activity.entity_type,
        entity_id=activity.entity_id,
        description=activity.description,
        created_at=activity.created_at,
        metadata=activity.metadata_json,
    )

    # Add user info
    if activity.user:
        response.user_name = activity.user.name
        response.user_email = activity.user.email

    return response


def _calculate_percentage_rise(last_month: int, this_month: int) -> float:
    if last_month == 0:
        return float(this_month * 100) if this_month > 0 else 0.0
    return ((this_month - last_month) / last_month) * 100


def _get_trend_type(last_month: int, this_month: int) -> TrendDirection:
    if this_month > last_month:
        return TrendDirection.INCREASED
    if this_month < last_month:
        return TrendDirection.DECREASED
    return TrendDirection.NO_CHANGE


async def get_super_admin_dashboard_summary(
    db: AsyncSession,
) -> SuperAdminDashboardSummary:
    now = datetime.now(timezone.utc)

    start_this_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        start_next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        start_next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

    if now.month == 1:
        start_last_month = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
    else:
        start_last_month = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)

    today_date = now.date()

    total_users = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar_one()
    total_doctors = (
        await db.execute(select(func.count()).select_from(Doctor))
    ).scalar_one()
    total_hospitals = (
        await db.execute(select(func.count()).select_from(Hospital))
    ).scalar_one()
    total_patients = (
        await db.execute(select(func.count()).select_from(Patient))
    ).scalar_one()
    total_appointments = (
        await db.execute(select(func.count()).select_from(Appointment))
    ).scalar_one()

    last_month_appointments = (
        await db.execute(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.created_at >= start_last_month,
                Appointment.created_at < start_this_month,
            )
        )
    ).scalar_one()

    this_month_appointments = (
        await db.execute(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.created_at >= start_this_month,
                Appointment.created_at < start_next_month,
            )
        )
    ).scalar_one()

    last_month_doctors = (
        await db.execute(
            select(func.count())
            .select_from(Doctor)
            .where(
                Doctor.created_at >= start_last_month,
                Doctor.created_at < start_this_month,
            )
        )
    ).scalar_one()

    this_month_doctors = (
        await db.execute(
            select(func.count())
            .select_from(Doctor)
            .where(
                Doctor.created_at >= start_this_month,
                Doctor.created_at < start_next_month,
            )
        )
    ).scalar_one()

    last_month_hospitals = (
        await db.execute(
            select(func.count())
            .select_from(Hospital)
            .where(
                Hospital.created_at >= start_last_month,
                Hospital.created_at < start_this_month,
            )
        )
    ).scalar_one()

    this_month_hospitals = (
        await db.execute(
            select(func.count())
            .select_from(Hospital)
            .where(
                Hospital.created_at >= start_this_month,
                Hospital.created_at < start_next_month,
            )
        )
    ).scalar_one()

    total_paid_amount_raw = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
                Payment.status == PaymentTransactionStatusEnum.SUCCESS
            )
        )
    ).scalar_one()

    available_doctors_today = (
        await db.execute(
            select(func.count(distinct(Availability.doctor_id)))
            .select_from(Availability)
            .join(Doctor, Doctor.doctor_id == Availability.doctor_id)
            .where(
                func.date(Availability.start_date_time) == today_date,
                Availability.is_booked.is_(False),
                Doctor.status == DoctorStatusEnum.ACTIVE,
            )
        )
    ).scalar_one()

    return SuperAdminDashboardSummary(
        total_users=total_users,
        total_doctors=total_doctors,
        total_hospitals=total_hospitals,
        total_patients=total_patients,
        total_appointments=total_appointments,
        appointments_monthly=AppointmentMonthlyStats(
            last_month=last_month_appointments,
            this_month=this_month_appointments,
            percentage_rise=_calculate_percentage_rise(
                last_month_appointments, this_month_appointments
            ),
            trend_type=_get_trend_type(
                last_month_appointments, this_month_appointments
            ),
        ),
        doctors_monthly=DoctorMonthlyStats(
            last_month=last_month_doctors,
            this_month=this_month_doctors,
            percentage_rise=_calculate_percentage_rise(
                last_month_doctors, this_month_doctors
            ),
            trend_type=_get_trend_type(last_month_doctors, this_month_doctors),
        ),
        hospitals_monthly=HospitalMonthlyStats(
            last_month=last_month_hospitals,
            this_month=this_month_hospitals,
            percentage_rise=_calculate_percentage_rise(
                last_month_hospitals, this_month_hospitals
            ),
            trend_type=_get_trend_type(last_month_hospitals, this_month_hospitals),
        ),
        total_paid_amount=float(total_paid_amount_raw or 0.0),
        available_doctors_today=available_doctors_today,
    )


async def _get_doctor_by_user_id(db: AsyncSession, doctor_user_id: str) -> Doctor:
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.user_id == doctor_user_id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=403,
            detail="User is not associated with a doctor profile",
        )

    return doctor


def _doctor_feed_query(
    doctor_id: str,
    start_date_time: datetime,
    end_date_time: datetime,
):
    return (
        select(Appointment)
        .options(
            selectinload(Appointment.patient).selectinload(Patient.user),
            selectinload(Appointment.availability),
        )
        .join(Availability, Appointment.availability_id == Availability.availability_id)
        .join(Patient, Appointment.patient_id == Patient.patient_id)
        .join(User, Patient.user_id == User.id)
        .where(
            Appointment.doctor_id == doctor_id,
            Availability.start_date_time >= start_date_time,
            Availability.start_date_time < end_date_time,
            Appointment.status != AppointmentStatusEnum.CANCELLED,
        )
        .order_by(Availability.start_date_time.asc(), Appointment.created_at.asc())
    )


async def get_doctor_dashboard_summary(
    db: AsyncSession,
    doctor_user_id: str,
) -> DoctorDashboardSummaryResponse:
    doctor = await _get_doctor_by_user_id(db, doctor_user_id)

    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    tomorrow_start = today_start + timedelta(days=1)

    appointment_overview_result = await db.execute(
        select(
            func.count(Appointment.appointment_id),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Availability.start_date_time >= now,
                                Appointment.status != AppointmentStatusEnum.CANCELLED,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Availability.start_date_time >= today_start,
                                Availability.start_date_time < tomorrow_start,
                                Appointment.status != AppointmentStatusEnum.CANCELLED,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .select_from(Appointment)
        .join(Availability, Appointment.availability_id == Availability.availability_id)
        .where(Appointment.doctor_id == doctor.doctor_id)
    )
    total_appointments, total_upcoming_appointments, today_appointments = (
        appointment_overview_result.one()
    )

    status_results = await db.execute(
        select(Appointment.status, func.count(Appointment.appointment_id))
        .select_from(Appointment)
        .where(Appointment.doctor_id == doctor.doctor_id)
        .group_by(Appointment.status)
    )
    status_counts = {status: int(count) for status, count in status_results.all()}

    payment_overview_result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            Payment.status == PaymentTransactionStatusEnum.SUCCESS,
                            Payment.amount,
                        ),
                        else_=0.0,
                    )
                ),
                0.0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Payment.status == PaymentTransactionStatusEnum.SUCCESS,
                                Payment.payment_type
                                == PaymentTypeEnum.APPOINTMENT_ADVANCE,
                            ),
                            Payment.amount,
                        ),
                        else_=0.0,
                    )
                ),
                0.0,
            ),
        )
        .select_from(Appointment)
        .outerjoin(Payment, Payment.appointment_id == Appointment.appointment_id)
        .where(Appointment.doctor_id == doctor.doctor_id)
    )
    total_payment_received, total_advance_received = payment_overview_result.one()

    pending_amount_result = await db.execute(
        select(func.coalesce(func.sum(Appointment.due_amount), 0.0)).where(
            Appointment.doctor_id == doctor.doctor_id
        )
    )
    total_pending_amount = pending_amount_result.scalar_one()

    future_availability_result = await db.execute(
        select(
            func.count(Availability.availability_id),
            func.coalesce(
                func.sum(
                    case(
                        (Availability.is_booked.is_(False), 1),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .select_from(Availability)
        .where(
            Availability.doctor_id == doctor.doctor_id,
            Availability.start_date_time >= now,
        )
    )
    total_future_availabilities, total_open_future_availabilities = (
        future_availability_result.one()
    )

    return DoctorDashboardSummaryResponse(
        data=DoctorDashboardSummary(
            appointment_overview=DoctorAppointmentOverview(
                total_appointments=int(total_appointments or 0),
                total_upcoming_appointments=int(total_upcoming_appointments or 0),
                today_appointments=int(today_appointments or 0),
                status_counts=[
                    DoctorAppointmentStatusCount(
                        status=status,
                        count=status_counts.get(status, 0),
                    )
                    for status in AppointmentStatusEnum
                ],
            ),
            payment_overview=DoctorPaymentOverview(
                total_payment_received=float(total_payment_received or 0.0),
                total_advance_received=float(total_advance_received or 0.0),
                total_pending_amount=float(total_pending_amount or 0.0),
            ),
            availability_overview=DoctorAvailabilityOverview(
                total_future_availabilities=int(total_future_availabilities or 0),
                total_open_future_availabilities=int(
                    total_open_future_availabilities or 0
                ),
            ),
        )
    )


async def get_doctor_upcoming_appointments_feed(
    db: AsyncSession,
    doctor_user_id: str,
    limit: int = 10,
) -> DoctorAppointmentFeedResponse:
    doctor = await _get_doctor_by_user_id(db, doctor_user_id)
    now = datetime.now(timezone.utc)
    logging_config.logger.info(
        f"Fetching upcoming appointments for doctor_id={doctor.doctor_id} starting from {now.isoformat()} with limit={limit}"
    )
    count_result = await db.execute(
        select(func.count(Appointment.appointment_id))
        .select_from(Appointment)
        .join(Availability, Appointment.availability_id == Availability.availability_id)
        .where(
            Appointment.doctor_id == doctor.doctor_id,
            Availability.start_date_time >= now,
            Appointment.status != AppointmentStatusEnum.CANCELLED,
        )
    )
    total_records = count_result.scalar_one()

    query = _doctor_feed_query(
        doctor.doctor_id, now, datetime.max.replace(tzinfo=timezone.utc)
    )
    result = await db.execute(query.limit(limit))
    appointments = list(result.scalars().all())

    return DoctorAppointmentFeedResponse(
        message="Doctor upcoming appointments fetched successfully",
        totalRecords=total_records,
        data=[
            DoctorAppointmentFeedItem(
                appointment_id=appointment.appointment_id,
                patient_id=appointment.patient_id,
                patient_name=appointment.patient.user.name
                if appointment.patient and appointment.patient.user
                else "Patient",
                status=appointment.status,
                payment_status=appointment.payment_status,
                start_date_time=appointment.availability.start_date_time,
                end_date_time=appointment.availability.end_date_time,
                total_amount=appointment.total_amount,
                paid_amount=appointment.paid_amount,
                due_amount=appointment.due_amount,
                reason=appointment.reason,
                notes=appointment.notes,
            )
            for appointment in appointments
        ],
    )


async def get_doctor_today_appointments_feed(
    db: AsyncSession,
    doctor_user_id: str,
    limit: int = 10,
) -> DoctorAppointmentFeedResponse:
    doctor = await _get_doctor_by_user_id(db, doctor_user_id)
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    tomorrow_start = today_start + timedelta(days=1)

    count_result = await db.execute(
        select(func.count(Appointment.appointment_id))
        .select_from(Appointment)
        .join(Availability, Appointment.availability_id == Availability.availability_id)
        .where(
            Appointment.doctor_id == doctor.doctor_id,
            Availability.start_date_time >= today_start,
            Availability.start_date_time < tomorrow_start,
            Appointment.status != AppointmentStatusEnum.CANCELLED,
        )
    )
    total_records = count_result.scalar_one()

    query = _doctor_feed_query(doctor.doctor_id, today_start, tomorrow_start)
    result = await db.execute(query.limit(limit))
    appointments = list(result.scalars().all())

    return DoctorAppointmentFeedResponse(
        message="Doctor today appointments fetched successfully",
        totalRecords=total_records,
        data=[
            DoctorAppointmentFeedItem(
                appointment_id=appointment.appointment_id,
                patient_id=appointment.patient_id,
                patient_name=appointment.patient.user.name
                if appointment.patient and appointment.patient.user
                else "Patient",
                status=appointment.status,
                payment_status=appointment.payment_status,
                start_date_time=appointment.availability.start_date_time,
                end_date_time=appointment.availability.end_date_time,
                total_amount=appointment.total_amount,
                paid_amount=appointment.paid_amount,
                due_amount=appointment.due_amount,
                reason=appointment.reason,
                notes=appointment.notes,
            )
            for appointment in appointments
        ],
    )


async def get_hospital_admin_dashboard_summary(
    db: AsyncSession,
    hospital_id: str,
) -> HospitalAdminDashboardSummary:
    now = datetime.now(timezone.utc)

    start_this_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        start_next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        start_next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

    if now.month == 1:
        start_last_month = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
    else:
        start_last_month = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)

    total_doctors = (
        await db.execute(
            select(func.count())
            .select_from(Doctor)
            .where(Doctor.hospital_id == hospital_id)
        )
    ).scalar_one()

    total_departments = (
        await db.execute(
            select(func.count())
            .select_from(Department)
            .where(Department.hospital_id == hospital_id)
        )
    ).scalar_one()

    total_appointments = (
        await db.execute(
            select(func.count())
            .select_from(Appointment)
            .join(Doctor, Doctor.doctor_id == Appointment.doctor_id)
            .where(Doctor.hospital_id == hospital_id)
        )
    ).scalar_one()

    last_month_appointments = (
        await db.execute(
            select(func.count())
            .select_from(Appointment)
            .join(Doctor, Doctor.doctor_id == Appointment.doctor_id)
            .where(
                Doctor.hospital_id == hospital_id,
                Appointment.created_at >= start_last_month,
                Appointment.created_at < start_this_month,
            )
        )
    ).scalar_one()

    this_month_appointments = (
        await db.execute(
            select(func.count())
            .select_from(Appointment)
            .join(Doctor, Doctor.doctor_id == Appointment.doctor_id)
            .where(
                Doctor.hospital_id == hospital_id,
                Appointment.created_at >= start_this_month,
                Appointment.created_at < start_next_month,
            )
        )
    ).scalar_one()

    last_month_doctors = (
        await db.execute(
            select(func.count())
            .select_from(Doctor)
            .where(
                Doctor.hospital_id == hospital_id,
                Doctor.created_at >= start_last_month,
                Doctor.created_at < start_this_month,
            )
        )
    ).scalar_one()

    this_month_doctors = (
        await db.execute(
            select(func.count())
            .select_from(Doctor)
            .where(
                Doctor.hospital_id == hospital_id,
                Doctor.created_at >= start_this_month,
                Doctor.created_at < start_next_month,
            )
        )
    ).scalar_one()

    total_revenue_raw = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0.0))
            .select_from(Payment)
            .join(Appointment, Appointment.appointment_id == Payment.appointment_id)
            .join(Doctor, Doctor.doctor_id == Appointment.doctor_id)
            .where(
                Doctor.hospital_id == hospital_id,
                Payment.status == PaymentTransactionStatusEnum.SUCCESS,
            )
        )
    ).scalar_one()

    return HospitalAdminDashboardSummary(
        total_doctors=total_doctors,
        total_appointments=total_appointments,
        total_revenue=float(total_revenue_raw or 0.0),
        total_departments=total_departments,
        appointments_monthly=AppointmentMonthlyStats(
            last_month=last_month_appointments,
            this_month=this_month_appointments,
            percentage_rise=_calculate_percentage_rise(
                last_month_appointments, this_month_appointments
            ),
            trend_type=_get_trend_type(
                last_month_appointments, this_month_appointments
            ),
        ),
        doctors_monthly=DoctorMonthlyStats(
            last_month=last_month_doctors,
            this_month=this_month_doctors,
            percentage_rise=_calculate_percentage_rise(
                last_month_doctors, this_month_doctors
            ),
            trend_type=_get_trend_type(last_month_doctors, this_month_doctors),
        ),
    )
