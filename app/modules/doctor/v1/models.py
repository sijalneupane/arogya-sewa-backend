from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.doctor_status_enum import DoctorStatusEnum
from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.availability.v1.models import Availability
    from app.modules.department.v1.models import Department
    from app.modules.file.v1.models import File
    from app.modules.hospital.v1.models import Hospital
    from app.modules.user.v1.models import User


class Doctor(Base, TimestampMixin):
    __tablename__ = "doctor"

    doctor_id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    experience: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="No experience."
    )
    status: Mapped[DoctorStatusEnum] = mapped_column(
        Enum(DoctorStatusEnum, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DoctorStatusEnum.ACTIVE,
    )
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    booking_fee: Mapped[float] = mapped_column(nullable=False, default=100.0)
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

    # Foreign key to Department (optional)
    department_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("department.department_id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    license_certificate: Mapped["File"] = relationship(
        uselist=False, back_populates="doctor_license"
    )
    user: Mapped["User"] = relationship(back_populates="doctor")
    hospital: Mapped[Optional["Hospital"]] = relationship(back_populates="doctors")
    department: Mapped[Optional["Department"]] = relationship(back_populates="doctors")
    availabilities: Mapped[list["Availability"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Doctor(id={self.doctor_id}, department_id={self.department_id}, user_id={self.user_id})"
