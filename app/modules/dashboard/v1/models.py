from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.activity_log_action_type_enum import ActivityLogActionTypeEnum
from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

# Only import for type-checking (avoids runtime circular import)
if TYPE_CHECKING:
    from app.modules.user.v1.models import User


class ActivityLog(Base, TimestampMixin):
    __tablename__ = "activity_logs"

    activity_log_id: Mapped[str] = mapped_column(
        String(10), primary_key=True, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=False)
    hospital_id: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    action_type: Mapped[ActivityLogActionTypeEnum] = mapped_column(
        Enum(ActivityLogActionTypeEnum, name="activity_log_action_type_enum"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="activity_logs")
