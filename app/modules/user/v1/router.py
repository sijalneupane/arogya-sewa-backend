from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.user.v1.schema import UserByIdResponse, UserListResponse
from app.modules.user.v1.service import get_user_by_id, get_user_list

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("", response_model=UserListResponse)
async def list_users(db: AsyncSession = Depends(get_db)):
    return await get_user_list(db)


@router.get(
    "/{user_id}",
    response_model=UserByIdResponse,
)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    _=Depends(authorize),
):
    return await get_user_by_id(db, user_id)
