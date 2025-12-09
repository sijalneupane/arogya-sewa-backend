from datetime import date as date_type
from datetime import time as time_type
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.doctor.v1.models import Doctor


class Availability(Base, TimestampMixin):
    __tablename__ = "availability"

    availability_id: Mapped[str] = mapped_column(
        String(8), primary_key=True, index=True
    )
    doctor_id: Mapped[str] = mapped_column(
        ForeignKey("doctor.doctor_id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    start_time: Mapped[time_type] = mapped_column(Time, nullable=False)
    end_time: Mapped[time_type] = mapped_column(Time, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    doctor: Mapped["Doctor"] = relationship(back_populates="availabilities")

    def __repr__(self) -> str:
        return f"Availability(id={self.availability_id}, doctor_id={self.doctor_id}, date={self.date})"
