from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.doctor.v1.models import Doctor
    from app.modules.hospital.v1.models import Hospital


class Department(Base, TimestampMixin):
    __tablename__ = "department"

    department_id: Mapped[str] = mapped_column(String(10), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hospital_id: Mapped[str] = mapped_column(
        ForeignKey("hospital.hospital_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    hospital: Mapped["Hospital"] = relationship(
        "Hospital", back_populates="departments"
    )
    # doctors relationship will be mapped later
    # doctors: Mapped[List["Doctor"]] = relationship("Doctor", back_populates="department")

    def __repr__(self) -> str:
        return f"Department(department_id={self.department_id}, name={self.name}, hospital_id={self.hospital_id})"
