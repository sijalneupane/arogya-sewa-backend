from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.payment_method_enum import PaymentMethodEnum
from app.common.enums.payment_transaction_status_enum import (
    PaymentTransactionStatusEnum,
)
from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.appointment.v1.models import Appointment
    from app.modules.user.v1.models import User


class Payment(Base, TimestampMixin):
    __tablename__ = "payment"

    payment_id: Mapped[str] = mapped_column(String(12), primary_key=True, index=True)
    appointment_id: Mapped[str] = mapped_column(
        ForeignKey("appointment.appointment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paid_by_user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[PaymentMethodEnum] = mapped_column(
        SQLEnum(
            PaymentMethodEnum,
            name="payment_method_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    status: Mapped[PaymentTransactionStatusEnum] = mapped_column(
        SQLEnum(
            PaymentTransactionStatusEnum,
            name="payment_transaction_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=PaymentTransactionStatusEnum.PENDING,
        server_default=PaymentTransactionStatusEnum.PENDING.value,
    )
    transaction_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gateway_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="payments")
    paid_by: Mapped["User"] = relationship()
