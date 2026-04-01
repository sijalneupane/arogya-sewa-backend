"""word_case_appointment_status_enum_values

Revision ID: 6c83e613ff57
Revises: 0a9d4b6a2c31
Create Date: 2026-03-31 17:27:30.242418

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6c83e613ff57"
down_revision: Union[str, Sequence[str], None] = "0a9d4b6a2c31"
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
            'Pending Payment',
            'Confirmed',
            'In Progress',
            'Completed',
            'Cancelled',
            'Rescheduled'
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
                WHEN status::text = 'pending_payment' THEN 'Pending Payment'
                WHEN status::text = 'confirmed' THEN 'Confirmed'
                WHEN status::text = 'inprogress' THEN 'In Progress'
                WHEN status::text = 'completed' THEN 'Completed'
                WHEN status::text = 'cancelled' THEN 'Cancelled'
                WHEN status::text = 'rescheduled' THEN 'Rescheduled'
                ELSE status::text
            END
        )::appointment_status_enum
        """
    )

    op.execute(
        "ALTER TABLE appointment ALTER COLUMN status SET DEFAULT 'Pending Payment'::appointment_status_enum"
    )

    op.execute("DROP TYPE appointment_status_enum_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TYPE appointment_status_enum RENAME TO appointment_status_enum_word_case"
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
                WHEN status::text = 'Pending Payment' THEN 'pending_payment'
                WHEN status::text = 'Confirmed' THEN 'confirmed'
                WHEN status::text = 'In Progress' THEN 'inprogress'
                WHEN status::text = 'Completed' THEN 'completed'
                WHEN status::text = 'Cancelled' THEN 'cancelled'
                WHEN status::text = 'Rescheduled' THEN 'rescheduled'
                ELSE status::text
            END
        )::appointment_status_enum
        """
    )

    op.execute(
        "ALTER TABLE appointment ALTER COLUMN status SET DEFAULT 'pending_payment'::appointment_status_enum"
    )

    op.execute("DROP TYPE appointment_status_enum_word_case")
