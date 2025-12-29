from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.core.utils.string_utils import StringUtils
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.doctor.v1.models import Doctor
from app.modules.patient.v1.service import create_patient
from app.modules.user.v1.models import User
from app.modules.user.v1.service import create_user, get_user_by_email


async def signup_patient(
    db: AsyncSession,
    email: str,
    name: str,
    phone_number: str,
    password: str,
    dob: date,
    gender: str,
    blood_group: str,
):
    """Create a user with patient role and corresponding patient record."""
    try:
        # Create user
        user = await create_user(
            db=db,
            email=email,
            name=name,
            phone_number=phone_number,
            password=password,
            role=RoleEnum.PATIENT,
        )

        # Create patient record
        patient = await create_patient(
            db=db,
            user_id=user.id,
            dob=dob,
            gender=gender,
            blood_group=blood_group,
        )

        await db.commit()

        # Re-query user with role relationship loaded
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user.id)
        )
        user_with_role = result.scalar_one()

        return user_with_role

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


async def signup_doctor(
    db: AsyncSession,
    email: str,
    name: str,
    phone_number: str,
    password: str,
    specialization_department: str,
    experience_years: int,
    license_certificate_id: str,
):
    """Create a user with doctor role and corresponding doctor record."""
    try:
        # Create user
        user = await create_user(
            db=db,
            email=email,
            name=name,
            phone_number=phone_number,
            password=password,
            role=RoleEnum.DOCTOR,
        )

        # Create doctor record
        doctor = Doctor(
            doctor_id=StringUtils.randomAlphaNumeric(8),
            user_id=user.id,
            specialization_department=specialization_department,
            experience_years=experience_years,
            license_certificate=license_certificate_id,
            hospital_id=None,  # No hospital assigned initially
        )

        db.add(doctor)
        await db.commit()

        # Re-query user with role relationship loaded
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user.id)
        )
        user_with_role = result.scalar_one()

        return user_with_role

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


async def signup_super_admin(
    db: AsyncSession,
    email: str,
    name: str,
    phone_number: str,
    password: str,
):
    """Create a user with super admin role."""
    try:
        user = await create_user(
            db=db,
            email=email,
            name=name,
            phone_number=phone_number,
            password=password,
            role=RoleEnum.SUPER_ADMIN,
        )

        await db.commit()

        # Re-query user with role relationship loaded
        result = await db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user.id)
        )
        user_with_role = result.scalar_one()

        return user_with_role

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email ")
    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    return user


async def login_user(db: AsyncSession, email: str, password: str):
    try:
        user = await authenticate_user(db, email, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Load user with role and files
        result = await db.execute(
            select(User)
            .options(selectinload(User.role), selectinload(User.files))
            .where(User.id == user.id)
        )
        user_with_details = result.scalar_one()

        payload = JwtPayload(
            sub=user_with_details.id,
            name=user_with_details.name,
            role=user_with_details.role.role,
        )
        # print(
        #     f"Creating JWT with payload: sub={user.id}, name={user.name}, role={user.role.role}"
        # )
        access = create_access_token(payload)
        refresh = create_refresh_token({"sub": user_with_details.id})

        return access, refresh, user_with_details
    except HTTPException as e:
        raise e
