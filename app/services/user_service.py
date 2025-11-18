from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import pwd_context  ## type: ignore
from app.models.user import User
from app.utils.string_utils import StringUtils


async def create_user(db: AsyncSession, email: str, password: str):
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            return None  # handle in router

        hashed_password = pwd_context.hash(password)
        id = StringUtils.randomAlphaNumeric(8)
        new_user = User(
            id=id,
            email=email,
            hashed_password=hashed_password,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except Exception as e:
        await db.rollback()
        raise e


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
