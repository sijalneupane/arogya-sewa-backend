"""merge doctor status and appointment fee branches

Revision ID: 3f7d2b9c8a44
Revises: 7c1d9e4b2a11, e69f686b9802
Create Date: 2026-04-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3f7d2b9c8a44"
down_revision: Union[str, Sequence[str], None] = ("7c1d9e4b2a11", "e69f686b9802")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge revision with no schema changes."""


def downgrade() -> None:
    """Downgrade merge revision."""
