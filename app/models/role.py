from typing import TYPE_CHECKING, List

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.role_enum import RoleEnum
from app.models.base import Base
from app.models.model_mixins.timestamp_mixin import TimestampMixin

if TYPE_CHECKING:
    from models.authorization import Authorization  # pragma: no cover

    from app.models.user import User  # pragma: no cover


class Role(Base, TimestampMixin):
    __tablename__ = "role"

    id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    # Use string reference to avoid circular import
    users: Mapped[List["User"]] = relationship(
        back_populates="role", cascade="all, delete"
    )
    authorization: Mapped[List["Authorization"]] = relationship(
        back_populates="role", cascade="all, delete"
    )
