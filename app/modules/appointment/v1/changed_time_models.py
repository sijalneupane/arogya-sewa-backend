from datetime import datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.appointment.v1.models import Appointment
    from app.modules.user.v1.models import User


class AppointmentChangedTime(Base, TimestampMixin):
    """Model for tracking appointment time changes"""

    __tablename__ = "appointment_changed_time"

    changed_time_id: Mapped[str] = mapped_column(
        String(12), primary_key=True, index=True
    )

    # Foreign key to appointment
    appointment_id: Mapped[str] = mapped_column(
        ForeignKey("appointment.appointment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Changed time details (new time)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Foreign key to the user who made the change (doctor)
    changed_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    appointment: Mapped["Appointment"] = relationship(back_populates="changed_times")
    changed_by: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"AppointmentChangedTime(id={self.changed_time_id}, appointment_id={self.appointment_id}, changed_at={self.changed_at})"
