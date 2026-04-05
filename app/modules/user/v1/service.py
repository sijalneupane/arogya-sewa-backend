from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.file_type_enum import FileTypeEnum
from app.common.enums.role_enum import RoleEnum
from app.core.security import pwd_context  ## type: ignore
from app.core.utils.string_utils import StringUtils
from app.modules.auth.v1.models import Role
from app.modules.file.v1.models import File
from app.modules.user.v1.models import User
from app.modules.user.v1.schema import FilterUserList, UserByIdResponse, UserResponse


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    name: str,
    phone_number: str,
    role: RoleEnum,
    profile_img_id: Optional[str] = None,
) -> User:
    try:
        async with db.begin_nested():
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

            file = None
            if profile_img_id:
                # Fetch the file with user relationship
                file_result = await db.execute(
                    select(File)
                    .options(selectinload(File.user))
                    .where(File.file_id == profile_img_id)
                )
                file = file_result.scalar_one_or_none()
                if not file:
                    raise HTTPException(
                        status_code=400, detail="Invalid profile image ID"
                    )
                if file.file_type != FileTypeEnum.OTHER:
                    raise HTTPException(
                        status_code=400,
                        detail="File should be OTHER for initial profile image",
                    )

            db.add(new_user)
            await db.flush()
            await db.refresh(new_user)

            if file:
                file.user_id = new_user.id
                file.file_type = FileTypeEnum.PROFILE
                await db.flush()

        # Load the user with the role relationship (savepoint released, still within outer transaction)
        result = await db.execute(
            select(User)
            .options(selectinload(User.role), selectinload(User.files))
            .where(User.id == new_user.id)
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


async def get_user_list(
    db: AsyncSession,
    filters: FilterUserList,
) -> Tuple[list, int]:
    """
    Get list of users with filters and pagination.

    Args:
        db: Database session
        filters: FilterUserList with role, search, page, size

    Returns:
        Tuple of (list of User objects, total count)
    """
    try:
        base_query = select(User).options(
            selectinload(User.role), selectinload(User.files)
        )

        # Apply role filter if provided
        if filters.role:
            base_query = base_query.join(Role).where(Role.role == filters.role)

        # Apply search filter if provided
        if filters.search:
            base_query = base_query.where(
                User.name.ilike(f"%{filters.search}%")
                | User.email.ilike(f"%{filters.search}%")
            )

        # Get total count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Apply pagination
        paginated_query = base_query.offset(filters.offset).limit(filters.size)

        result = await db.execute(paginated_query)
        users = list(result.scalars().all())
        return users, total
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_user_by_id(db: AsyncSession, user_id: str):
    try:
        print(f"Fetching user by ID: {user_id}")
        result = await db.execute(
            select(User)
            .options(selectinload(User.role), selectinload(User.files))
            .where(User.id == user_id)
        )

        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_response = UserResponse.model_validate(user)
        return UserByIdResponse(data=user_response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error" + str(e))


async def update_user(
    db: AsyncSession,
    user_id: str,
    current_user_id: str,
    role: RoleEnum,
    email: Optional[str] = None,
    name: Optional[str] = None,
    phone_number: Optional[str] = None,
):
    """Update user account details."""
    try:
        # Get the user
        result = await db.execute(
            select(User)
            .options(selectinload(User.role), selectinload(User.files))
            .where(User.id == user_id)
        )
        user = result.unique().scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Authorization check
        # Super admin can update any user
        # Other users can only update their own account
        if role != RoleEnum.SUPER_ADMIN and user_id != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only update your own account.",
            )

        # Check if email is being changed and if it's already taken
        if email is not None and email != user.email:
            email_check = await db.execute(select(User).where(User.email == email))
            existing_user = email_check.scalar_one_or_none()
            if existing_user:
                raise HTTPException(
                    status_code=400, detail="Email is already registered"
                )
            user.email = email

        # Update fields if provided
        if name is not None:
            user.name = name
        if phone_number is not None:
            user.phone_number = phone_number

        await db.commit()
        await db.refresh(user)

        # Reload with relationships
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
        updated_user = result.scalar_one()

        return updated_user

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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
