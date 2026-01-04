"""update appointment status to use enum

Revision ID: 94a1f4620462
Revises: 082e0c7d0dfd
Create Date: 2026-01-04 00:42:31.877184

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "94a1f4620462"
down_revision: Union[str, Sequence[str], None] = "082e0c7d0dfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the enum type with lowercase values (matching the StrEnum values)
    appointment_status_enum = sa.Enum(
        "scheduled",
        "confirmed",
        "inprogress",
        "completed",
        "cancelled",
        "rescheduled",
        name="appointment_status_enum",
    )
    appointment_status_enum.create(op.get_bind(), checkfirst=True)

    # Drop the existing default first
    op.alter_column("appointment", "status", server_default=None)

    # Alter the column to use the enum type with USING clause for data conversion
    op.execute("""
        ALTER TABLE appointment 
        ALTER COLUMN status TYPE appointment_status_enum 
        USING status::text::appointment_status_enum
    """)

    # Set the new default as enum value
    op.execute(
        "ALTER TABLE appointment ALTER COLUMN status SET DEFAULT 'scheduled'::appointment_status_enum"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the enum default
    op.alter_column("appointment", "status", server_default=None)

    # Convert column back to VARCHAR
    op.execute(
        "ALTER TABLE appointment ALTER COLUMN status TYPE VARCHAR(20) USING status::text"
    )

    # Restore the original default
    op.alter_column(
        "appointment",
        "status",
        server_default=sa.text("'scheduled'::character varying"),
    )

    # Drop the enum type
    sa.Enum(name="appointment_status_enum").drop(op.get_bind(), checkfirst=True)
