# app/alembic/helpers/enum.py
from typing import Sequence

from alembic import op


def upgrade_enum(
    table: str,
    column: str,
    enum_name: str,
    old_values: Sequence[str],
    new_values: Sequence[str],
) -> None:
    """
    Full-safe enum migration (works on PG 9.1+).

    1. CREATE TYPE <enum>_new AS ENUM (…)
    2. ALTER TABLE … TYPE <enum>_new USING …::text::<enum>_new
    3. DROP TYPE <enum>
    4. ALTER TYPE <enum>_new RENAME TO <enum>
    """
    tmp_name = f"{enum_name}_new"

    # 1. create new type
    op.execute(
        f"CREATE TYPE {tmp_name} AS ENUM ({', '.join(map(repr, new_values))})"
    )

    # 2. migrate column
    op.execute(
        f"ALTER TABLE {table} "
        f"ALTER COLUMN {column} TYPE {tmp_name} "
        f"USING {column}::text::{tmp_name}"
    )

    # 3. drop old type
    op.execute(f"DROP TYPE IF EXISTS {enum_name}")

    # 4. rename
    op.execute(f"ALTER TYPE {tmp_name} RENAME TO {enum_name}")


def downgrade_enum(
    table: str,
    column: str,
    enum_name: str,
    old_values: Sequence[str],
    new_values: Sequence[str],
) -> None:
    """Swap old to new values – used for downgrade."""
    upgrade_enum(table, column, enum_name, new_values, old_values)