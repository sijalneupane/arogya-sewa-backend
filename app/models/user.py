from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.model_mixins.timestamp_mixin import TimestampMixin

# Only import Role for type-checking (avoids runtime circular import)
if TYPE_CHECKING:
    from app.models.role import Role


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("role.id"), nullable=False)

    # Use string reference
    role: Mapped["Role"] = relationship(back_populates="users")

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name}, email={self.email}, role_id={self.role_id})"
