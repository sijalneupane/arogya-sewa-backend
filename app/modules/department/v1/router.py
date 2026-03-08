from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import authorize
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.department.v1.schema import (
    DepartmentCreateSchema,
    DepartmentDetailResponseSchema,
    DepartmentFilterQuery,
    DepartmentListResponseSchema,
    DepartmentResponseSchema,
    DepartmentUpdateSchema,
)
from app.modules.department.v1.service import (
    create_department,
    delete_department,
    get_department_by_id,
    get_departments_by_hospital,
    get_departments_for_admin,
    update_department,
)

router = APIRouter(
    prefix="/departments",
    tags=["Departments"],
)


@router.post(
    "",
    summary="Create a new department (hospital admin only)",
    status_code=status.HTTP_201_CREATED,
)
async def create_new_department(
    data: DepartmentCreateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> DepartmentDetailResponseSchema:
    """Create a new department.  Only the admin of the specified hospital may call this."""
    department = await create_department(
        db=db,
        name=data.name,
        description=data.description,
        admin_id=user.sub,
        is_active=data.is_active,
    )
    response = DepartmentResponseSchema.model_validate(department)
    return DepartmentDetailResponseSchema(
        message="Department created successfully", data=response
    )


@router.get(
    "/hospital/{hospital_id}",
    summary="Get all departments for a hospital (public)",
)
async def list_departments_for_hospital(
    hospital_id: str,
    filters: DepartmentFilterQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> DepartmentListResponseSchema:
    """Return a searchable list of departments belonging to a hospital."""
    departments = await get_departments_by_hospital(
        db=db, hospital_id=hospital_id, filters=filters
    )
    department_responses = [
        DepartmentResponseSchema.model_validate(d) for d in departments
    ]
    return DepartmentListResponseSchema(data=department_responses)


@router.get(
    "/my",
    summary="Get departments of the logged-in hospital admin's hospital",
)
async def list_my_hospital_departments(
    filters: DepartmentFilterQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> DepartmentListResponseSchema:
    """Return all departments for the hospital managed by the currently logged-in hospital admin."""
    departments = await get_departments_for_admin(
        db=db, admin_id=user.sub, filters=filters
    )
    department_responses = [
        DepartmentResponseSchema.model_validate(d) for d in departments
    ]
    return DepartmentListResponseSchema(
        message="Departments for your hospital fetched successfully",
        data=department_responses,
    )


@router.get("/{department_id}", summary="Get a department by ID (public)")
async def get_department(
    department_id: str,
    db: AsyncSession = Depends(get_db),
) -> DepartmentDetailResponseSchema:
    """Return a single department by its ID."""
    department = await get_department_by_id(db=db, department_id=department_id)
    response = DepartmentResponseSchema.model_validate(department)
    return DepartmentDetailResponseSchema(data=response)


@router.patch("/{department_id}", summary="Update a department (hospital admin only)")
async def update_department_endpoint(
    department_id: str,
    data: DepartmentUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
) -> DepartmentDetailResponseSchema:
    """Update an existing department.  Only the owning hospital admin may call this."""
    department = await update_department(
        db=db,
        department_id=department_id,
        admin_id=user.sub,
        name=data.name,
        description=data.description,
        is_active=data.is_active,
    )
    response = DepartmentResponseSchema.model_validate(department)
    return DepartmentDetailResponseSchema(
        message="Department updated successfully", data=response
    )


@router.delete(
    "/{department_id}",
    summary="Delete a department (hospital admin only)",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_department_endpoint(
    department_id: str,
    db: AsyncSession = Depends(get_db),
    user: JwtPayload = Depends(get_current_user),
    _=Depends(authorize),
):
    """Delete a department.  Only the owning hospital admin may call this."""
    await delete_department(
        db=db,
        department_id=department_id,
        admin_id=user.sub,
    )
