import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.configuration.mailgun_config import get_mailgun_service
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import (
    AuthenticatedUserResponse,
    AuthMessageResponse,
    AuthUserByIdResponse,
    ChangePasswordRequest,
    JwtPayload,
    LoginData,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
    SendPasswordResetOtpRequest,
    VerifyOtpRequest,
)
from app.modules.auth.v1.service import (
    get_authenticated_user,
    login_user,
    refresh_user_tokens,
    reset_user_password,
    send_password_reset_otp,
    signup_patient,
    update_authenticated_user_fcm_token,
    update_user_password,
    verify_otp,
)
from app.modules.email.v1.email_utils import send_patient_signup_email
from app.modules.user.v1.schema import (
    PatientSignupSchema,
    SignupResponse,
    UserResponse,
)
from app.modules.user.v1.schema import UserLogin as LoginSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=SignupResponse)
async def signup_patient_route(
    data: PatientSignupSchema, db: AsyncSession = Depends(get_db)
):
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

    # Send welcome email to patient
    try:
        mailgun_service = get_mailgun_service()
        await send_patient_signup_email(
            service=mailgun_service,
            patient_name=user.name,
            patient_email=user.email,
        )
    except Exception as exc:
        logger.warning(f"Failed to send patient signup email: {exc}")

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


# @router.post("/signup/super-admin", response_model=SignupResponse)
# async def signup_super_admin_route(
#     data: SuperAdminSignupSchema, db: AsyncSession = Depends(get_db)
# ):
#     """Register a new super admin user. Hospital admin cannot be created via signup."""
#     user = await signup_super_admin(
#         db=db,
#         email=data.email,
#         name=data.name,
#         phone_number=data.phone_number,
#         password=data.password,
#     )
#     return SignupResponse(
#         message="Super admin registered successfully",
#         data=UserResponse.model_validate(user),
#     )


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


@router.post("/refresh-token", response_model=RefreshTokenResponse)
async def refresh_token_route(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    return await refresh_user_tokens(db=db, refresh_token=data.refresh_token)


@router.post("/password/forgot/send-otp", response_model=AuthMessageResponse)
async def send_password_reset_otp_route(
    data: SendPasswordResetOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    return await send_password_reset_otp(db=db, email=str(data.email))


@router.post("/password/forgot/verify-otp", response_model=AuthMessageResponse)
async def verify_otp_route(
    data: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    return await verify_otp(db=db, email=str(data.email), otp_code=data.otp_code)


@router.post("/password/forgot/reset", response_model=AuthMessageResponse)
async def reset_password_route(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    return await reset_user_password(
        db=db,
        email=str(data.email),
        password=data.password,
        confirm_password=data.confirm_password,
    )


@router.post("/password/change", response_model=AuthMessageResponse)
async def change_password_route(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: JwtPayload = Depends(get_current_user),
):
    return await update_user_password(
        db=db,
        user_id=current_user.sub,
        old_password=data.old_password,
        new_password=data.new_password,
        confirm_password=data.confirm_password,
    )


@router.get("/me", response_model=AuthUserByIdResponse)
async def get_current_user_route(
    current_user: JwtPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    fcm_token: str | None = Query(
        default=None,
        max_length=255,
        description="Optional FCM token to store for the authenticated user",
    ),
):
    """Get the currently authenticated user's details."""
    if fcm_token is not None:
        user = await update_authenticated_user_fcm_token(
            db=db,
            user_id=current_user.sub,
            role=current_user.role,
            fcm_token=fcm_token,
        )
    else:
        user = await get_authenticated_user(
            db=db,
            user_id=current_user.sub,
            role=current_user.role,
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    return AuthUserByIdResponse(data=AuthenticatedUserResponse.model_validate(user))
