from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum

from app.common.enums.notification_type_enum import NotificationTypeEnum
from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.user.v1.models import User


class Notification(Base, TimestampMixin):
    __tablename__ = "notification"

    notification_id: Mapped[str] = mapped_column(
        String(12), primary_key=True, index=True
    )
    type: Mapped[NotificationTypeEnum] = mapped_column(
        SQLEnum(
            NotificationTypeEnum,
            name="notification_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notification_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    has_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    receiver_user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    receiver: Mapped["User"] = relationship(back_populates="notifications_received")

    def __repr__(self) -> str:
        return f"Notification(id={self.notification_id}, receiver_user_id={self.receiver_user_id}, type={self.type})"
