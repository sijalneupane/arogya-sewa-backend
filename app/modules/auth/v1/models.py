from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum

from app.common.enums.role_enum import RoleEnum
from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.user.v1.models import User


class Authorization(Base, TimestampMixin):
    __tablename__ = "authorization"
    id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("role.id"), nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    methods: Mapped[List[str]] = mapped_column(JSONB, nullable=False)

    # Use string reference
    role: Mapped["Role"] = relationship(back_populates="authorization")


class Role(Base, TimestampMixin):
    __tablename__ = "role"

    id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    role: Mapped[RoleEnum] = mapped_column(
        SQLEnum(RoleEnum, name="role_enum"), nullable=False
    )
    description: Mapped[str] = mapped_column(String, nullable=True)

    # Use string reference to avoid circular import
    users: Mapped[List["User"]] = relationship(
        back_populates="role", cascade="all, delete"
    )
    authorization: Mapped[List["Authorization"]] = relationship(
        back_populates="role", cascade="all, delete"
    )
