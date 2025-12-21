from typing import TYPE_CHECKING, Optional

from sqlalchemy import VARCHAR, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

# Only import Role for type-checking (avoids runtime circular import)
if TYPE_CHECKING:
    from app.modules.auth.v1.models import Role
    from app.modules.doctor.v1.models import Doctor
    from app.modules.file.v1.models import File
    from app.modules.hospital.v1.models import Hospital
    from app.modules.patient.v1.models import Patient


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    password: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    last_login: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("role.id"), nullable=False)

    # Use string reference
    role: Mapped["Role"] = relationship(back_populates="users")
    files: Mapped[list["File"]] = relationship(back_populates="user")
    hospital: Mapped[Optional["Hospital"]] = relationship(
        back_populates="admin", uselist=False
    )
    doctor: Mapped[Optional["Doctor"]] = relationship(
        back_populates="user", uselist=False,
    )
    patient: Mapped[Optional["Patient"]] = relationship(
        back_populates="user", uselist=False
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name}, email={self.email}, role_id={self.role_id})"
