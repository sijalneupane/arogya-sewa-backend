from typing import Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.hospital.v1.models import Hospital
from app.modules.user.v1 import service as UserService
from app.modules.user.v1.models import User
from app.modules.user.v1.service import create_user


async def add_hospital(
    db: AsyncSession,
    name: str,
    address: str,
    contact_number: list[str],
    opened_date,
    admin_name: str,
    admin_email: str,
    admin_password: str,
) -> Hospital:
    try:
        # Create admin user first
        admin_user = await create_user(
            db=db,
            name=admin_name,
            email=admin_email,
            password=admin_password,
            role=RoleEnum.HOSPITAL_ADMIN,
        )

        # Create hospital
        hospital = Hospital(
            hospital_id=StringUtils.randomAlphaNumeric(8),
            name=name,
            address=address,
            contact_number=contact_number,
            opened_date=opened_date,
            admin=admin_user,
        )
        db.add(hospital)
        await db.commit()
        await db.refresh(hospital)

        # Ensure the admin relationship is loaded
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin))
            .where(Hospital.hospital_id == hospital.hospital_id)
        )
        hospital_with_admin = result.scalar_one()
        return hospital_with_admin
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def get_all_hospitals(db: AsyncSession) -> list[Hospital]:
    """Get all hospitals with their admin details."""
    try:
        result = await db.execute(
            select(Hospital).options(
                selectinload(Hospital.admin).selectinload(User.role)
            )
        )
        hospitals = result.scalars().all()
        return list(hospitals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_hospital_by_id(db: AsyncSession, hospital_id: str) -> Hospital:
    """Get a hospital by its ID with admin details."""
    try:
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin).selectinload(User.role))
            .where(Hospital.hospital_id == hospital_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")
        return hospital
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_hospital_by_admin_id(db: AsyncSession, admin_id: str) -> Hospital:
    """Get a hospital by its admin user ID."""
    try:
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin).selectinload(User.role))
            .where(Hospital.admin_id == admin_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(
                status_code=404, detail="Hospital not found for this admin"
            )
        return hospital
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def update_hospital(
    db: AsyncSession,
    hospital_id: str,
    current_user_id: str,
    role: RoleEnum,
    name: Optional[str] = None,
    address: Optional[str] = None,
    contact_number: Optional[list[str]] = None,
    opened_date=None,
) -> Hospital:
    """Update hospital details."""
    try:
        # Get the hospital first
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin).selectinload(User.role))
            .where(Hospital.hospital_id == hospital_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

        # Authorization check
        if role == RoleEnum.SUPER_ADMIN:
            # Super admin can update any hospital
            pass
        elif role == RoleEnum.HOSPITAL_ADMIN:
            # Hospital admin can only update their own hospital
            if hospital.admin_id != current_user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. You can only update your own hospital.",
                )
        else:
            # Other roles are not allowed to update hospitals
            raise HTTPException(
                status_code=403,
                detail="Access denied. Insufficient permissions to update hospital.",
            )

        # Update fields if provided
        if name is not None:
            hospital.name = name
        if address is not None:
            hospital.address = address
        if contact_number is not None:
            hospital.contact_number = contact_number
        if opened_date is not None:
            hospital.opened_date = opened_date

        await db.commit()
        await db.refresh(hospital)

        # Reload with relationships
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin).selectinload(User.role))
            .where(Hospital.hospital_id == hospital_id)
        )
        updated_hospital = result.scalar_one()
        return updated_hospital
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def delete_hospital(
    db: AsyncSession, hospital_id: str, role: RoleEnum, current_user_id: str
):
    """Delete a hospital by its ID."""
    try:
        await db.begin()
        # Get the hospital first
        result = await db.execute(
            select(Hospital).where(Hospital.hospital_id == hospital_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

        # Authorization check
        if role != RoleEnum.SUPER_ADMIN:
            # Other roles are not allowed to delete hospitals
            raise HTTPException(
                status_code=403,
                detail="Access denied. Insufficient permissions to delete hospital.",
            )
            # Super admin can delete any hospital

        # await UserService.delete_user(db, hospital.admin_id)
        await db.delete(hospital)
        await db.commit()
        return {"message": "Hospital deleted successfully"}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
