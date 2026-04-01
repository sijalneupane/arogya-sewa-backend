from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db import get_db
from app.modules.auth.v1.schemas import LoginData, LoginResponse
from app.modules.auth.v1.service import (
    login_user,
    signup_doctor,
    signup_patient,
    signup_super_admin,
)
from app.modules.user.v1.schema import (
    DoctorSignupSchema,
    PatientSignupSchema,
    SignupResponse,
    SuperAdminSignupSchema,
    UserResponse,
)
from app.modules.user.v1.schema import UserLogin as LoginSchema

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup/patient", response_model=SignupResponse)
async def signup_patient_route(
    data: PatientSignupSchema, db: AsyncSession = Depends(get_db)
):
    """Register a new patient user with patient details."""
    user = await signup_patient(
        db=db,
        email=data.user.email,
        name=data.user.name,
        phone_number=data.user.phone_number,
        password=data.user.password,
        dob=data.dob,
        gender=data.gender,
        blood_group=data.blood_group,
    )
    return SignupResponse(
        message="Patient registered successfully",
        data=UserResponse.model_validate(user),
    )


# @router.post("/signup/doctor", response_model=SignupResponse)
# async def signup_doctor_route(
#     data: DoctorSignupSchema, db: AsyncSession = Depends(get_db)
# ):
#     """Register a new doctor user with doctor credentials."""
#     user = await signup_doctor(
#         db=db,
#         email=data.user.email,
#         name=data.user.name,
#         phone_number=data.user.phone_number,
#         password=data.user.password,
#         specialization_department=data.specialization_department,
#         experience_years=data.experience_years,
#         license_certificate_id=data.license_certificate_id,
#     )
#     return SignupResponse(
#         message="Doctor registered successfully", data=UserResponse.model_validate(user)
#     )


@router.post("/signup/super-admin", response_model=SignupResponse)
async def signup_super_admin_route(
    data: SuperAdminSignupSchema, db: AsyncSession = Depends(get_db)
):
    """Register a new super admin user. Hospital admin cannot be created via signup."""
    user = await signup_super_admin(
        db=db,
        email=data.email,
        name=data.name,
        phone_number=data.phone_number,
        password=data.password,
    )
    return SignupResponse(
        message="Super admin registered successfully",
        data=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginSchema, db: AsyncSession = Depends(get_db)):
    try:
        access, refresh, user = await login_user(
            db,
            data.email,
            data.password,
            data.fcm_token,
        )

        return LoginResponse(
            data=LoginData(access_token=access, refresh_token=refresh, user=user)
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Internal server error" + e.__str__()
        )
