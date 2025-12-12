from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.string_utils import StringUtils
from app.modules.patient.v1.models import Patient


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
