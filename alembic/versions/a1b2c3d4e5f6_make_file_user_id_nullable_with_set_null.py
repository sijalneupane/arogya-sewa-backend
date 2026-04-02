"""Make file.user_id nullable with SET NULL cascade

Revision ID: a1b2c3d4e5f6
Revises: f989970120af
Create Date: 2026-04-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "3f7d2b9c8a44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: make file.user_id nullable with SET NULL cascade."""
    # Drop the existing non-nullable foreign key constraint
    op.drop_constraint("file_user_id_fkey", "file", type_="foreignkey")

    # Alter the column to be nullable
    op.alter_column("file", "user_id", existing_type=sa.String(8), nullable=True)

    # Create new foreign key with ondelete='SET NULL'
    op.create_foreign_key(
        "file_user_id_fkey", "file", "user", ["user_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    """Downgrade schema: revert to non-nullable user_id."""
    # Drop the SET NULL foreign key
    op.drop_constraint("file_user_id_fkey", "file", type_="foreignkey")

    # Alter the column back to non-nullable
    op.alter_column("file", "user_id", existing_type=sa.String(8), nullable=False)

    # Recreate the original non-nullable foreign key
    op.create_foreign_key("file_user_id_fkey", "file", "user", ["user_id"], ["id"])
