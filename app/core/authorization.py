# core/authorization.py

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.db import get_db
from app.core.security import get_current_user
from app.models.authorization import Authorization
from app.models.role import Role


async def authorize(
    request: Request,
    user=Depends(get_current_user),  # Ensure JWT + User is loaded
    db: AsyncSession = Depends(get_db),
):
    user_role = user.get("role")
    path = request.scope["route"].path
    method = request.method

    role_result = await db.execute(select(Role).where(Role.role == user_role))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(404, "Role not found")

    print(
        f"Authorizing user with role: {user_role} for path: {path} and method: {method}"
    )
    # Check DB for path + method + role + organization
    permission = await db.execute(
        select(Authorization).where(
            Authorization.role_id == role.id,
            Authorization.path == path,
        )
    )
    permission = permission.scalar_one_or_none()
    if not permission:
        raise HTTPException(403, "Access denied to this path")

    if method not in permission.methods:
        raise HTTPException(403, "Method not allowed")

    return True
