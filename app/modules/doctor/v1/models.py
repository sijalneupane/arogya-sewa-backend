from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.availability.v1.models import Availability
    from app.modules.file.v1.models import File
    from app.modules.hospital.v1.models import Hospital
    from app.modules.user.v1.models import User


class Doctor(Base, TimestampMixin):
    __tablename__ = "doctor"

    doctor_id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    specialization_department: Mapped[str] = mapped_column(String(100), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    booking_fee: Mapped[float] = mapped_column(nullable=False, default=0.0)
    license_certificate_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("file.file_id"),
        nullable=True,
        unique=True,  # One file can only be used by one doctor
    )

    # Foreign key to User (required)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id"), nullable=False, unique=True
    )

    # Foreign key to Hospital (optional)
    hospital_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("hospital.hospital_id"), nullable=True
    )

    # Relationships
    license_certificate: Mapped["File"] = relationship(
        uselist=False, back_populates="doctor_license"
    )
    user: Mapped["User"] = relationship(back_populates="doctor")
    hospital: Mapped[Optional["Hospital"]] = relationship(back_populates="doctors")
    availabilities: Mapped[list["Availability"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Doctor(id={self.doctor_id}, specialization={self.specialization_department}, user_id={self.user_id})"
