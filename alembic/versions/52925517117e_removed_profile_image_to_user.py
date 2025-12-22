"""removed_profile_image_to_user

Revision ID: 52925517117e
Revises: 5ea02bd7f969
Create Date: 2025-12-21 08:04:18.734974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52925517117e'
down_revision: Union[str, Sequence[str], None] = '5ea02bd7f969'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
