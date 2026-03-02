from typing import TYPE_CHECKING, List

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base
from app.modules.file.v1.models import File

if TYPE_CHECKING:
    from app.modules.department.v1.models import Department
    from app.modules.doctor.v1.models import Doctor
    from app.modules.user.v1.models import User


class Hospital(Base, TimestampMixin):
    __tablename__ = "hospital"

    hospital_id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    contact_number: Mapped[List[str]] = mapped_column(
        ARRAY(String(15)), nullable=False, default=list
    )
    opened_date: Mapped[Date] = mapped_column(Date, nullable=True)
    admin_id: Mapped[str] = mapped_column(
        ForeignKey("user.id"), nullable=False, unique=True
    )

    # Relationships
    # One-to-many: A hospital can have many files (logo, license, images, etc.)
    # Files are differentiated by file_type enum
    files: Mapped[List["File"]] = relationship(
        back_populates="hospital", cascade="all, delete-orphan"
    )
    admin: Mapped["User"] = relationship("User", back_populates="hospital")
    doctors: Mapped[List["Doctor"]] = relationship("Doctor", back_populates="hospital")
    departments: Mapped[List["Department"]] = relationship(
        "Department", back_populates="hospital", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Hospital(hospital_id={self.hospital_id}, name={self.name}, location={self.location})"
