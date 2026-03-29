from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.db.db import get_db
from app.modules.appointment.v1.models import Appointment
from app.modules.payment.v1.khalti_service import KhaltiGateway, get_khalti_gateway
from app.modules.payment.v1.schemas import (
    KhaltiInitiatePaymentRequest,
    KhaltiInitiatePaymentResponse,
    PaymentResponseSchema,
)
from app.modules.payment.v1.service import (
    PaymentService,
    get_advance_percentage,
)

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
async def initiate_khalti_payment(
    request: KhaltiInitiatePaymentRequest,
    payment_service: PaymentService = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db),
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
        paid_by_user_id=appointment.booked_by_user_id,
        doctor_fee=request.doctor_fee,
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
async def verify_khalti_payment(
    pidx: str = Query(..., description="Khalti payment identifier"),
    appointment_id: str = Query(..., description="Appointment ID"),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """
    Verify Khalti payment and complete appointment booking.

    This endpoint:
    1. Verifies payment status with Khalti
    2. Updates payment record with transaction details
    3. Updates appointment to "Partial" payment status
    4. Returns payment confirmation
    """
    try:
        payment = await payment_service.verify_and_complete_advance_payment(
            pidx=pidx,
            appointment_id=appointment_id,
        )

        return {
            "status": "success",
            "message": "Payment verified and appointment booking confirmed",
            "payment": PaymentResponseSchema.from_orm(payment),
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cash/record", response_model=PaymentResponseSchema)
async def record_cash_payment_endpoint(
    appointment_id: str = Query(..., description="Appointment ID"),
    amount: float = Query(..., gt=0, description="Amount in rupees"),
    user_id: str = Query(..., description="User making payment"),
    remarks: str = Query(None, description="Payment remarks"),
    payment_service: PaymentService = Depends(get_payment_service),
    db: AsyncSession = Depends(get_db),
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
        select(Appointment).where(Appointment.appointment_id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    payment = await payment_service.record_cash_payment(
        appointment_id=appointment_id,
        paid_by_user_id=user_id,
        amount=amount,
        remarks=remarks,
    )

    return PaymentResponseSchema.from_orm(payment)


@router.get("/appointment/{appointment_id}", response_model=list[PaymentResponseSchema])
async def get_appointment_payment_history(
    appointment_id: str,
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Get all payments for an appointment"""
    payments = await payment_service.get_appointment_payments(appointment_id)
    return [PaymentResponseSchema.from_orm(p) for p in payments]
