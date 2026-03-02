"""Doctor status enum and bio

Revision ID: 2b4a25dae686
Revises: 8a17d5d7efa3
Create Date: 2026-03-02 14:30:12.263949

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b4a25dae686"
down_revision: Union[str, Sequence[str], None] = "8a17d5d7efa3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The actual string values stored for DoctorStatusEnum (StrEnum values)
doctor_status_enum = sa.Enum(
    "Active", "On Leave", "On Appointment", "Inactive", name="doctorstatusenum"
)


def upgrade() -> None:
    # 1. Create the PostgreSQL enum type first
    doctor_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add bio column
    op.add_column("doctor", sa.Column("bio", sa.Text(), nullable=True))

    # 3. Drop the old server default so it doesn't block the type change
    op.execute("ALTER TABLE doctor ALTER COLUMN status DROP DEFAULT")

    # 4. Alter status column using USING clause to cast existing string data
    op.execute("""
        ALTER TABLE doctor
        ALTER COLUMN status TYPE doctorstatusenum
        USING CASE
            WHEN status = 'active'         THEN 'Active'::doctorstatusenum
            WHEN status = 'on_leave'       THEN 'On Leave'::doctorstatusenum
            WHEN status = 'on_appointment' THEN 'On Appointment'::doctorstatusenum
            WHEN status = 'inactive'       THEN 'Inactive'::doctorstatusenum
            ELSE 'Active'::doctorstatusenum
        END
    """)

    # 5. Set the new default using the enum value
    op.execute(
        "ALTER TABLE doctor ALTER COLUMN status SET DEFAULT 'Active'::doctorstatusenum"
    )


def downgrade() -> None:
    # 1. Drop the enum default first
    op.execute("ALTER TABLE doctor ALTER COLUMN status DROP DEFAULT")

    # 2. Convert enum column back to VARCHAR
    op.execute("""
        ALTER TABLE doctor
        ALTER COLUMN status TYPE VARCHAR(50)
        USING status::VARCHAR
    """)

    # 3. Restore the old default
    op.execute("ALTER TABLE doctor ALTER COLUMN status SET DEFAULT 'active'")

    # 4. Drop bio column
    op.drop_column("doctor", "bio")

    # 5. Drop the enum type
    doctor_status_enum.drop(op.get_bind(), checkfirst=True)
