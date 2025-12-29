"""update_file_type_enum_using_helper

Revision ID: 7278e1cf8da5
Revises: f989970120af
Create Date: 2025-12-28 00:44:42.213572

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Import the custom enum helper
from app.core.utils.alembi_helpers.enum_helper import upgrade_enum, downgrade_enum


# revision identifiers, used by Alembic.
revision: str = "7278e1cf8da5"
down_revision: Union[str, Sequence[str], None] = "f989970120af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define old and new enum values
OLD_FILE_TYPE_VALUES = ["PROFILE", "LICENSE", "HOSPITAL_LOGO", "HOSPITAL"]

NEW_FILE_TYPE_VALUES = [
    "PROFILE",
    "LICENSE",
    "HOSPITAL_LOGO",
    "HOSPITAL",
    "HOSPITAL_BANNER",
    "MEDICAL_REPORT",
    "PRESCRIPTION",
    "OTHER",
]


def upgrade() -> None:
    """Upgrade schema - add 'document' to FileTypeEnum."""
    upgrade_enum(
        table="file",
        column="file_type",
        enum_name="file_type_enum",
        old_values=OLD_FILE_TYPE_VALUES,
        new_values=NEW_FILE_TYPE_VALUES,
    )


def downgrade() -> None:
    """Downgrade schema - remove 'document' from FileTypeEnum."""
    downgrade_enum(
        table="file",
        column="file_type",
        enum_name="file_type_enum",
        old_values=OLD_FILE_TYPE_VALUES,
        new_values=NEW_FILE_TYPE_VALUES,
    )
