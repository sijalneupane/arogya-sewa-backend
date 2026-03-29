from datetime import date as date_type
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum as SQLEnum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.appointment_status_enum import AppointmentStatusEnum
from app.common.enums.payment_status_enum import PaymentStatusEnum
from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.appointment.v1.changed_time_models import AppointmentChangedTime
    from app.modules.availability.v1.models import Availability
    from app.modules.doctor.v1.models import Doctor
    from app.modules.payment.v1.models import Payment
    from app.modules.patient.v1.models import Patient
    from app.modules.user.v1.models import User


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointment"

    appointment_id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)

    # Foreign keys
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patient.patient_id", ondelete="CASCADE"), nullable=False, index=True
    )
    doctor_id: Mapped[str] = mapped_column(
        ForeignKey("doctor.doctor_id", ondelete="CASCADE"), nullable=False, index=True
    )
    availability_id: Mapped[str] = mapped_column(
        ForeignKey("availability.availability_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One availability slot can only have one appointment
    )
    booked_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    paid_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    due_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    payment_status: Mapped[PaymentStatusEnum] = mapped_column(
        SQLEnum(
            PaymentStatusEnum,
            name="payment_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=PaymentStatusEnum.UNPAID,
        server_default=PaymentStatusEnum.UNPAID.value,
    )
    status: Mapped[AppointmentStatusEnum] = mapped_column(
        SQLEnum(
            AppointmentStatusEnum,
            name="appointment_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=AppointmentStatusEnum.PENDING_PAYMENT,
        server_default=AppointmentStatusEnum.PENDING_PAYMENT.value,
        index=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship()
    doctor: Mapped["Doctor"] = relationship()
    availability: Mapped["Availability"] = relationship()
    booked_by: Mapped["User"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )
    changed_times: Mapped[list["AppointmentChangedTime"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Appointment(id={self.appointment_id}, patient_id={self.patient_id}, doctor_id={self.doctor_id}, status={self.status})"


# Import for mapper registration so relationship("Payment") resolves at runtime.
from app.modules.payment.v1.models import Payment  # noqa: E402,F401
