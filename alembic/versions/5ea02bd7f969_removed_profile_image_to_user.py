"""removed_profile_image_to_user

Revision ID: 5ea02bd7f969
Revises: 441262d971a6
Create Date: 2025-12-21 08:03:54.332333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ea02bd7f969'
down_revision: Union[str, Sequence[str], None] = '441262d971a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
