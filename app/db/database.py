import os

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("POSTGRES_DB", "fastapi_db")

# ✅ Async database URL uses asyncpg
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# ✅ Sync database URL uses psycopg2
SYNC_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# ------------------ ASYNC ENGINE ------------------
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ------------------ SYNC ENGINE ------------------
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"options": "-c search_path=public"},
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
)
