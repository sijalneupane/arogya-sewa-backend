"""refactor_availability_use_datetime_fields

Revision ID: e85605c2bfd7
Revises: c6a07dc01801
Create Date: 2025-12-30 15:16:12.785056

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e85605c2bfd7"
down_revision: Union[str, Sequence[str], None] = "c6a07dc01801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new datetime columns
    op.add_column(
        "availability", sa.Column("start_date_time", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "availability", sa.Column("end_date_time", sa.DateTime(), nullable=True)
    )

    # Migrate data: combine date and time fields into datetime fields
    op.execute("""
        UPDATE availability
        SET start_date_time = (date::timestamp + start_time::interval),
            end_date_time = (date::timestamp + end_time::interval)
    """)

    # Make the new columns non-nullable
    op.alter_column("availability", "start_date_time", nullable=False)
    op.alter_column("availability", "end_date_time", nullable=False)

    # Drop old columns
    op.drop_column("availability", "date")
    op.drop_column("availability", "start_time")
    op.drop_column("availability", "end_time")


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the old columns
    op.add_column("availability", sa.Column("date", sa.Date(), nullable=True))
    op.add_column("availability", sa.Column("start_time", sa.Time(), nullable=True))
    op.add_column("availability", sa.Column("end_time", sa.Time(), nullable=True))

    # Migrate data back: extract date and time from datetime fields
    op.execute("""
        UPDATE availability
        SET date = start_date_time::date,
            start_time = start_date_time::time,
            end_time = end_date_time::time
    """)

    # Make the old columns non-nullable
    op.alter_column("availability", "date", nullable=False)
    op.alter_column("availability", "start_time", nullable=False)
    op.alter_column("availability", "end_time", nullable=False)

    # Drop new datetime columns
    op.drop_column("availability", "start_date_time")
    op.drop_column("availability", "end_date_time")
