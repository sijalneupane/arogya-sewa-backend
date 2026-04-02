import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schema.pagination import PaginatedResponse, PaginationMeta
from app.core.authorization import authorize
from app.core.config import settings
from app.core.configuration.mailgun_config import get_mailgun_service
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.appointment.v1.models import Appointment
from app.modules.appointment.v1.service import get_appointment_by_id
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.email.v1.email_utils import send_appointment_payment_confirmed_email
from app.modules.payment.v1.khalti_service import KhaltiGateway, get_khalti_gateway
from app.modules.payment.v1.schemas import (
    CashPaymentRecordRequest,
    KhaltiAdvancePaymentRequest,
    KhaltiFinalPaymentRequest,
    KhaltiInitiatePaymentResponse,
    PaymentFilterQuery,
    PaymentResponseSchema,
)
from app.modules.payment.v1.service import (
    PaymentService,
    get_advance_percentage,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])


def get_payment_service(
    db: AsyncSession = Depends(get_db),
    khalti_gateway: KhaltiGateway = Depends(get_khalti_gateway),
    advance_percentage: float = Depends(get_advance_percentage),
) -> PaymentService:
    """Dependency provider for payment application service."""
    return PaymentService(
        db=db,
        khalti_gateway=khalti_gateway,
        advance_percentage=advance_percentage,
    )


@router.post("/khalti/initiate", response_model=KhaltiInitiatePaymentResponse)
async def initiate_khalti_advance_payment(
    request: KhaltiAdvancePaymentRequest,
    payment_service: PaymentService = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """
    Initiate Khalti payment for appointment advance (10%).

    This endpoint:
    1. Validates appointment exists
    2. Calculates 10% advance amount
    3. Initiates payment with Khalti Gateway
    4. Creates provisional payment record
    5. Returns pidx and payment_url for frontend redirect
    """
    # Validate appointment exists
    result = await db.execute(
        select(Appointment).where(Appointment.appointment_id == request.appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Generate return URL (frontend should handle payment callback)
    return_url = f"{settings.APP_DOMAIN}/payment/callback"
    website_url = settings.APP_DOMAIN

    # Create advance payment
    payment_info = await payment_service.create_advance_payment(
        appointment_id=request.appointment_id,
        paid_by_user_id=user.sub,
        amount_paisa=request.amount_paisa,
        customer_phone=request.customer_phone,
        return_url=return_url,
        website_url=website_url,
    )

    return KhaltiInitiatePaymentResponse(
        pidx=payment_info["pidx"],
        payment_url=payment_info["payment_url"],
        expires_at=payment_info["expires_at"],
        expires_in=payment_info["expires_in"],
    )


@router.post("/khalti/verify")
async def verify_khalti_advance_payment(
    pidx: str = Query(..., description="Khalti payment identifier"),
    appointment_id: str = Query(..., description="Appointment ID"),
    payment_service: PaymentService = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """
    Verify Khalti payment and complete appointment booking.

    This endpoint:
    1. Verifies payment status with Khalti
    2. Updates payment record with transaction details
    3. Updates appointment to "Partial" payment status
    4. Sends payment confirmation emails
    5. Returns payment confirmation
    """
    try:
        payment = await payment_service.verify_and_complete_advance_payment(
            pidx=pidx,
            appointment_id=appointment_id,
        )

        # Send payment confirmation emails
        try:
            appointment = await get_appointment_by_id(db, appointment_id)
            if appointment and appointment.doctor and appointment.patient:
                mailgun_service = get_mailgun_service()

                doctor_name = (
                    appointment.doctor.user.name
                    if appointment.doctor.user
                    else "Doctor"
                )
                patient_name = (
                    appointment.patient.user.name
                    if appointment.patient.user
                    else "Patient"
                )

                # Format appointment date and time
                appointment_date = (
                    appointment.availability.start_date_time.strftime("%B %d, %Y")
                    if appointment.availability
                    else "TBD"
                )
                appointment_time = (
                    appointment.availability.start_date_time.strftime("%I:%M %p")
                    if appointment.availability
                    else "TBD"
                )

                # Get hospital name
                hospital_name = "Arogya Sewa"
                if appointment.doctor.hospital:
                    hospital_name = appointment.doctor.hospital.name

                remaining_due = (
                    appointment.due_amount if appointment.due_amount > 0 else None
                )

                # Send email to patient
                await send_appointment_payment_confirmed_email(
                    service=mailgun_service,
                    recipient_name=patient_name,
                    recipient_email=appointment.patient.user.email,
                    recipient_type="patient",
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    hospital_name=hospital_name,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    appointment_id=appointment_id,
                    paid_amount=payment.amount,
                    remaining_due=remaining_due,
                )

                # Send email to doctor
                await send_appointment_payment_confirmed_email(
                    service=mailgun_service,
                    recipient_name=doctor_name,
                    recipient_email=appointment.doctor.user.email,
                    recipient_type="doctor",
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    hospital_name=hospital_name,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    appointment_id=appointment_id,
                    paid_amount=payment.amount,
                    remaining_due=remaining_due,
                )

                # Send email to hospital admin if hospital exists
                if appointment.doctor.hospital and appointment.doctor.hospital.admin:
                    admin = appointment.doctor.hospital.admin
                    await send_appointment_payment_confirmed_email(
                        service=mailgun_service,
                        recipient_name=admin.name,
                        recipient_email=admin.email,
                        recipient_type="hospital_admin",
                        patient_name=patient_name,
                        doctor_name=doctor_name,
                        hospital_name=hospital_name,
                        appointment_date=appointment_date,
                        appointment_time=appointment_time,
                        appointment_id=appointment_id,
                        paid_amount=payment.amount,
                        remaining_due=remaining_due,
                    )
        except Exception as email_exc:
            logger.warning(f"Failed to send payment confirmation emails: {email_exc}")

        return {
            "status": "success",
            "message": "Advance payment verified successfully",
            "payment": PaymentResponseSchema.from_orm(payment),
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/khalti/final/initiate", response_model=KhaltiInitiatePaymentResponse)
async def initiate_khalti_final_payment(
    request: KhaltiFinalPaymentRequest,
    payment_service: PaymentService = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """Initiate Khalti final payment for remaining appointment due amount."""
    result = await db.execute(
        select(Appointment).where(Appointment.appointment_id == request.appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return_url = f"{settings.APP_DOMAIN}/payment/callback"
    website_url = settings.APP_DOMAIN

    payment_info = await payment_service.create_final_payment(
        appointment_id=request.appointment_id,
        paid_by_user_id=user.sub,
        amount_paisa=request.amount_paisa,
        customer_phone=request.customer_phone,
        return_url=return_url,
        website_url=website_url,
    )

    return KhaltiInitiatePaymentResponse(
        pidx=payment_info["pidx"],
        payment_url=payment_info["payment_url"],
        expires_at=payment_info["expires_at"],
        expires_in=payment_info["expires_in"],
    )


@router.post("/khalti/final/verify")
async def verify_khalti_final_payment(
    pidx: str = Query(..., description="Khalti payment identifier"),
    appointment_id: str = Query(..., description="Appointment ID"),
    payment_service: PaymentService = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """Verify Khalti final payment and complete appointment payment lifecycle."""
    try:
        payment = await payment_service.verify_and_complete_final_payment(
            pidx=pidx,
            appointment_id=appointment_id,
        )

        # Send payment completion emails
        try:
            appointment = await get_appointment_by_id(db, appointment_id)
            if appointment and appointment.doctor and appointment.patient:
                mailgun_service = get_mailgun_service()

                doctor_name = (
                    appointment.doctor.user.name
                    if appointment.doctor.user
                    else "Doctor"
                )
                patient_name = (
                    appointment.patient.user.name
                    if appointment.patient.user
                    else "Patient"
                )

                # Format appointment date and time
                appointment_date = (
                    appointment.availability.start_date_time.strftime("%B %d, %Y")
                    if appointment.availability
                    else "TBD"
                )
                appointment_time = (
                    appointment.availability.start_date_time.strftime("%I:%M %p")
                    if appointment.availability
                    else "TBD"
                )

                # Get hospital name
                hospital_name = "Arogya Sewa"
                if appointment.doctor.hospital:
                    hospital_name = appointment.doctor.hospital.name

                # Send email to patient (full payment completed)
                await send_appointment_payment_confirmed_email(
                    service=mailgun_service,
                    recipient_name=patient_name,
                    recipient_email=appointment.patient.user.email,
                    recipient_type="patient",
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    hospital_name=hospital_name,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    appointment_id=appointment_id,
                    paid_amount=payment.amount,
                    remaining_due=0,
                )

                # Send email to doctor
                await send_appointment_payment_confirmed_email(
                    service=mailgun_service,
                    recipient_name=doctor_name,
                    recipient_email=appointment.doctor.user.email,
                    recipient_type="doctor",
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    hospital_name=hospital_name,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    appointment_id=appointment_id,
                    paid_amount=payment.amount,
                    remaining_due=0,
                )

                # Send email to hospital admin if hospital exists
                if appointment.doctor.hospital and appointment.doctor.hospital.admin:
                    admin = appointment.doctor.hospital.admin
                    await send_appointment_payment_confirmed_email(
                        service=mailgun_service,
                        recipient_name=admin.name,
                        recipient_email=admin.email,
                        recipient_type="hospital_admin",
                        patient_name=patient_name,
                        doctor_name=doctor_name,
                        hospital_name=hospital_name,
                        appointment_date=appointment_date,
                        appointment_time=appointment_time,
                        appointment_id=appointment_id,
                        paid_amount=payment.amount,
                        remaining_due=0,
                    )
        except Exception as email_exc:
            logger.warning(
                f"Failed to send final payment confirmation emails: {email_exc}"
            )

        return {
            "status": "success",
            "message": "Final payment verified and appointment completed",
            "payment": PaymentResponseSchema.from_orm(payment),
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cash/record", response_model=PaymentResponseSchema)
async def record_cash_payment_endpoint(
    request: CashPaymentRecordRequest,
    payment_service: PaymentService = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """
    Record a cash payment for remaining appointment dues.

    This endpoint:
    1. Records cash payment for appointment
    2. Updates appointment payment status if fully paid
    3. Returns payment record
    """
    # Validate appointment exists
    result = await db.execute(
        select(Appointment).where(Appointment.appointment_id == request.appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    payment = await payment_service.record_cash_payment(
        appointment_id=request.appointment_id,
        paid_by_user_id=user.sub,
        amount=request.amount,
        remarks=request.remarks,
    )

    return PaymentResponseSchema.from_orm(payment)


@router.get("/appointment/{appointment_id}", response_model=list[PaymentResponseSchema])
async def get_appointment_payment_history(
    appointment_id: str,
    payment_service: PaymentService = Depends(get_payment_service),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """Get all payments for an appointment"""
    payments = await payment_service.get_appointment_payments(appointment_id)
    return [PaymentResponseSchema.from_orm(p) for p in payments]


@router.get(
    "/doctor/my-appointments",
    response_model=PaginatedResponse[list[PaymentResponseSchema]],
)
async def get_doctor_payment_records(
    filters: PaymentFilterQuery = Depends(),
    payment_service: PaymentService = Depends(get_payment_service),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """Get all payment records for appointments where the logged-in doctor is involved."""
    payments, total = await payment_service.get_doctor_payments(
        doctor_user_id=user.sub,
        filters=filters,
    )
    return PaginatedResponse(
        message="Doctor payment records fetched successfully",
        data=[PaymentResponseSchema.from_orm(p) for p in payments],
        paginationMeta=PaginationMeta(
            totalPage=math.ceil(total / filters.size) if total else 0,
            currentPage=filters.page,
            pageSize=filters.size,
            totalRecords=total,
        ),
    )


@router.get(
    "/hospital-admin/appointments",
    response_model=PaginatedResponse[list[PaymentResponseSchema]],
)
async def get_hospital_admin_payment_records(
    filters: PaymentFilterQuery = Depends(),
    payment_service: PaymentService = Depends(get_payment_service),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """Get all payment records for appointments handled by doctors in admin's hospital."""

    payments, total = await payment_service.get_hospital_admin_payments(
        admin_user_id=user.sub,
        filters=filters,
    )
    return PaginatedResponse(
        message="Hospital admin payment records fetched successfully",
        data=[PaymentResponseSchema.from_orm(p) for p in payments],
        paginationMeta=PaginationMeta(
            totalPage=math.ceil(total / filters.size) if total else 0,
            currentPage=filters.page,
            pageSize=filters.size,
            totalRecords=total,
        ),
    )
