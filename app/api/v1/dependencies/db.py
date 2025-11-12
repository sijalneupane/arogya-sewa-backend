from contextlib import asynccontextmanager

from app.db.database import AsyncSessionLocal


@asynccontextmanager
async def get_session():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
