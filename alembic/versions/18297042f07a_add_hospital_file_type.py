"""add hospital file type

Revision ID: 18297042f07a
Revises: b598a6de0af0
Create Date: 2025-11-13 16:17:48.551498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.enums.file_type_enum import FileTypeEnum
from app.utils.alembi_helpers.enum_helper import downgrade_enum, upgrade_enum


# revision identifiers, used by Alembic.
revision: str = '18297042f07a'
down_revision: Union[str, Sequence[str], None] = 'b598a6de0af0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
OLD = ["profile", "license", "hospital_logo"]
NEW = [e.value for e in FileTypeEnum]

def upgrade() -> None:
    """Upgrade schema."""
    upgrade_enum("file", "file_type", "file_type_enum", OLD, NEW)


def downgrade() -> None:
    """Downgrade schema."""
    downgrade_enum("file", "file_type", "file_type_enum", NEW, OLD)
