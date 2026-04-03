"""add payment type enum to payment

Revision ID: e4d9b3a17c5f
Revises: c7e4d1a9f2b8
Create Date: 2026-04-03 00:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e4d9b3a17c5f"
down_revision: Union[str, Sequence[str], None] = "c7e4d1a9f2b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


payment_type_enum_ddl = postgresql.ENUM(
    "Appointment advance",
    "Appointment clear",
    name="payment_type_enum",
)

payment_type_enum = postgresql.ENUM(
    "Appointment advance",
    "Appointment clear",
    name="payment_type_enum",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    payment_type_enum_ddl.create(bind, checkfirst=True)

    op.add_column(
        "payment",
        sa.Column(
            "payment_type",
            payment_type_enum,
            nullable=False,
            server_default="Appointment clear",
        ),
    )
    op.alter_column("payment", "payment_type", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("payment", "payment_type")

    bind = op.get_bind()
    payment_type_enum_ddl.drop(bind, checkfirst=True)
