from datetime import date, datetime, timedelta, timezone
import secrets

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.configuration.mailgun_config import get_mailgun_service
from app.core.security import (
    create_access_token,
    create_refresh_token,
    pwd_context,
    verify_password,
)
from app.core.utils.string_utils import StringUtils
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.doctor.v1.models import Doctor
from app.modules.email.v1.email_utils import send_password_reset_otp_email
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


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
    fcm_token: str | None = None,
):
    try:
        user = await authenticate_user(db, email, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if fcm_token and fcm_token != user.fcm_token:
            user.fcm_token = fcm_token
            await db.commit()
            await db.refresh(user)

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


def _generate_otp_code(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


async def send_password_reset_otp(db: AsyncSession, email: str):
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Email is not registered")

    otp_code = _generate_otp_code(6)
    otp_expiry_time = datetime.now(timezone.utc) + timedelta(minutes=2)

    try:
        mailgun_service = get_mailgun_service()
        await send_password_reset_otp_email(
            service=mailgun_service,
            recipient_email=email,
            otp_code=otp_code,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error sending OTP: {exc}")

    user.otp_code = otp_code
    user.otp_expiry_time = otp_expiry_time
    user.otp_verified = False
    await db.commit()

    return {
        "message": "Password reset OTP sent successfully, please check your email for the OTP.",
    }


async def verify_otp(db: AsyncSession, email: str, otp_code: str):
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.otp_code or not user.otp_expiry_time:
        if user.otp_verified:
            raise HTTPException(
                status_code=400,
                detail="Please request a new OTP first as the old OTP was already verified",
            )
        raise HTTPException(
            status_code=400,
            detail=f"OTP has not been requested for {email} yet",
        )

    if user.otp_code != otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    now = datetime.now(timezone.utc)
    if now > user.otp_expiry_time:
        raise HTTPException(status_code=400, detail="OTP expired")

    user.otp_code = None
    user.otp_expiry_time = None
    user.otp_verified = True
    await db.commit()

    return {
        "message": "OTP verified successfully. Proceed with password reset.",
    }


async def reset_user_password(
    db: AsyncSession,
    email: str,
    password: str,
    confirm_password: str,
):
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.otp_verified:
        raise HTTPException(status_code=400, detail="OTP not verified")

    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user.password = pwd_context.hash(password)
    user.otp_verified = False
    user.otp_code = None
    user.otp_expiry_time = None
    await db.commit()

    return {"message": "Password updated successfully"}


async def update_user_password(
    db: AsyncSession,
    user_id: str,
    old_password: str,
    new_password: str,
    confirm_password: str,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(old_password, user.password):
        raise HTTPException(status_code=401, detail="Invalid old password")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user.password = pwd_context.hash(new_password)
    await db.commit()

    return {"message": "Password updated successfully"}
