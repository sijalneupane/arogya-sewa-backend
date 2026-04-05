from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.doctor_status_enum import DoctorStatusEnum
from app.common.enums.payment_transaction_status_enum import (
    PaymentTransactionStatusEnum,
)
from app.core.utils.string_utils import StringUtils
from app.modules.appointment.v1.models import Appointment
from app.modules.availability.v1.models import Availability
from app.modules.dashboard.v1.models import ActivityLog
from app.modules.dashboard.v1.schema import (
    ActivityLogCreate,
    ActivityLogResponse,
    AppointmentMonthlyStats,
    DashboardActivityFilters,
    DoctorMonthlyStats,
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
