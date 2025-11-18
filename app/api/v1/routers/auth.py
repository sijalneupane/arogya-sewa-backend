from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.db import get_db
from app.schemas.token import Token  # type: ignore
from app.schemas.user import UserCreate, UserResponse
from app.schemas.user import UserLogin as LoginSchema
from app.services.auth_service import login_user  ## type: ignore
from app.services.user_service import create_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserResponse)
async def signup(data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(db, data.email, data.password)
        if not user:
            raise HTTPException(status_code=400, detail="Email already registered")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Internal server error" + e.__str__()
        )


@router.post("/login", response_model=Token)
async def login(data: LoginSchema, db: AsyncSession = Depends(get_db)):
    access, refresh, user = await login_user(db, data.email, data.password)

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }
