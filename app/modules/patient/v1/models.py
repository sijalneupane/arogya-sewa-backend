from typing import TYPE_CHECKING
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.user.v1.models import User


class Patient(Base, TimestampMixin):
    __tablename__ = "patient"

    patient_id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    blood_group: Mapped[str] = mapped_column(String(5), nullable=False)

    # Foreign key to User (required and unique)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id"), nullable=False, unique=True
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="patient")

    def __repr__(self) -> str:
        return f"Patient(id={self.patient_id}, user_id={self.user_id}, gender={self.gender})"
