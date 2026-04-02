"""Merge migration heads

Revision ID: b2c3d4e5f6g7
Revises: 3f7d2b9c8a44, a1b2c3d4e5f6
Create Date: 2026-04-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, Sequence[str], None] = ("3f7d2b9c8a44", "a1b2c3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge revisions with no additional schema changes."""


def downgrade() -> None:
    """Downgrade merge revision."""
