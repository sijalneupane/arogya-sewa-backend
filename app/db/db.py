from contextlib import asynccontextmanager

from app.db.database import AsyncSessionLocal


@asynccontextmanager
async def get_session():
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        # In case of unhandled exceptions, ensure cleanup
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db():
    async with get_session() as session:
        yield session
