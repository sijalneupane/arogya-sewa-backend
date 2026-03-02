from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schema.pagination import PaginatedResponse, PaginationMeta
from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.user.v1.schema import (
    FilterUserList,
    UserByIdResponse,
    UserResponse,
    UserUpdate,
    UserUpdateResponse,
)
from app.modules.user.v1.service import get_user_by_id, get_user_list, update_user

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("")
async def list_users(
    filters: FilterUserList = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[UserResponse]]:
    """
    Get list of all users with pagination.

    Optional query parameters:
    - **role**: Filter users by role (SUPER_ADMIN, HOSPITAL_ADMIN, DOCTOR, PATIENT)
    - **name**: Search by user name
    - **page**: Page number (default: 1)
    - **size**: Number of items per page (default: 10, max: 500)
    """
    users, total = await get_user_list(db, filters=filters)
    user_responses = [UserResponse.model_validate(user) for user in users]
    total_pages = (total + filters.size - 1) // filters.size if total > 0 else 0
    return PaginatedResponse(
        message="User list fetched successfully",
        data=user_responses,
        paginationMeta=PaginationMeta(
            totalPage=total_pages,
            currentPage=filters.page,
            pageSize=filters.size,
            totalRecords=total,
        ),
    )


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
