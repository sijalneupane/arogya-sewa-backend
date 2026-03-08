import math
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schema.pagination import (
    PaginatedResponse,
    PaginationMeta,
    PaginationQuery,
)
from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.doctor.v1.schema import (
    DoctorCreateSchema,
    DoctorDetailResponseSchema,
    DoctorFilterSchema,
    DoctorPostPatchResponse,
    DoctorResponseSchema,
    DoctorUpdateSchema,
    DoctorWithHospitalResponseSchema,
)
from app.modules.doctor.v1.service import (
    create_doctor,
    delete_doctor,
    get_all_doctors,
    get_doctor_by_id,
    get_doctor_by_user_id,
    get_doctors_by_hospital,
    get_doctors_of_logged_in_hospital_admin,
    update_doctor,
    # upgrade_user_to_doctor,
)

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)


@router.post("", summary="Create a new doctor with user credentials")
async def create_new_doctor(
    data: DoctorCreateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> DoctorPostPatchResponse:
    """Create a new doctor with user account."""
    created_doctor = await create_doctor(
        db=db,
        department_id=data.department_id,
        experience_years=data.experience_years,
        license_certificate=data.license_certificate_id,
        user_name=data.user.name,
        user_email=data.user.email,
        user_password=data.user.password,
        user_phone=data.user.phone_number,
        hospital_admin_id=user.sub,
        bio=data.bio,
    )
    response = DoctorResponseSchema.model_validate(created_doctor)
    return DoctorPostPatchResponse(message="Doctor created successfully", data=response)


@router.get("", summary="Get all doctors")
async def get_doctors(
    filters: DoctorFilterSchema = Depends(),
    pagination: PaginationQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    # _=Depends(authorize),
) -> PaginatedResponse[List[DoctorResponseSchema]]:
    """Get all doctors with their details."""
    doctors, total = await get_all_doctors(
        db=db,
        name=filters.name,
        status=filters.status,
        department_id=filters.department_id,
        page=pagination.page,
        size=pagination.size,
    )
    doctor_responses = [
        DoctorResponseSchema.model_validate(doctor) for doctor in doctors
    ]
    return PaginatedResponse(
        message="Doctors fetched successfully",
        data=doctor_responses,
        paginationMeta=PaginationMeta(
            totalPage=math.ceil(total / pagination.size) if total else 0,
            currentPage=pagination.page,
            pageSize=pagination.size,
            totalRecords=total,
        ),
    )


# @router.post("/upgrade", summary="Upgrade current user to doctor")
# async def upgrade_current_user_to_doctor(
#     data: UserToDoctorUpgradeSchema,
#     db: AsyncSession = Depends(get_db),
#     user: JwtPayload = Depends(get_current_user),
#     # _=Depends(authorize),  # Any authenticated user can upgrade themselves
# ) -> DoctorDetailResponseSchema:
#     """Upgrade the current user to a doctor. This will update user role to DOCTOR and create doctor profile."""
#     doctor = await upgrade_user_to_doctor(
#         db=db,
#         user_id=user.sub,
#         specialization_department=data.specialization_department,
#         experience_years=data.experience_years,
#         license_certificate_id=data.license_certificate_id,
#     )
#     response = DoctorWithHospitalResponseSchema.model_validate(doctor)
#     return DoctorDetailResponseSchema(
#         message="Successfully upgraded to doctor", data=response
#     )


@router.get("/me", summary="Get own doctor profile")
async def get_own_doctor_profile(
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> DoctorDetailResponseSchema:
    """Get the current user's doctor profile."""
    doctor = await get_doctor_by_user_id(db=db, user_id=user.sub)
    response = DoctorWithHospitalResponseSchema.model_validate(doctor)
    return DoctorDetailResponseSchema(data=response)


@router.get("/hospital/my", summary="Get doctors by hospital of current admin")
async def get_hospital_admin_doctors(
    filters: DoctorFilterSchema = Depends(),
    pagination: PaginationQuery = Depends(),
    hospital_admin_id: JwtPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # _=Depends(authorize),
) -> PaginatedResponse[List[DoctorResponseSchema]]:
    """Get all doctors for a specific hospital."""
    doctors, total = await get_doctors_of_logged_in_hospital_admin(
        db=db,
        hospital_admin_id=hospital_admin_id.sub,
        name=filters.name,
        status=filters.status,
        department_id=filters.department_id,
        page=pagination.page,
        size=pagination.size,
    )
    doctor_responses = [
        DoctorResponseSchema.model_validate(doctor) for doctor in doctors
    ]
    return PaginatedResponse(
        message=f"Doctors for hospital admin {hospital_admin_id.sub} fetched successfully",
        data=doctor_responses,
        paginationMeta=PaginationMeta(
            totalPage=math.ceil(total / pagination.size) if total else 0,
            currentPage=pagination.page,
            pageSize=pagination.size,
            totalRecords=total,
        ),
    )


@router.get("/hospital/{hospital_id}", summary="Get doctors by hospital")
async def get_hospital_doctors(
    hospital_id: str,
    filters: DoctorFilterSchema = Depends(),
    pagination: PaginationQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    # _=Depends(authorize),
) -> PaginatedResponse[List[DoctorResponseSchema]]:
    """Get all doctors for a specific hospital."""
    doctors, total = await get_doctors_by_hospital(
        db=db,
        hospital_id=hospital_id,
        name=filters.name,
        status=filters.status,
        department_id=filters.department_id,
        page=pagination.page,
        size=pagination.size,
    )
    doctor_responses = [
        DoctorResponseSchema.model_validate(doctor) for doctor in doctors
    ]
    return PaginatedResponse(
        message=f"Doctors for hospital {hospital_id} fetched successfully",
        data=doctor_responses,
        paginationMeta=PaginationMeta(
            totalPage=math.ceil(total / pagination.size) if total else 0,
            currentPage=pagination.page,
            pageSize=pagination.size,
            totalRecords=total,
        ),
    )


@router.get("/{doctor_id}", summary="Get doctor by ID")
async def get_doctor(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
    # _=Depends(authorize),
) -> DoctorDetailResponseSchema:
    """Get a doctor by their ID."""
    doctor = await get_doctor_by_id(db=db, doctor_id=doctor_id)
    response = DoctorWithHospitalResponseSchema.model_validate(doctor)
    return DoctorDetailResponseSchema(data=response)


@router.patch("/{doctor_id}", summary="Update doctor details")
async def update_doctor_details(
    doctor_id: str,
    data: DoctorUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> DoctorPostPatchResponse:
    """Update doctor details."""
    updated_doctor = await update_doctor(
        db=db,
        doctor_id=doctor_id,
        current_user_id=user.sub,
        role=user.role,
        **data.model_dump(exclude_unset=True),
    )
    response = DoctorResponseSchema.model_validate(updated_doctor)
    return DoctorPostPatchResponse(message="Doctor updated successfully", data=response)


@router.delete("/{doctor_id}", summary="Delete doctor")
async def delete_doctor_by_id(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """Delete a doctor."""
    result = await delete_doctor(
        db=db, doctor_id=doctor_id, current_user_id=user.sub, role=user.role
    )
    return result
