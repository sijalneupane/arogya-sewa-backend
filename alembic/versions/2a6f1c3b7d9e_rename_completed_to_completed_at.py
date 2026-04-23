"""rename appointment completed marker to completed_at

Revision ID: 2a6f1c3b7d9e
Revises: 1d4c2b7e8f91
Create Date: 2026-04-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2a6f1c3b7d9e"
down_revision: Union[str, Sequence[str], None] = "1d4c2b7e8f91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "appointment",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE appointment
        SET completed_at = updated_at
        WHERE completed = 1
        """
    )

    op.drop_column("appointment", "completed")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "appointment",
        sa.Column("completed", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE appointment
        SET completed = 1
        WHERE completed_at IS NOT NULL
        """
    )

    op.drop_column("appointment", "completed_at")
