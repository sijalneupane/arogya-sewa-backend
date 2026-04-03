from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.common.enums.payment_method_enum import PaymentMethodEnum
from app.common.enums.payment_transaction_status_enum import (
    PaymentTransactionStatusEnum,
)
from app.common.enums.payment_type_enum import PaymentTypeEnum
from app.common.schema.pagination import PaginationQuery
from app.modules.user.v1.schema import UserResponse


class KhaltiAdvancePaymentRequest(BaseModel):
    """Request to initiate Khalti advance payment for appointment booking."""

    appointment_id: str = Field(
        ..., min_length=8, max_length=8, description="Appointment ID"
    )
    amount_paisa: int = Field(..., gt=0, description="Advance amount in paisa")
    customer_phone: str = Field(..., description="Customer Khalti ID/phone number")


class KhaltiFinalPaymentRequest(BaseModel):
    """Request to initiate Khalti final payment for appointment completion."""

    appointment_id: str = Field(
        ..., min_length=8, max_length=8, description="Appointment ID"
    )
    amount_paisa: int = Field(..., gt=0, description="Final payment amount in paisa")
    customer_phone: str = Field(..., description="Customer Khalti ID/phone number")


class KhaltiInitiatePaymentResponse(BaseModel):
    """Response after initiating Khalti payment"""

    pidx: str = Field(..., description="Khalti payment identifier")
    payment_url: str = Field(..., description="URL for user to complete payment")
    expires_at: str = Field(..., description="When this payment link expires")
    expires_in: int = Field(..., description="Expiry time in seconds")


class PaymentCallbackRequest(BaseModel):
    """Callback from Khalti after payment is made"""

    pidx: str = Field(..., description="Payment identifier")
    transaction_id: Optional[str] = Field(None, description="Khalti transaction ID")
    tidx: Optional[str] = Field(None, description="Transaction index")
    status: str = Field(
        ..., description="Payment status (Completed, Pending, User canceled, etc)"
    )
    amount: int = Field(..., description="Amount in paisa")
    total_amount: int = Field(..., description="Total amount in paisa")
    mobile: Optional[str] = Field(None, description="User Khalti ID")
    purchase_order_id: str = Field(..., description="Our order ID (appointment_id)")
    purchase_order_name: str = Field(..., description="Order name")


class PaymentCreateSchema(BaseModel):
    """Schema for creating a payment record"""

    appointment_id: str = Field(..., description="Appointment ID")
    paid_by_user_id: str = Field(..., description="User making payment")
    amount: float = Field(..., gt=0, description="Amount paid in rupees")
    payment_method: PaymentMethodEnum = Field(
        ..., description="Payment method (Khalti, Esewa, Cash)"
    )
    payment_type: PaymentTypeEnum = Field(..., description="Payment type")
    status: PaymentTransactionStatusEnum = Field(
        default=PaymentTransactionStatusEnum.PENDING
    )
    transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    gateway_ref: Optional[str] = Field(
        None, description="Khalti pidx or gateway reference"
    )
    remarks: Optional[str] = Field(None, description="Payment remarks")
    paid_at: Optional[datetime] = Field(
        None, description="Payment completion timestamp"
    )


class PaymentResponseSchema(BaseModel):
    """Schema for payment response"""

    payment_id: str
    appointment_id: str
    paid_by_user_id: str
    amount: float
    payment_method: PaymentMethodEnum
    payment_type: PaymentTypeEnum
    status: PaymentTransactionStatusEnum
    transaction_id: Optional[str] = None
    gateway_ref: Optional[str] = None
    remarks: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_by: Optional[UserResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CashPaymentRecordRequest(BaseModel):
    """Request body for recording a cash payment."""

    appointment_id: str = Field(..., description="Appointment ID")
    amount: float = Field(..., gt=0, description="Amount in rupees")
    user_id: str = Field(..., description="User making payment")
    remarks: Optional[str] = Field(None, description="Payment remarks")


class PaymentFilterQuery(PaginationQuery):
    """Filter and pagination query for payment list endpoints."""

    status: Optional[PaymentTransactionStatusEnum] = Field(
        None,
        description="Filter by payment transaction status",
    )
    from_date: Optional[date] = Field(
        None,
        description="Filter payments from this date (inclusive)",
    )
    to_date: Optional[date] = Field(
        None,
        description="Filter payments up to this date (inclusive)",
    )


class AppointmentBookingWithPaymentRequest(BaseModel):
    """Request for booking appointment with Khalti payment"""

    availability_id: str = Field(
        ..., min_length=8, max_length=8, description="Availability slot ID"
    )
    reason: Optional[str] = Field(
        None, max_length=500, description="Appointment reason"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")
    doctor_fee: float = Field(
        ..., gt=0, description="Doctor consultation fee in rupees"
    )
    customer_phone: str = Field(..., description="Customer Khalti ID for payment")


class AppointmentBookingPaymentResponse(BaseModel):
    """Response containing appointment and Khalti payment link"""

    appointment_id: str
    payment_info: KhaltiInitiatePaymentResponse
    message: str

    class Config:
        from_attributes = True
