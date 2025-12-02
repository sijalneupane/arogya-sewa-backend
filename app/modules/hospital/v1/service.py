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
    # check duplicates first
    duplicate_hospital = await db.execute(
        select(Hospital).where(Hospital.name == name, Hospital.address == address)
    )
    if duplicate_hospital.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Hospital with the same name and address already exists",
        )

    # create admin user explicitly (no Depends here)
    admin = await create_user(
        db=db,
        email=admin_email,
        password=admin_password,
        name=admin_name,
        role=RoleEnum.HOSPITAL_ADMIN,
    )

    hospital_id = StringUtils.randomAlphaNumeric(8)
    new_hospital = Hospital(
        hospital_id=hospital_id,
        name=name,
        address=address,
        contact_number=contact_number,
        opened_date=opened_date,
        admin=admin,
        # if your Hospital model has a relation/foreign key to admin, set it here, e.g. admin_id=admin.id
    )
    db.add(new_hospital)
    await db.commit()
    await db.refresh(new_hospital)
    return new_hospital
