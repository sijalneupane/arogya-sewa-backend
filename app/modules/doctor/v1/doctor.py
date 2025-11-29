# from typing import TYPE_CHECKING, List

# from sqlalchemy import ForeignKey, String
# from sqlalchemy.orm import Mapped, mapped_column, relationship

# from app.models.base import Base
# from app.models.model_mixins.timestamp_mixin import TimestampMixin

# if TYPE_CHECKING:
#     from app.models.user import User


# class Doctor(Base, TimestampMixin):
#     __tablename__ = "doctor"

#     doctor_id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
#     name: Mapped[str] = mapped_column(String(100), nullable=False)
#     specialty: Mapped[str] = mapped_column(String(100), nullable=False)
#     contact_number: Mapped[str] = mapped_column(String(15), nullable=False)
#     email: Mapped[str] = mapped_column(
#         String(100), unique=True, index=True, nullable=False
#     )
#     hospital_id: Mapped[str] = mapped_column(
#         ForeignKey("hospital.hospital_id"), nullable=False
#     )
#     hospital: Mapped[List["User"]] = relationship(
#         back_populates="doctor", cascade="all, delete"
#     )
#     user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=False)
#     users: Mapped[List["User"]] = relationship(
#         back_populates="doctor", cascade="all, delete"
#     )

#     def __repr__(self) -> str:
#         return (
#             f"Doctor(id={self.doctor_id}, name={self.name}, specialty={self.specialty})"
#         )
