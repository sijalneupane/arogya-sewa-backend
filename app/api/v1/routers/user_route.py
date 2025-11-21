from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.db import get_db
from app.schemas.user import UserByIdResponse, UserListResponse
from app.services.user_service import get_user_by_id, get_user_list

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/", response_model=UserListResponse)
async def list_users(db: AsyncSession = Depends(get_db)):
    return await get_user_list(db)


@router.get("/{user_id}", response_model=UserByIdResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    return await get_user_by_id(db, user_id)
