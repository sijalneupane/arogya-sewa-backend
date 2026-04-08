from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import VARCHAR, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.base import instance_state
from sqlalchemy.types import DateTime

from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

# Only import Role for type-checking (avoids runtime circular import)
if TYPE_CHECKING:
    from app.modules.auth.v1.models import Role
    from app.modules.dashboard.v1.models import ActivityLog
    from app.modules.doctor.v1.models import Doctor
    from app.modules.file.v1.models import File
    from app.modules.hospital.v1.models import Hospital
    from app.modules.notification.v1.models import Notification
    from app.modules.patient.v1.models import Patient


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    fcm_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    otp_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    otp_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    otp_expiry_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
        back_populates="user",
        uselist=False,
    )
    patient: Mapped[Optional["Patient"]] = relationship(
        back_populates="user", uselist=False
    )
    notifications_received: Mapped[list["Notification"]] = relationship(
        back_populates="receiver", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def profile_image(self):
        """Get profile image from files list."""
        from app.common.enums.file_type_enum import FileTypeEnum

        # Check if files relationship is loaded to avoid lazy loading
        state = instance_state(self)
        if "files" not in state.dict or not state.dict.get("files"):
            return None

        if self.files:
            return next(
                (file for file in self.files if file.file_type == FileTypeEnum.PROFILE),
                None,
            )
        return None

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name}, email={self.email}, role_id={self.role_id})"
