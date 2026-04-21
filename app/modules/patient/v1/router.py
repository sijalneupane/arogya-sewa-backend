from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.patient.v1.schema import (
    PatientUpdate,
    PatientUpdateResponse,
    PatientResponse,
)
from app.modules.patient.v1.service import update_patient
from app.common.enums.role_enum import RoleEnum

router = APIRouter(
    prefix="/patient",
    tags=["Patient Profile"],
)


@router.patch(
    "/profile/update/me",
    response_model=PatientUpdateResponse,
    summary="Update patient profile",
)
async def update_patient_profile(
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """
    Update logged-in patient's profile details.

    Only PATIENT role users can update their own profile.

    Updatable fields:
    - Patient: dob, gender, blood_group
    - User: email, name, phone_number

    Checks for duplicate email and phone_number across all users.
    """
    # # Verify user has PATIENT role
    # if current_user.role != RoleEnum.PATIENT:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access denied. Only patients can update their profile.",
    #     )

    # Extract user fields if provided
    user_data = data.user.model_dump(exclude_unset=True) if data.user else {}

    # Update patient
    updated_patient = await update_patient(
        db=db,
        user_id=current_user.sub,
        dob=data.dob,
        gender=data.gender,
        blood_group=data.blood_group,
        **user_data,
    )

    patient_response = PatientResponse.model_validate(updated_patient)
    return PatientUpdateResponse(
        message="Patient profile updated successfully",
        data=patient_response,
    )
