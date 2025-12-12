from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.security import pwd_context  ## type: ignore
from app.core.utils.string_utils import StringUtils
from app.modules.auth.v1.models import Role
from app.modules.user.v1.models import User
from app.modules.user.v1.schema import UserByIdResponse, UserListResponse, UserResponse


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    name: str,
    phone_number: str,
    role: RoleEnum,
) -> User:
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            raise HTTPException(status_code=400, detail="Email already registered")

        relatedRole = await db.execute(select(Role).where(Role.role == role))
        hashed_password = pwd_context.hash(password)
        id = StringUtils.randomAlphaNumeric(8)
        new_user = User(
            id=id,
            name=name,
            email=email,
            phone_number=phone_number,
            role=relatedRole.scalar_one(),
            password=hashed_password,
        )

        db.add(new_user)
        await db.flush()  # Changed from commit to flush
        await db.refresh(new_user)

        # Load the user with the role relationship
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == new_user.id)
        )
        user_with_role = result.scalar_one()
        return user_with_role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error" + str(e))


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_list(db: AsyncSession):
    try:
        result = await db.execute(select(User).options(selectinload(User.role)))
        userresult = result.scalars().all()
        reusltList = [UserResponse.model_validate(user) for user in userresult]
        return UserListResponse(data=reusltList)
    except Exception or HTTPException as e:
        raise e


async def get_user_by_id(db: AsyncSession, user_id: str):
    try:
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_response = UserResponse.model_validate(user)
        return UserByIdResponse(data=user_response)
    except Exception or HTTPException as e:
        raise e


async def update_user_role(db: AsyncSession, user_id: str, new_role: RoleEnum) -> User:
    """Update user role. Used internally for role upgrades."""
    try:
        # Get the user
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get the new role
        role_result = await db.execute(select(Role).where(Role.role == new_role))
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Update user role
        user.role_id = role.id
        await db.flush()  # Don't commit here, let caller handle transaction
        await db.refresh(user)

        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
