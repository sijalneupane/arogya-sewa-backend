"""remove on appointment and rename available to active

Revision ID: 7c1d9e4b2a11
Revises: 0a9d4b6a2c31
Create Date: 2026-04-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c1d9e4b2a11"
down_revision: Union[str, Sequence[str], None] = "0a9d4b6a2c31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE doctorstatusenum RENAME TO doctorstatusenum_old")

    op.execute(
        """
        CREATE TYPE doctorstatusenum AS ENUM (
            'Active',
            'On Leave',
            'Inactive'
        )
        """
    )

    op.execute("ALTER TABLE doctor ALTER COLUMN status DROP DEFAULT")

    op.execute(
        """
        ALTER TABLE doctor
        ALTER COLUMN status TYPE doctorstatusenum
        USING (
            CASE
                WHEN status::text = 'Available' THEN 'Active'
                WHEN status::text = 'Active' THEN 'Active'
                WHEN status::text = 'On Leave' THEN 'On Leave'
                WHEN status::text = 'On Appointment' THEN 'Active'
                WHEN status::text = 'Inactive' THEN 'Inactive'
                ELSE 'Active'
            END
        )::doctorstatusenum
        """
    )

    op.execute(
        "ALTER TABLE doctor ALTER COLUMN status SET DEFAULT 'Active'::doctorstatusenum"
    )

    op.execute("DROP TYPE doctorstatusenum_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE doctorstatusenum RENAME TO doctorstatusenum_new")

    op.execute(
        """
        CREATE TYPE doctorstatusenum AS ENUM (
            'Active',
            'On Leave',
            'On Appointment',
            'Inactive'
        )
        """
    )

    op.execute("ALTER TABLE doctor ALTER COLUMN status DROP DEFAULT")

    op.execute(
        """
        ALTER TABLE doctor
        ALTER COLUMN status TYPE doctorstatusenum
        USING (
            CASE
                WHEN status::text = 'Active' THEN 'Available'
                WHEN status::text = 'On Leave' THEN 'On Leave'
                WHEN status::text = 'Inactive' THEN 'Inactive'
                ELSE 'Available'
            END
        )::doctorstatusenum
        """
    )

    op.execute(
        "ALTER TABLE doctor ALTER COLUMN status SET DEFAULT 'Available'::doctorstatusenum"
    )

    op.execute("DROP TYPE doctorstatusenum_new")
