"""merge reminder and existing heads

Revision ID: 8b2d1f0e9c4a
Revises: 3cf09e3c0814, 7a6f4d2c8e1a
Create Date: 2026-04-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8b2d1f0e9c4a"
down_revision: Union[str, Sequence[str], None] = ("3cf09e3c0814", "7a6f4d2c8e1a")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge revision with no schema changes."""


def downgrade() -> None:
    """Downgrade merge revision."""
