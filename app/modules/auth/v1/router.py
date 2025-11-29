from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db import get_db
from app.modules.auth.v1.schemas import LoginData, LoginResponse
from app.modules.auth.v1.service import login_user
from app.modules.user.v1.schema import UserCreate, UserResponse
from app.modules.user.v1.schema import UserLogin as LoginSchema
from app.modules.user.v1.service import create_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserResponse)
async def signup(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # try:
    return await create_user(db, data.email, data.password, data.name, data.role)
    #     if not user:
    #         raise HTTPException(status_code=400, detail="Email already registered")
    #     return "user"
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=500, detail="Internal server error" + e.__str__()
    #     )


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginSchema, db: AsyncSession = Depends(get_db)):
    try:
        access, refresh, user = await login_user(db, data.email, data.password)

        return LoginResponse(
            data=LoginData(access_token=access, refresh_token=refresh, user=user)
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Internal server error" + e.__str__()
        )
