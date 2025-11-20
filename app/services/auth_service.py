from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (  # type: ignore
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.services.user_service import get_user_by_email


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email ")
    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    return user


async def login_user(db: AsyncSession, email: str, password: str):
    try:
        user = await authenticate_user(db, email, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        access = create_access_token({"sub": user.id, "role": user.role.role})
        refresh = create_refresh_token({"sub": user.id})
    except HTTPException as e:
        raise e
    return access, refresh, user
