from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils.string_utils import StringUtils
from app.modules.patient.v1.models import Patient
from app.modules.user.v1.models import User


async def create_patient(
    db: AsyncSession,
    user_id: str,
    dob: date,
    gender: str,
    blood_group: str,
) -> Patient:
    """Create a new patient record linked to a user."""
    try:
        patient_id = StringUtils.randomAlphaNumeric(8)
        new_patient = Patient(
            patient_id=patient_id,
            user_id=user_id,
            dob=dob,
            gender=gender,
            blood_group=blood_group,
        )

        db.add(new_patient)
        await db.flush()  # Don't commit here, let caller handle transaction
        await db.refresh(new_patient)

        return new_patient
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create patient: {str(e)}"
        )


async def update_patient(
    db: AsyncSession,
    user_id: str,
    dob: Optional[date] = None,
    gender: Optional[str] = None,
    blood_group: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> Patient:
    """Update patient details and related user information with duplicate checking."""
    try:
        # Get patient by user_id
        result = await db.execute(
            select(Patient)
            .options(
                selectinload(Patient.user).selectinload(User.role),
                selectinload(Patient.user).selectinload(User.files),
            )
            .where(Patient.user_id == user_id)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Check for duplicate email if email is being updated
        if email and email != patient.user.email:
            email_exists = await db.execute(select(User).where(User.email == email))
            if email_exists.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail="Email already in use by another user",
                )

        # Check for duplicate phone_number if phone_number is being updated
        if phone_number and phone_number != patient.user.phone_number:
            phone_exists = await db.execute(
                select(User).where(User.phone_number == phone_number)
            )
            if phone_exists.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail="Phone number already in use by another user",
                )

        # Update patient details
        if dob is not None:
            patient.dob = dob
        if gender is not None:
            patient.gender = gender
        if blood_group is not None:
            patient.blood_group = blood_group

        # Update user details
        if email is not None:
            patient.user.email = email
        if name is not None:
            patient.user.name = name
        if phone_number is not None:
            patient.user.phone_number = phone_number

        await db.commit()
        await db.refresh(patient)

        # Reload with relationships
        result = await db.execute(
            select(Patient)
            .options(
                selectinload(Patient.user).selectinload(User.role),
                selectinload(Patient.user).selectinload(User.files),
            )
            .where(Patient.patient_id == patient.patient_id)
        )
        updated_patient = result.scalar_one()
        return updated_patient

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update patient: {str(e)}"
        )
