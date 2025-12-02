from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.hospital.v1.schema import HospitalCreateSchema, HospitalResponseSchema
from app.modules.hospital.v1.service import add_hospital

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
