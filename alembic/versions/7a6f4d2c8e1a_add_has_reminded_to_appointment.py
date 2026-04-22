"""add has_reminded to appointment

Revision ID: 7a6f4d2c8e1a
Revises: f2b7c1d9a6e3
Create Date: 2026-04-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a6f4d2c8e1a"
down_revision: Union[str, Sequence[str], None] = "f2b7c1d9a6e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "appointment",
        sa.Column(
            "has_reminded",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_appointment_has_reminded"),
        "appointment",
        ["has_reminded"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_appointment_has_reminded"), table_name="appointment")
    op.drop_column("appointment", "has_reminded")
