from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
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
    start_date_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_date_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_booked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    # Relationships
    doctor: Mapped["Doctor"] = relationship(back_populates="availabilities")

    def __repr__(self) -> str:
        return f"Availability(id={self.availability_id}, doctor_id={self.doctor_id}, start={self.start_date_time})"
