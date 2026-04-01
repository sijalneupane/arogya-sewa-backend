"""add_fcm_token_to_user

Revision ID: f4d2a9c7b1e0
Revises: e1a2f5b7c9d1
Create Date: 2026-04-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4d2a9c7b1e0"
down_revision: Union[str, Sequence[str], None] = "e1a2f5b7c9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("user", sa.Column("fcm_token", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "fcm_token")
