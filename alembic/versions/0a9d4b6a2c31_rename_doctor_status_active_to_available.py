"""rename doctor status active to available

Revision ID: 0a9d4b6a2c31
Revises: f2b7c1d9a6e3
Create Date: 2026-03-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0a9d4b6a2c31"
down_revision: Union[str, Sequence[str], None] = "f2b7c1d9a6e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE doctorstatusenum RENAME VALUE 'Active' TO 'Available'")
    op.execute(
        "ALTER TABLE doctor ALTER COLUMN status SET DEFAULT 'Available'::doctorstatusenum"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE doctorstatusenum RENAME VALUE 'Available' TO 'Active'")
    op.execute(
        "ALTER TABLE doctor ALTER COLUMN status SET DEFAULT 'Active'::doctorstatusenum"
    )
