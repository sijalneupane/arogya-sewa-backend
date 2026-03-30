from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.utils.string_utils import StringUtils
from app.common.enums.payment_method_enum import PaymentMethodEnum
from app.common.enums.payment_status_enum import PaymentStatusEnum
from app.common.enums.payment_transaction_status_enum import (
    PaymentTransactionStatusEnum,
)
from app.modules.appointment.v1.models import Appointment
from app.modules.doctor.v1.models import Doctor
from app.modules.hospital.v1.models import Hospital
from app.modules.payment.v1.khalti_service import KhaltiGateway, KhaltiGatewayError
from app.modules.payment.v1.models import Payment


def calculate_advance_amount(doctor_fee: float, advance_percentage: float) -> int:
    """
    Calculate advance payment amount in paisa.

    Args:
        doctor_fee: Doctor consultation fee in rupees
        advance_percentage: Percentage for advance

    Returns:
        Advance amount in paisa
    """
    advance_amount_rs = doctor_fee * (advance_percentage / 100)
    # Convert to paisa (multiply by 100)
    advance_amount_paisa = int(advance_amount_rs * 100)
    return advance_amount_paisa


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

    async def create_advance_payment(
        self,
        appointment_id: str,
        paid_by_user_id: str,
        doctor_fee: float,
        customer_phone: str,
        return_url: str,
        website_url: str,
    ) -> dict:
        """Create appointment advance payment request and persist pending transaction."""
        advance_amount_paisa = calculate_advance_amount(
            doctor_fee, self.advance_percentage
        )
        advance_amount_rs = advance_amount_paisa / 100
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
            amount=advance_amount_rs,
            payment_method=PaymentMethodEnum.KHALTI,
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

        if status == "Completed":
            payment.status = PaymentTransactionStatusEnum.SUCCESS
            payment.transaction_id = khalti_response.get("transaction_id")
            payment.paid_at = datetime.now(timezone.utc)

            appointment = await self.db.execute(
                select(Appointment).where(Appointment.appointment_id == appointment_id)
            )
            appt = appointment.scalar_one_or_none()

            if appt:
                appt.payment_status = PaymentStatusEnum.PARTIAL
                appt.paid_amount = payment.amount
                appt.due_amount = appt.total_amount - payment.amount

        elif status == "Pending":
            payment.status = PaymentTransactionStatusEnum.PENDING
            raise HTTPException(
                status_code=202,
                detail="Payment is still pending. Please try again later.",
            )

        elif status in ["User canceled", "Expired"]:
            payment.status = PaymentTransactionStatusEnum.FAILED
            raise HTTPException(status_code=400, detail=f"Payment {status.lower()}")

        else:
            payment.status = PaymentTransactionStatusEnum.FAILED
            raise HTTPException(
                status_code=400,
                detail=f"Payment failed with status: {status}",
            )

        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def record_cash_payment(
        self,
        appointment_id: str,
        paid_by_user_id: str,
        amount: float,
        remarks: Optional[str] = None,
    ) -> Payment:
        """Record a cash payment for remaining appointment dues."""
        payment_id = generate_payment_id()

        payment = Payment(
            payment_id=payment_id,
            appointment_id=appointment_id,
            paid_by_user_id=paid_by_user_id,
            amount=amount,
            payment_method=PaymentMethodEnum.CASH,
            status=PaymentTransactionStatusEnum.SUCCESS,
            paid_at=datetime.now(timezone.utc),
            remarks=remarks or "Cash payment",
        )

        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_appointment_payments(self, appointment_id: str) -> list[Payment]:
        """Get all payments for an appointment."""
        result = await self.db.execute(
            select(Payment)
            .where(Payment.appointment_id == appointment_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_doctor_payments(self, doctor_user_id: str) -> list[Payment]:
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

        result = await self.db.execute(
            select(Payment)
            .join(Appointment, Payment.appointment_id == Appointment.appointment_id)
            .where(Appointment.doctor_id == doctor.doctor_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_hospital_admin_payments(self, admin_user_id: str) -> list[Payment]:
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

        result = await self.db.execute(
            select(Payment)
            .join(Appointment, Payment.appointment_id == Appointment.appointment_id)
            .join(Doctor, Appointment.doctor_id == Doctor.doctor_id)
            .where(Doctor.hospital_id == hospital.hospital_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())


def get_advance_percentage() -> float:
    """Dependency provider for configurable advance payment percentage."""
    return settings.ADVANCE_PAYMENT_PERCENTAGE
