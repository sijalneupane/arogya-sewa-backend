"""add completed marker to appointment

Revision ID: 1d4c2b7e8f91
Revises: 8b2d1f0e9c4a
Create Date: 2026-04-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1d4c2b7e8f91"
down_revision: Union[str, Sequence[str], None] = "8b2d1f0e9c4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "appointment",
        sa.Column("completed", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("appointment", "completed")
