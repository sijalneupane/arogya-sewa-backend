"""add otp fields to user for password reset

Revision ID: c7e4d1a9f2b8
Revises: b2c3d4e5f6g7
Create Date: 2026-04-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c7e4d1a9f2b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("user", sa.Column("otp_code", sa.String(length=6), nullable=True))
    op.add_column(
        "user",
        sa.Column(
            "otp_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "user",
        sa.Column("otp_expiry_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("user", "otp_verified", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "otp_expiry_time")
    op.drop_column("user", "otp_verified")
    op.drop_column("user", "otp_code")
