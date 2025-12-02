from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.hospital.v1.models import Hospital
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
