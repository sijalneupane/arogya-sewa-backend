from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.string_utils import StringUtils
from app.modules.department.v1.models import Department
from app.modules.department.v1.schema import DepartmentFilterQuery
from app.modules.hospital.v1.models import Hospital


async def _get_hospital_for_admin(db: AsyncSession, admin_id: str) -> Hospital:
    """Verify the authenticated user is admin of a hospital and return it."""
    result = await db.execute(select(Hospital).where(Hospital.admin_id == admin_id))
    hospital = result.scalar_one_or_none()
    if not hospital:
        raise HTTPException(
            status_code=403,
            detail="You are not an admin of any hospital",
        )
    return hospital


async def _get_department_owned_by_admin(
    db: AsyncSession, department_id: str, admin_id: str
) -> Department:
    """Fetch a department and verify it belongs to the requesting hospital admin."""
    result = await db.execute(
        select(Department)
        .join(Hospital, Hospital.hospital_id == Department.hospital_id)
        .where(Department.department_id == department_id)
        .where(Hospital.admin_id == admin_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found or you do not have permission to modify it",
        )
    return department


async def create_department(
    db: AsyncSession,
    name: str,
    description: str,
    admin_id: str,
    is_active: bool = True,
) -> Department:
    """Create a new department. Only the hospital admin may create for their hospital."""
    try:
        # Derive hospital from the logged-in admin
        hospital = await _get_hospital_for_admin(db, admin_id)

        # Check for duplicate department name within the same hospital
        duplicate_result = await db.execute(
            select(Department).where(
                Department.hospital_id == hospital.hospital_id,
                Department.name.ilike(name),
            )
        )
        if duplicate_result.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"A department named '{name}' already exists in this hospital",
            )

        department = Department(
            department_id="DE_" + StringUtils.randomAlphaNumeric(7),
            name=name,
            description=description,
            is_active=is_active,
            hospital_id=hospital.hospital_id,
        )
        db.add(department)
        await db.commit()
        await db.refresh(department)
        return department

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def get_departments_by_hospital(
    db: AsyncSession,
    hospital_id: str,
    filters: DepartmentFilterQuery,
) -> List[Department]:
    """Get all departments for a hospital, with optional name search."""
    # Check hospital exists
    hospital_result = await db.execute(
        select(Hospital).where(Hospital.hospital_id == hospital_id)
    )
    if not hospital_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Hospital not found")

    stmt = select(Department).where(Department.hospital_id == hospital_id)

    if filters.name:
        stmt = stmt.where(Department.name.ilike(f"%{filters.name}%"))

    stmt = stmt.order_by(Department.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_departments_for_admin(
    db: AsyncSession,
    admin_id: str,
    filters: DepartmentFilterQuery,
) -> List[Department]:
    """Get all departments belonging to the logged-in hospital admin's hospital."""
    hospital = await _get_hospital_for_admin(db, admin_id)
    return await get_departments_by_hospital(
        db=db, hospital_id=hospital.hospital_id, filters=filters
    )


async def get_department_by_id(db: AsyncSession, department_id: str) -> Department:
    """Get a single department by its ID."""
    result = await db.execute(
        select(Department).where(Department.department_id == department_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department


async def update_department(
    db: AsyncSession,
    department_id: str,
    admin_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Department:
    """Update a department. Only the owning hospital admin may update."""
    try:
        department = await _get_department_owned_by_admin(db, department_id, admin_id)

        if name is not None:
            department.name = name
        if description is not None:
            department.description = description
        if is_active is not None:
            department.is_active = is_active

        await db.commit()
        await db.refresh(department)
        return department

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def delete_department(
    db: AsyncSession,
    department_id: str,
    admin_id: str,
) -> None:
    """Delete a department. Only the owning hospital admin may delete."""
    try:
        department = await _get_department_owned_by_admin(db, department_id, admin_id)

        await db.delete(department)
        await db.commit()

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
