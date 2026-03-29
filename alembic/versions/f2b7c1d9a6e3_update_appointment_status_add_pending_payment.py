"""update appointment status add pending payment

Revision ID: f2b7c1d9a6e3
Revises: d1f7a1c2b3e4
Create Date: 2026-03-29 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f2b7c1d9a6e3"
down_revision: Union[str, Sequence[str], None] = "d1f7a1c2b3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE appointment_status_enum RENAME TO appointment_status_enum_old"
    )

    op.execute(
        """
        CREATE TYPE appointment_status_enum AS ENUM (
            'pending_payment',
            'confirmed',
            'inprogress',
            'completed',
            'cancelled',
            'rescheduled'
        )
        """
    )

    op.execute("ALTER TABLE appointment ALTER COLUMN status DROP DEFAULT")

    op.execute(
        """
        ALTER TABLE appointment
        ALTER COLUMN status TYPE appointment_status_enum
        USING (
            CASE
                WHEN status::text = 'scheduled' THEN 'pending_payment'
                ELSE status::text
            END
        )::appointment_status_enum
        """
    )

    op.execute(
        "ALTER TABLE appointment ALTER COLUMN status SET DEFAULT 'pending_payment'::appointment_status_enum"
    )

    op.execute("DROP TYPE appointment_status_enum_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TYPE appointment_status_enum RENAME TO appointment_status_enum_new"
    )

    op.execute(
        """
        CREATE TYPE appointment_status_enum AS ENUM (
            'scheduled',
            'confirmed',
            'inprogress',
            'completed',
            'cancelled',
            'rescheduled'
        )
        """
    )

    op.execute("ALTER TABLE appointment ALTER COLUMN status DROP DEFAULT")

    op.execute(
        """
        ALTER TABLE appointment
        ALTER COLUMN status TYPE appointment_status_enum
        USING (
            CASE
                WHEN status::text = 'pending_payment' THEN 'scheduled'
                ELSE status::text
            END
        )::appointment_status_enum
        """
    )

    op.execute(
        "ALTER TABLE appointment ALTER COLUMN status SET DEFAULT 'scheduled'::appointment_status_enum"
    )

    op.execute("DROP TYPE appointment_status_enum_new")
