"""add_hospital_id_to_file_for_many_to_one

Revision ID: 0c2730c9b419
Revises: a8a352aa99fa
Create Date: 2025-12-22 05:53:21.101101

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0c2730c9b419"
down_revision: Union[str, Sequence[str], None] = "a8a352aa99fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove the old hospital_license_id column from hospital table
    op.drop_constraint(
        "hospital_hospital_license_id_fkey", "hospital", type_="foreignkey"
    )
    op.drop_column("hospital", "hospital_license_id")

    # Add hospital_id to file table for many-to-one relationship
    op.add_column("file", sa.Column("hospital_id", sa.String(length=8), nullable=True))
    op.create_foreign_key(
        "file_hospital_id_fkey", "file", "hospital", ["hospital_id"], ["hospital_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove hospital_id from file table
    op.drop_constraint("file_hospital_id_fkey", "file", type_="foreignkey")
    op.drop_column("file", "hospital_id")

    # Restore hospital_license_id column to hospital table
    op.add_column(
        "hospital",
        sa.Column("hospital_license_id", sa.String(length=100), nullable=True),
    )
    op.create_foreign_key(
        "hospital_hospital_license_id_fkey",
        "hospital",
        "file",
        ["hospital_license_id"],
        ["file_id"],
    )
