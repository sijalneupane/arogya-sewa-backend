from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schema import role
from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.hospital.v1.schema import (
    HospitalCreateSchema,
    HospitalDetailResponseSchema,
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
    created_hospital = await add_hospital(**data.model_dump(), db=db)
    response = HospitalResponseSchema.model_validate(created_hospital)
    return {"message": "Hospital created successfully", "data": response}


@router.get("", summary="Get all hospitals")
async def get_hospitals(
    db: AsyncSession = Depends(get_db),
    # _=Depends(authorize),
) -> HospitalListResponseSchema:
    hospitals = await get_all_hospitals(db=db)
    hospital_responses = [
        HospitalResponseSchema.model_validate(hospital) for hospital in hospitals
    ]
    return HospitalListResponseSchema(data=hospital_responses)


@router.get("/my", summary="Get own hospital (for hospital admin)")
async def get_own_hospital(
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    # _=Depends(authorize),
) -> HospitalDetailResponseSchema:
    hospital = await get_hospital_by_admin_id(db=db, admin_id=user.sub)
    response = HospitalResponseSchema.model_validate(hospital)
    return HospitalDetailResponseSchema(data=response)


@router.get("/nearest", summary="Get closest hospitals to user's location")
async def get_closest_hospitals(
    latitude: float,
    longitude: float,
    max_distance_km: float = 20,
    db: AsyncSession = Depends(get_db),
    # _=Depends(authorize),
) -> HospitalListResponseSchema:
    hospitals = await get_closest_hospital_long_lat_haversine(
        db, latitude, longitude, max_distance_km
    )
    if not hospitals:
        return HospitalListResponseSchema(data=[])
    hospital_responses = [
        HospitalResponseSchema.model_validate(hospital) for hospital in hospitals
    ]
    return HospitalListResponseSchema(data=hospital_responses)


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
