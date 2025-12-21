from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums.role_enum import RoleEnum
from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.user.v1.schema import (
    UserByIdResponse,
    UserListResponse,
    UserUpdate,
    UserUpdateResponse,
)
from app.modules.user.v1.service import get_user_by_id, get_user_list, update_user

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("", response_model=UserListResponse)
async def list_users(
    role: Optional[RoleEnum] = Query(None, description="Filter users by role"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of all users.

    Optional query parameter:
    - **role**: Filter users by role (SUPER_ADMIN, HOSPITAL_ADMIN, DOCTOR, PATIENT)
    """
    return await get_user_list(db, role=role)


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


@router.patch(
    "/{user_id}",
    response_model=UserUpdateResponse,
    summary="Update user account",
)
async def update_user_account(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """
    Update user account details.

    - Users can update their own account
    - Super admins can update any user account
    - Updatable fields: email, name, phone_number
    """
    updated_user = await update_user(
        db=db,
        user_id=user_id,
        current_user_id=current_user.sub,
        role=current_user.role,
        **data.model_dump(exclude_unset=True),
    )

    from app.modules.user.v1.schema import UserResponse

    user_response = UserResponse.model_validate(updated_user)
    return UserUpdateResponse(data=user_response)
