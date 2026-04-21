import logging
from datetime import datetime, time, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from app.common.enums.appointment_status_enum import AppointmentStatusEnum
from app.common.enums.file_type_enum import FileTypeEnum
from app.common.enums.notification_type_enum import NotificationTypeEnum
from app.common.enums.payment_method_enum import PaymentMethodEnum
from app.common.enums.payment_status_enum import PaymentStatusEnum
from app.common.enums.payment_transaction_status_enum import (
    PaymentTransactionStatusEnum,
)
from app.common.enums.payment_type_enum import PaymentTypeEnum
from app.core.config import settings
from app.core.utils.string_utils import StringUtils
from app.modules.appointment.v1.models import Appointment
from app.modules.availability.v1.models import Availability
from app.modules.doctor.v1.models import Doctor
from app.modules.file.v1.models import File
from app.modules.hospital.v1.models import Hospital
from app.modules.notification.v1.service import send_notification
from app.modules.patient.v1.models import Patient
from app.modules.payment.v1.khalti_service import KhaltiGateway, KhaltiGatewayError
from app.modules.payment.v1.models import Payment
from app.modules.payment.v1.schemas import PaymentFilterQuery
from app.modules.user.v1.models import User

logger = logging.getLogger(__name__)


def generate_payment_id() -> str:
    """Generate unique payment ID"""
    return StringUtils.randomAlphaNumeric(12)


class PaymentService:
    """Application service coordinating payment workflow with injected dependencies."""

    def __init__(
        self,
        db: AsyncSession,
        khalti_gateway: KhaltiGateway,
        advance_percentage: float,
    ) -> None:
        self.db = db
        self.khalti_gateway = khalti_gateway
        self.advance_percentage = advance_percentage

    @staticmethod
    def _payment_user_load_options() -> tuple:
        """Load user role and only profile files for payment response serialization."""
        return (
            selectinload(Payment.paid_by).selectinload(User.role),
            selectinload(Payment.paid_by).selectinload(User.files),
            with_loader_criteria(
                File,
                File.file_type == FileTypeEnum.PROFILE,
                include_aliases=True,
            ),
        )

    async def _get_payment_with_user(self, payment_id: str) -> Payment:
        """Fetch a payment with paid-by user details preloaded for API response."""
        result = await self.db.execute(
            select(Payment)
            .options(*self._payment_user_load_options())
            .where(Payment.payment_id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment record not found")
        return payment

    async def _get_appointment_or_404(self, appointment_id: str) -> Appointment:
        result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.availability))
            .where(Appointment.appointment_id == appointment_id)
        )
        appointment = result.scalar_one_or_none()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return appointment

    async def _get_doctor_or_404(self, doctor_id: str) -> Doctor:
        result = await self.db.execute(
            select(Doctor).where(Doctor.doctor_id == doctor_id)
        )
        doctor = result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return doctor

    @staticmethod
    def _round_money(amount: float) -> float:
        return round(float(amount), 2)

    async def _cancel_appointment_and_release_availability(
        self, appointment: Appointment, reason: str
    ) -> None:
        appointment.status = AppointmentStatusEnum.CANCELLED
        appointment.payment_status = PaymentStatusEnum.UNPAID

        availability_result = await self.db.execute(
            select(Availability).where(
                Availability.availability_id == appointment.availability_id
            )
        )
        availability = availability_result.scalar_one_or_none()
        if availability:
            availability.is_booked = False

        await self.db.commit()
        raise HTTPException(status_code=400, detail=reason)

    def _ensure_due_exists_for_settlement(self, appointment: Appointment) -> float:
        """Return normalized due amount and fail if there is nothing left to settle."""
        due_amount = self._round_money(appointment.due_amount)
        if due_amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="No due amount left for final settlement",
            )
        return due_amount

    def _validate_payment_time_window(self, appointment: Appointment) -> None:
        """
        Validate that payment is made within the allowed time window.

        Payment can only be completed:
        - From 10 minutes BEFORE the appointment start time
        - Until the appointment end time

        Args:
            appointment: The appointment with loaded availability

        Raises:
            HTTPException: If current time is outside the allowed payment window
        """
        if not appointment.availability:
            raise HTTPException(
                status_code=400,
                detail="Appointment availability data not found",
            )

        current_time = datetime.now(timezone.utc)
        appointment_start = appointment.availability.start_date_time
        appointment_end = appointment.availability.end_date_time

        # Ensure all datetimes have timezone info
        if appointment_start.tzinfo is None:
            appointment_start = appointment_start.replace(tzinfo=timezone.utc)
        if appointment_end.tzinfo is None:
            appointment_end = appointment_end.replace(tzinfo=timezone.utc)

        # Calculate the allowed payment window
        earliest_payment_time = appointment_start - timedelta(minutes=10)

        # Check if current time is within the window
        if current_time < earliest_payment_time:
            time_until_payment_allowed = (
                earliest_payment_time - current_time
            ).total_seconds() / 60
            raise HTTPException(
                status_code=400,
                detail=f"Payment cannot be made yet. Payment window opens {int(time_until_payment_allowed)} minutes before the appointment.",
            )

        if current_time > appointment_end:
            raise HTTPException(
                status_code=400,
                detail="Payment window has closed. The appointment time has ended.",
            )

    async def create_advance_payment(
        self,
        appointment_id: str,
        paid_by_user_id: str,
        amount_paisa: int,
        customer_phone: str,
        return_url: str,
        website_url: str,
    ) -> dict:
        """Create appointment advance payment request and persist pending transaction."""
        appointment = await self._get_appointment_or_404(appointment_id)

        if appointment.payment_status != PaymentStatusEnum.UNPAID:
            raise HTTPException(
                status_code=400,
                detail="Advance payment is only allowed for unpaid appointments",
            )

        created_at = appointment.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > created_at + timedelta(days=1):
            await self._cancel_appointment_and_release_availability(
                appointment,
                "Advance payment window expired. Appointment has been cancelled.",
            )

        doctor = await self._get_doctor_or_404(appointment.doctor_id)
        expected_advance_amount = self._round_money(
            doctor.booking_fee * (self.advance_percentage / 100)
        )
        expected_advance_amount_paisa = int(round(expected_advance_amount * 100))
        requested_amount_paisa = int(amount_paisa)

        if requested_amount_paisa != expected_advance_amount_paisa:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid advance amount in paisa. "
                    f"Expected {expected_advance_amount_paisa}, got {requested_amount_paisa}."
                ),
            )

        # Validate payment time window
        # self._validate_payment_time_window(appointment)

        advance_amount_paisa = expected_advance_amount_paisa
        payment_id = generate_payment_id()

        try:
            khalti_response = await self.khalti_gateway.initiate_payment(
                amount=advance_amount_paisa,
                purchase_order_id=appointment_id,
                purchase_order_name=f"Appointment booking advance ({self.advance_percentage}%)",
                customer_name="Patient",
                customer_email="patient@arogya.com",
                customer_phone=customer_phone,
                return_url=return_url,
                website_url=website_url,
                merchant_extra=payment_id,
            )
        except KhaltiGatewayError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        payment = Payment(
            payment_id=payment_id,
            appointment_id=appointment_id,
            paid_by_user_id=paid_by_user_id,
            amount=expected_advance_amount,
            payment_method=PaymentMethodEnum.KHALTI,
            payment_type=PaymentTypeEnum.APPOINTMENT_ADVANCE,
            status=PaymentTransactionStatusEnum.PENDING,
            gateway_ref=khalti_response.get("pidx"),
            remarks=f"{self.advance_percentage}% advance payment",
        )

        self.db.add(payment)
        await self.db.commit()

        return {
            "pidx": khalti_response.get("pidx"),
            "payment_url": khalti_response.get("payment_url"),
            "expires_at": khalti_response.get("expires_at"),
            "expires_in": khalti_response.get("expires_in"),
            "payment_id": payment_id,
        }

    async def verify_and_complete_advance_payment(
        self,
        pidx: str,
        appointment_id: str,
    ) -> Payment:
        """Verify Khalti payment and update payment/appointment state."""
        try:
            khalti_response = await self.khalti_gateway.verify_payment(pidx)
        except KhaltiGatewayError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        status = khalti_response.get("status")
        result = await self.db.execute(
            select(Payment).where(Payment.gateway_ref == pidx)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment record not found")

        if payment.appointment_id != appointment_id:
            raise HTTPException(
                status_code=400, detail="Appointment and payment mismatch"
            )

        appointment = await self._get_appointment_or_404(appointment_id)

        if self._round_money(payment.amount) != self._round_money(
            appointment.advance_fee
        ):
            raise HTTPException(
                status_code=400,
                detail="This payment is not a valid advance payment",
            )

        print(
            "-----Advance payment verification response from Khalti:", khalti_response
        )
        print("-----Advance payment status from Khalti:", status)
        if status == "Completed":
            payment.status = PaymentTransactionStatusEnum.SUCCESS
            payment.transaction_id = khalti_response.get("transaction_id")
            payment.paid_at = datetime.now(timezone.utc)
            appointment.payment_status = PaymentStatusEnum.PARTIAL
            appointment.status = AppointmentStatusEnum.CONFIRMED
            appointment.paid_amount = self._round_money(payment.amount)
            appointment.due_amount = self._round_money(
                appointment.total_amount - appointment.paid_amount
            )

        elif status == "Pending":
            payment.status = PaymentTransactionStatusEnum.PENDING
            await self.db.commit()
            raise HTTPException(
                status_code=202,
                detail="Payment is still pending. Please try again later.",
            )

        elif status in ["User canceled", "Expired"]:
            payment.status = PaymentTransactionStatusEnum.FAILED
            await self.db.commit()
            raise HTTPException(status_code=400, detail=f"Payment {status.lower()}")

        else:
            payment.status = PaymentTransactionStatusEnum.FAILED
            await self.db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Payment failed with status: {status}",
            )

        await self.db.commit()

        try:
            notification_appointment = await self._get_appointment_or_404(
                appointment_id
            )
            patient_result = await self.db.execute(
                select(Patient)
                .options(selectinload(Patient.user))
                .where(Patient.patient_id == notification_appointment.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            doctor_result = await self.db.execute(
                select(Doctor)
                .options(selectinload(Doctor.user))
                .where(Doctor.doctor_id == notification_appointment.doctor_id)
            )
            doctor = doctor_result.scalar_one_or_none()

            if patient and patient.user and doctor and doctor.user:
                await send_notification(
                    db=self.db,
                    receiver_user_id=patient.user.id,
                    notification_type=NotificationTypeEnum.PAYMENT,
                    title="Appointment Verified Successfully",
                    body=(
                        f"Your appointment with Dr. {doctor.user.name} has been "
                        f"verified successfully."
                    ),
                    notification_data={
                        "appointment_id": notification_appointment.appointment_id,
                        "doctor_id": doctor.doctor_id,
                        "patient_id": patient.patient_id,
                        "payment_status": notification_appointment.payment_status.value,
                    },
                )
        except Exception as exc:
            logger.warning(
                "Advance payment verified but patient notification failed for appointment %s: %s",
                appointment_id,
                str(exc),
            )

        return await self._get_payment_with_user(payment.payment_id)

    async def create_final_payment(
        self,
        appointment_id: str,
        paid_by_user_id: str,
        amount_paisa: int,
        customer_phone: str,
        return_url: str,
        website_url: str,
    ) -> dict:
        """Create Khalti payment request for remaining due amount."""
        appointment = await self._get_appointment_or_404(appointment_id)

        if appointment.payment_status != PaymentStatusEnum.PARTIAL:
            raise HTTPException(
                status_code=400,
                detail="Final payment requires a successful advance payment",
            )

        remaining_due = self._ensure_due_exists_for_settlement(appointment)
        expected_final_amount_paisa = int(round(remaining_due * 100))
        requested_amount_paisa = int(amount_paisa)

        if requested_amount_paisa != expected_final_amount_paisa:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid final payment amount in paisa. "
                    f"Expected {expected_final_amount_paisa}, got {requested_amount_paisa}."
                ),
            )

        # Validate payment time window
        self._validate_payment_time_window(appointment)

        final_amount_paisa = expected_final_amount_paisa
        payment_id = generate_payment_id()

        try:
            khalti_response = await self.khalti_gateway.initiate_payment(
                amount=final_amount_paisa,
                purchase_order_id=appointment_id,
                purchase_order_name="Appointment final payment",
                customer_name="Patient",
                customer_email="patient@arogya.com",
                customer_phone=customer_phone,
                return_url=return_url,
                website_url=website_url,
                merchant_extra=payment_id,
            )
        except KhaltiGatewayError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        payment = Payment(
            payment_id=payment_id,
            appointment_id=appointment_id,
            paid_by_user_id=paid_by_user_id,
            amount=remaining_due,
            payment_method=PaymentMethodEnum.KHALTI,
            payment_type=PaymentTypeEnum.APPOINTMENT_CLEAR,
            status=PaymentTransactionStatusEnum.PENDING,
            gateway_ref=khalti_response.get("pidx"),
            remarks="Final payment",
        )

        self.db.add(payment)
        await self.db.commit()

        return {
            "pidx": khalti_response.get("pidx"),
            "payment_url": khalti_response.get("payment_url"),
            "expires_at": khalti_response.get("expires_at"),
            "expires_in": khalti_response.get("expires_in"),
            "payment_id": payment_id,
        }

    async def verify_and_complete_final_payment(
        self,
        pidx: str,
        appointment_id: str,
    ) -> Payment:
        """Verify Khalti final payment and close appointment as fully paid."""
        try:
            khalti_response = await self.khalti_gateway.verify_payment(pidx)
        except KhaltiGatewayError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        status = khalti_response.get("status")
        result = await self.db.execute(
            select(Payment).where(Payment.gateway_ref == pidx)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment record not found")

        if payment.appointment_id != appointment_id:
            raise HTTPException(
                status_code=400, detail="Appointment and payment mismatch"
            )

        appointment = await self._get_appointment_or_404(appointment_id)
        remaining_due = self._ensure_due_exists_for_settlement(appointment)

        if self._round_money(payment.amount) != remaining_due:
            raise HTTPException(
                status_code=400,
                detail="This payment is not a valid final payment",
            )

        if appointment.payment_status != PaymentStatusEnum.PARTIAL:
            raise HTTPException(
                status_code=400,
                detail="Appointment is not in partial payment state",
            )

        if status == "Completed":
            payment.status = PaymentTransactionStatusEnum.SUCCESS
            payment.transaction_id = khalti_response.get("transaction_id")
            payment.paid_at = datetime.now(timezone.utc)

            appointment.paid_amount = self._round_money(
                appointment.paid_amount + payment.amount
            )
            appointment.due_amount = 0
            appointment.payment_status = PaymentStatusEnum.PAID
            appointment.status = AppointmentStatusEnum.COMPLETED

        elif status == "Pending":
            payment.status = PaymentTransactionStatusEnum.PENDING
            await self.db.commit()
            raise HTTPException(
                status_code=202,
                detail="Payment is still pending. Please try again later.",
            )

        elif status in ["User canceled", "Expired"]:
            payment.status = PaymentTransactionStatusEnum.FAILED
            await self.db.commit()
            raise HTTPException(status_code=400, detail=f"Payment {status.lower()}")

        else:
            payment.status = PaymentTransactionStatusEnum.FAILED
            await self.db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Payment failed with status: {status}",
            )

        await self.db.commit()

        try:
            notification_appointment = await self._get_appointment_or_404(
                appointment_id
            )
            patient_result = await self.db.execute(
                select(Patient)
                .options(selectinload(Patient.user))
                .where(Patient.patient_id == notification_appointment.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            doctor_result = await self.db.execute(
                select(Doctor)
                .options(selectinload(Doctor.user))
                .where(Doctor.doctor_id == notification_appointment.doctor_id)
            )
            doctor = doctor_result.scalar_one_or_none()

            if patient and patient.user and doctor and doctor.user:
                await send_notification(
                    db=self.db,
                    receiver_user_id=patient.user.id,
                    notification_type=NotificationTypeEnum.PAYMENT,
                    title="Appointment Payment Verified",
                    body=(
                        f"Your final payment for the appointment with Dr. {doctor.user.name} has been verified successfully."
                    ),
                    notification_data={
                        "appointment_id": notification_appointment.appointment_id,
                        "doctor_id": doctor.doctor_id,
                        "patient_id": patient.patient_id,
                        "payment_status": notification_appointment.payment_status.value,
                    },
                )
        except Exception as exc:
            logger.warning(
                "Final payment verified but patient notification failed for appointment %s: %s",
                appointment_id,
                str(exc),
            )

        return await self._get_payment_with_user(payment.payment_id)

    async def record_cash_payment(
        self,
        appointment_id: str,
        paid_by_user_id: str,
        amount: float,
        remarks: Optional[str] = None,
    ) -> Payment:
        """Record a cash payment for final remaining appointment dues."""
        appointment = await self._get_appointment_or_404(appointment_id)

        if appointment.payment_status != PaymentStatusEnum.PARTIAL:
            raise HTTPException(
                status_code=400,
                detail="Cash final payment requires a successful advance payment",
            )

        remaining_due = self._ensure_due_exists_for_settlement(appointment)
        requested_amount = self._round_money(amount)

        if requested_amount != remaining_due:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid cash payment amount. "
                    f"Expected {remaining_due}, got {requested_amount}."
                ),
            )

        # Validate payment time window
        self._validate_payment_time_window(appointment)

        payment_id = generate_payment_id()

        payment = Payment(
            payment_id=payment_id,
            appointment_id=appointment_id,
            paid_by_user_id=paid_by_user_id,
            amount=remaining_due,
            payment_method=PaymentMethodEnum.CASH,
            payment_type=PaymentTypeEnum.APPOINTMENT_CLEAR,
            status=PaymentTransactionStatusEnum.SUCCESS,
            paid_at=datetime.now(timezone.utc),
            remarks=remarks or "Final cash payment",
        )

        appointment.paid_amount = self._round_money(
            appointment.paid_amount + remaining_due
        )
        appointment.due_amount = 0
        appointment.payment_status = PaymentStatusEnum.PAID
        appointment.status = AppointmentStatusEnum.COMPLETED

        self.db.add(payment)
        await self.db.commit()
        return await self._get_payment_with_user(payment.payment_id)

    async def get_appointment_payments(self, appointment_id: str) -> list[Payment]:
        """Get all payments for an appointment."""
        result = await self.db.execute(
            select(Payment)
            .options(*self._payment_user_load_options())
            .where(Payment.appointment_id == appointment_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_doctor_payments(
        self,
        doctor_user_id: str,
        filters: PaymentFilterQuery,
    ) -> tuple[list[Payment], int]:
        """Get all payments for appointments belonging to the logged-in doctor."""
        doctor_result = await self.db.execute(
            select(Doctor).where(Doctor.user_id == doctor_user_id)
        )
        doctor = doctor_result.scalar_one_or_none()

        if not doctor:
            raise HTTPException(
                status_code=403,
                detail="User is not associated with a doctor profile",
            )

        base_query = (
            select(Payment)
            .options(*self._payment_user_load_options())
            .join(Appointment, Payment.appointment_id == Appointment.appointment_id)
            .where(Appointment.doctor_id == doctor.doctor_id)
        )

        count_query = (
            select(func.count())
            .select_from(Payment)
            .join(Appointment, Payment.appointment_id == Appointment.appointment_id)
            .where(Appointment.doctor_id == doctor.doctor_id)
        )

        if filters.status:
            base_query = base_query.where(Payment.status == filters.status)
            count_query = count_query.where(Payment.status == filters.status)

        if filters.from_date:
            from_dt = datetime.combine(filters.from_date, time.min, tzinfo=timezone.utc)
            base_query = base_query.where(Payment.created_at >= from_dt)
            count_query = count_query.where(Payment.created_at >= from_dt)

        if filters.to_date:
            to_dt_exclusive = datetime.combine(
                filters.to_date + timedelta(days=1),
                time.min,
                tzinfo=timezone.utc,
            )
            base_query = base_query.where(Payment.created_at < to_dt_exclusive)
            count_query = count_query.where(Payment.created_at < to_dt_exclusive)

        base_query = base_query.order_by(Payment.created_at.desc())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(
            base_query.offset((filters.page - 1) * filters.size).limit(filters.size)
        )
        return list(result.scalars().all()), total

    async def get_hospital_admin_payments(
        self,
        admin_user_id: str,
        filters: PaymentFilterQuery,
    ) -> tuple[list[Payment], int]:
        """Get all payments for appointments handled by doctors in admin's hospital."""
        hospital_result = await self.db.execute(
            select(Hospital).where(Hospital.admin_id == admin_user_id)
        )
        hospital = hospital_result.scalar_one_or_none()

        if not hospital:
            raise HTTPException(
                status_code=403,
                detail="Hospital admin must be associated with a hospital",
            )

        base_query = (
            select(Payment)
            .options(*self._payment_user_load_options())
            .join(Appointment, Payment.appointment_id == Appointment.appointment_id)
            .join(Doctor, Appointment.doctor_id == Doctor.doctor_id)
            .where(Doctor.hospital_id == hospital.hospital_id)
        )

        count_query = (
            select(func.count())
            .select_from(Payment)
            .join(Appointment, Payment.appointment_id == Appointment.appointment_id)
            .join(Doctor, Appointment.doctor_id == Doctor.doctor_id)
            .where(Doctor.hospital_id == hospital.hospital_id)
        )

        if filters.status:
            base_query = base_query.where(Payment.status == filters.status)
            count_query = count_query.where(Payment.status == filters.status)

        if filters.from_date:
            from_dt = datetime.combine(filters.from_date, time.min, tzinfo=timezone.utc)
            base_query = base_query.where(Payment.created_at >= from_dt)
            count_query = count_query.where(Payment.created_at >= from_dt)

        if filters.to_date:
            to_dt_exclusive = datetime.combine(
                filters.to_date + timedelta(days=1),
                time.min,
                tzinfo=timezone.utc,
            )
            base_query = base_query.where(Payment.created_at < to_dt_exclusive)
            count_query = count_query.where(Payment.created_at < to_dt_exclusive)

        base_query = base_query.order_by(Payment.created_at.desc())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(
            base_query.offset((filters.page - 1) * filters.size).limit(filters.size)
        )
        return list(result.scalars().all()), total


def get_advance_percentage() -> float:
    """Dependency provider for configurable advance payment percentage."""
    return settings.ADVANCE_PAYMENT_PERCENTAGE
