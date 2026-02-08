from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schema import role
from app.common.schema.pagination import PaginatedResponse, PaginationMeta
from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.hospital.v1.schema import (
    AdminHospitalDetailResponseSchema,
    AdminHospitalResponseSchema,
    HospitalCreateSchema,
    HospitalDetailResponseSchema,
    FilterHospitaList,
    HospitalListResponseSchema,
    HospitalResponseSchema,
    HospitalUpdateSchema,
)
from app.modules.hospital.v1.service import (
    add_hospital,
    get_all_hospitals,
    get_closest_hospital_long_lat_haversine,
    get_closest_hospital_long_lat_vincenity,
    get_hospital_by_admin_id,
    get_hospital_by_id,
    update_hospital,
)

router = APIRouter(
    prefix="/hospital",
    tags=["Hospitals"],
)


@router.post("", summary="Create a new hospital with admin credentials")
async def create_hospital(
    data: HospitalCreateSchema,
    db: AsyncSession = Depends(get_db),
    user=Depends(
        get_current_user,
    ),
    _=Depends(authorize),
):
    created_hospital = await add_hospital(
        admin_details=data.admin_details,
        contact_number=data.contact_number,
        db=db,
        name=data.name,
        location=data.location,
        latitude=data.latitude,
        longitude=data.longitude,
        opened_date=data.opened_date,
        hospital_license_id=data.hospital_license_id,
        logo_img_id=data.logo_img_id,
        banner_img_id=data.banner_img_id,
    )
    response = HospitalResponseSchema.model_validate(created_hospital)
    return {"message": "Hospital created successfully", "data": response}


@router.get("", summary="Get all hospitals")
async def get_hospitals(
    db: AsyncSession = Depends(get_db),
    filters: FilterHospitaList = Depends(),
    # _=Depends(authorize),
) -> PaginatedResponse[list[HospitalResponseSchema]]:
    hospitals, total = await get_all_hospitals(db=db, filters=filters)
    hospital_responses = [
        HospitalResponseSchema.model_validate(hospital) for hospital in hospitals
    ]

    total_pages = (total + filters.size - 1) // filters.size if total > 0 else 0

    return PaginatedResponse(
        message="Hospitals fetched successfully",
        data=hospital_responses,
        paginationMeta=PaginationMeta(
            totalPage=total_pages,
            currentPage=filters.page,
            pageSize=filters.size,
            totalRecords=total,
        ),
    )


@router.get("/my", summary="Get own hospital (for hospital admin)")
async def get_own_hospital(
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> AdminHospitalDetailResponseSchema:
    hospital = await get_hospital_by_admin_id(db=db, admin_id=user.sub)
    response = AdminHospitalResponseSchema.model_validate(hospital)
    return AdminHospitalDetailResponseSchema(data=response)


@router.get("/nearest", summary="Get closest hospitals to user's location")
async def get_closest_hospitals(
    latitude: float,
    longitude: float,
    max_distance_km: float = 20,
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db),
    # _=Depends(authorize),
) -> PaginatedResponse[list[HospitalResponseSchema]]:
    hospitals, total = await get_closest_hospital_long_lat_haversine(
        db, latitude, longitude, max_distance_km, page, size
    )
    hospital_responses = [
        HospitalResponseSchema.model_validate(hospital) for hospital in hospitals
    ]

    total_pages = (total + size - 1) // size if total > 0 else 0

    return PaginatedResponse(
        message="Nearest hospitals fetched successfully",
        data=hospital_responses,
        paginationMeta=PaginationMeta(
            totalPage=total_pages, currentPage=page, pageSize=size, totalRecords=total
        ),
    )


@router.get("/{hospital_id}", summary="Get hospital by ID")
async def get_hospital(
    hospital_id: str,
    db: AsyncSession = Depends(get_db),
) -> HospitalDetailResponseSchema:
    hospital = await get_hospital_by_id(db=db, hospital_id=hospital_id)
    response = HospitalResponseSchema.model_validate(hospital)
    return HospitalDetailResponseSchema(data=response)


@router.patch("/{hospital_id}", summary="Update hospital details")
async def update_hospital_details(
    hospital_id: str,
    data: HospitalUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> HospitalDetailResponseSchema:
    updated_hospital = await update_hospital(
        db=db,
        hospital_id=hospital_id,
        current_user_id=user.sub,
        role=user.role,
        **data.model_dump(exclude_unset=True),
    )
    response = HospitalResponseSchema.model_validate(updated_hospital)
    return HospitalDetailResponseSchema(
        message="Hospital updated successfully", data=response
    )


@router.delete("/{hospital_id}", summary="Delete a hospital (Not implemented)")
async def delete_hospital(
    hospital_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
):
    """Delete a hospital by its ID. (Functionality not implemented yet)"""
    # Implementation would go here
    return {"message": "Delete hospital functionality is not implemented yet."}
