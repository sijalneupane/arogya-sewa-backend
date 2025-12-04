"""Truncate hospital

Revision ID: 9021b3aa99af
Revises: 3a2627350349
Create Date: 2025-12-04 14:52:14.098713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9021b3aa99af'
down_revision: Union[str, Sequence[str], None] = '3a2627350349'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("TRUNCATE TABLE hospital;")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
