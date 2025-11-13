# alembic/env.py
import sys
from pathlib import Path

from app.models.base import Base  # Import your SQLAlchemy models

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging.config import fileConfig

from sqlalchemy import Enum, engine_from_config, pool

from alembic import context
from app.core.config import settings

# this is the Alembic Config object
config = context.config

# Set the DB URL from your settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ==================== ENUM AUTO-DETECTION HOOK ====================
def _get_enum_values(enum_type):
    """Extract list of .value from Python Enum (StrEnum or regular Enum)"""
    return [member.value for member in enum_type.__members__.values()]


def compare_enums(
    context,
    local_column,
    remote_column,
    local_type,  # TypeEngine for the metadata column (e.g. sqlalchemy.Enum)
    remote_type,  # TypeEngine for the DB-reflected column (e.g. postgresql.ENUM)
):
    """
    Custom compare_type function using the Alembic expected signature:
    (context, local_column, remote_column, local_type, remote_type).
    Returns True if enum members differ → forces Alembic to generate a diff.
    """
    # Only consider SQLAlchemy Enum types that reference a Python enum class
    if not isinstance(local_type, Enum) or not hasattr(local_type, "enum_class"):
        return False

    # Remote type from the DB should expose 'enums' (Postgres ENUM); otherwise skip
    if not hasattr(remote_type, "enums"):
        return False

    py_values = set(_get_enum_values(local_type.enum_class))
    db_values = set(remote_type.enums)

    if py_values != db_values:
        # Optional: log for debugging; derive table/column names if available
        try:
            table_name = getattr(local_column, "table", None)
            table_name = table_name.name if table_name is not None else None
        except Exception:
            table_name = None

        col_name = getattr(local_column, "name", None) or getattr(
            remote_column, "name", None
        )

        print(
            f"Enum changed: {table_name}.{col_name} | "
            f"Python: {sorted(py_values)} | DB: {sorted(db_values)}"
        )
        return True  # Force migration generation

    return False


# =====================================================================


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=compare_enums,  # Add here
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    print("Tables in metadata:", Base.metadata.tables.keys())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=compare_enums,  # Add here
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
