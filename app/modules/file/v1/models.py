from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.file_meta_type_enum import FileMetaTypeEnum
from app.common.enums.file_type_enum import FileTypeEnum
from app.common.models.model_mixins.timestamp_mixin import TimestampMixin
from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.user.v1.models import User  # pragma: no cover


class File(Base, TimestampMixin):
    __tablename__ = "file"

    file_id: Mapped[str] = mapped_column(String(8), primary_key=True, index=True)
    public_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    meta_type: Mapped[FileMetaTypeEnum] = mapped_column(
        SQLEnum(FileMetaTypeEnum, name="file_meta_type_enum"), nullable=False
    )
    file_type: Mapped[FileTypeEnum] = mapped_column(
        SQLEnum(FileTypeEnum, name="file_type_enum"), nullable=False
    )

    # Relationship to User model (assuming a user can have multiple files)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="files")  # type
