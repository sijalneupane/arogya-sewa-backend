from datetime import date as date_type
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.appointment.v1.changed_time_models import AppointmentChangedTime
    from app.modules.availability.v1.models import Availability
    from app.modules.doctor.v1.models import Doctor
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

    # Appointment details
    appointment_date: Mapped[date_type] = mapped_column(
        Date, nullable=False, index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
        index=True,
    )  # scheduled, completed, cancelled

    # Relationships
    patient: Mapped["Patient"] = relationship()
    doctor: Mapped["Doctor"] = relationship()
    availability: Mapped["Availability"] = relationship()
    booked_by: Mapped["User"] = relationship()
    changed_times: Mapped[list["AppointmentChangedTime"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Appointment(id={self.appointment_id}, patient_id={self.patient_id}, doctor_id={self.doctor_id}, status={self.status})"
