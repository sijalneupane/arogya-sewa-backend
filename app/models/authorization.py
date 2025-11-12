# from typing import TYPE_CHECKING
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.model_mixins.timestamp_mixin import TimestampMixin
from app.models.role import Role

if TYPE_CHECKING:
    from app.models.role import Role


class Authorization(Base, TimestampMixin):
    __tablename__ = "authorization"
    id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("role.id"), nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    methods: Mapped[List[str]] = mapped_column(JSONB, nullable=False)

    # Use string reference
    role: Mapped["Role"] = relationship(back_populates="authorization")
