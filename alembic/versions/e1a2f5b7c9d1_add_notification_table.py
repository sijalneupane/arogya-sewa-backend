"""add_notification_table

Revision ID: e1a2f5b7c9d1
Revises: 6c83e613ff57
Create Date: 2026-04-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e1a2f5b7c9d1"
down_revision: Union[str, Sequence[str], None] = "6c83e613ff57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    notification_type_enum = postgresql.ENUM(
        "System",
        "Appointment",
        "Payment",
        "Reminder",
        "Promotion",
        name="notification_type_enum",
        create_type=False,
    )
    notification_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notification",
        sa.Column("notification_id", sa.String(length=12), nullable=False),
        sa.Column("type", notification_type_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "notification_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("has_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("receiver_user_id", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["receiver_user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("notification_id"),
    )
    op.create_index(
        op.f("ix_notification_notification_id"),
        "notification",
        ["notification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_receiver_user_id"),
        "notification",
        ["receiver_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_notification_receiver_user_id"), table_name="notification")
    op.drop_index(op.f("ix_notification_notification_id"), table_name="notification")
    op.drop_table("notification")

    notification_type_enum = postgresql.ENUM(
        "System",
        "Appointment",
        "Payment",
        "Reminder",
        "Promotion",
        name="notification_type_enum",
        create_type=False,
    )
    notification_type_enum.drop(op.get_bind(), checkfirst=True)
