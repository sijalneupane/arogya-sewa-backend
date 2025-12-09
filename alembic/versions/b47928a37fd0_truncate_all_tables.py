"""Truncate all tables

Revision ID: b47928a37fd0
Revises: 6aa7b7ef3276
Create Date: 2025-12-09 00:53:13.340026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b47928a37fd0'
down_revision: Union[str, Sequence[str], None] = '6aa7b7ef3276'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
