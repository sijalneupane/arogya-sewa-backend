from ast import Not
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.file_type_enum import FileTypeEnum
from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.auth.v1.models import Role
from app.modules.file.v1.models import File
from app.modules.file.v1.service import delete_file
from app.modules.hospital.v1.models import Hospital
from app.modules.hospital.v1.schema import FilterHospitaList
from app.modules.user.v1.models import User
from app.modules.user.v1.schema import UserCreate
from app.modules.user.v1.service import create_user


async def add_hospital(
    db: AsyncSession,
    name: str,
    location: str,
    latitude: float,
    longitude: float,
    contact_number: list[str],
    opened_date,
    hospital_license_id: str,
    logo_img_id: str,
    banner_img_id: str,
    admin_details: UserCreate,
) -> Hospital:
    try:
        # Validate hospital license file exists
        license_file = await db.execute(
            select(File).where(File.file_id == hospital_license_id)
        )
        license_file_obj = license_file.scalar_one_or_none()
        if not license_file_obj or license_file_obj.file_type != FileTypeEnum.LICENSE:
            raise HTTPException(
                status_code=404, detail="Hospital license file not found"
            )

        logo_file = await db.execute(select(File).where(File.file_id == logo_img_id))
        logo_file_obj = logo_file.scalar_one_or_none()
        if not logo_file_obj or logo_file_obj.file_type != FileTypeEnum.HOSPITAL_LOGO:
            raise HTTPException(status_code=404, detail="Logo file not found")

        banner_file = await db.execute(
            select(File).where(File.file_id == banner_img_id)
        )
        banner_file_obj = banner_file.scalar_one_or_none()
        if (
            not banner_file_obj
            or banner_file_obj.file_type != FileTypeEnum.HOSPITAL_BANNER
        ):
            raise HTTPException(status_code=404, detail="Banner file not found")
        # Create admin user first
        admin_user = await create_user(
            db=db,
            name=admin_details.name,
            email=admin_details.email,
            password=admin_details.password,
            role=RoleEnum.HOSPITAL_ADMIN,
            phone_number=admin_details.phone_number,
        )

        # Create hospital
        hospital = Hospital(
            hospital_id=StringUtils.randomAlphaNumeric(8),
            name=name,
            location=location,
            latitude=latitude,
            longitude=longitude,
            contact_number=contact_number,
            opened_date=opened_date,
            admin=admin_user,
        )
        db.add(hospital)
        await db.flush()  # Flush to get hospital_id

        # Assign files to hospital
        license_file_obj.hospital_id = hospital.hospital_id
        logo_file_obj.hospital_id = hospital.hospital_id
        banner_file_obj.hospital_id = hospital.hospital_id

        await db.commit()
        await db.refresh(hospital)

        # Ensure the admin and files relationships are loaded
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin), selectinload(Hospital.files))
            .where(Hospital.hospital_id == hospital.hospital_id)
        )
        hospital_with_relations = result.scalar_one()
        return hospital_with_relations
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def get_all_hospitals(
    db: AsyncSession, filters: FilterHospitaList
) -> Tuple[list[Hospital], int]:
    try:
        # 1️⃣ Build base query
        base_stmt = select(Hospital)

        # 2️⃣ Apply filters to base query
        if filters.name:
            base_stmt = base_stmt.where(Hospital.name.ilike(f"%{filters.name}%"))

        if filters.address:
            base_stmt = base_stmt.where(Hospital.location.ilike(f"%{filters.address}%"))

        if filters.opened_date_from:
            base_stmt = base_stmt.where(
                Hospital.opened_date >= filters.opened_date_from
            )

        if filters.opened_date_to:
            base_stmt = base_stmt.where(Hospital.opened_date <= filters.opened_date_to)

        # 3️⃣ Get total count (before pagination)
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar_one()

        # 4️⃣ Apply pagination and eager loading for final query
        # Calculate offset explicitly to ensure it works correctly
        offset_value = (filters.page - 1) * filters.size
        stmt = (
            base_stmt.options(
                selectinload(Hospital.files),
            )
            .offset(offset_value)
            .limit(filters.size)
        )

        result = await db.execute(stmt)
        hospitals = result.scalars().all()

        return (list(hospitals), total_count)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_hospital_by_id(db: AsyncSession, hospital_id: str) -> Hospital:
    try:
        result = await db.execute(
            select(Hospital)
            .join(Hospital.admin)
            .join(User.role)
            .options(
                selectinload(Hospital.files),
                selectinload(Hospital.admin).selectinload(User.role),
                selectinload(Hospital.admin).selectinload(User.files),
            )
            .where(
                Hospital.hospital_id == hospital_id,
                Role.role == RoleEnum.HOSPITAL_ADMIN,
            )
        )

        hospital = result.unique().scalar_one_or_none()

        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

        return hospital

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_hospital_by_admin_id(db: AsyncSession, admin_id: str) -> Hospital:
    """Get a hospital by its admin user ID."""
    try:
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin), selectinload(Hospital.files))
            .where(Hospital.admin_id == admin_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(
                status_code=404, detail="Hospital not found for this admin"
            )
        return hospital
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def update_hospital(
    db: AsyncSession,
    hospital_id: str,
    current_user_id: str,
    role: RoleEnum,
    name: Optional[str] = None,
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    contact_number: Optional[list[str]] = None,
    opened_date=None,
    hospital_license_id: Optional[str] = None,
    logo_img_id: Optional[str] = None,
    banner_img_id: Optional[str] = None,
) -> Hospital:
    """Update hospital details."""
    try:
        # Get the hospital first
        result = await db.execute(
            select(Hospital)
            .options(
                selectinload(Hospital.admin).selectinload(User.role),
                selectinload(Hospital.admin).selectinload(User.files),
                selectinload(Hospital.files),
            )
            .where(Hospital.hospital_id == hospital_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

        old_license_file_id: Optional[str] = None
        old_logo_file_id: Optional[str] = None
        old_banner_file_id: Optional[str] = None
        for file in hospital.files:
            if file.file_type == FileTypeEnum.LICENSE:
                old_license_file_id = file.file_id
            elif file.file_type == FileTypeEnum.HOSPITAL_LOGO:
                old_logo_file_id = file.file_id
            elif file.file_type == FileTypeEnum.HOSPITAL_BANNER:
                old_banner_file_id = file.file_id
        # Authorization check
        if role == RoleEnum.HOSPITAL_ADMIN:
            # Hospital admin can only update their own hospital
            if hospital.admin_id != current_user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. You can only update your own hospital.",
                )
        elif role != RoleEnum.SUPER_ADMIN:
            # Other roles are not allowed to update hospitals
            raise HTTPException(
                status_code=403,
                detail="Access denied. Insufficient permissions to update hospital.",
            )

        file_to_delete: Optional[List[str]] = []
        # Validate and assign hospital license file if provided
        if hospital_license_id is not None:
            license_file = await db.execute(
                select(File).where(File.file_id == hospital_license_id)
            )
            license_file_obj = license_file.scalar_one_or_none()
            if not license_file_obj:
                raise HTTPException(
                    status_code=404, detail="Hospital license file not found"
                )
            # Assign file to this hospital
            file_to_delete.append(old_license_file_id) if old_license_file_id else None
            license_file_obj.hospital_id = hospital.hospital_id

        # Validate and assign logo file if provided
        if logo_img_id is not None:
            logo_file = await db.execute(
                select(File).where(File.file_id == logo_img_id)
            )
            logo_file_obj = logo_file.scalar_one_or_none()
            if not logo_file_obj:
                raise HTTPException(status_code=404, detail="Logo file not found")
            # Assign file to this hospital
            file_to_delete.append(old_logo_file_id) if old_logo_file_id else None
            logo_file_obj.hospital_id = hospital.hospital_id

        # Validate and assign banner file if provided
        if banner_img_id is not None:
            banner_file = await db.execute(
                select(File).where(File.file_id == banner_img_id)
            )
            banner_file_obj = banner_file.scalar_one_or_none()
            if not banner_file_obj:
                raise HTTPException(status_code=404, detail="Banner file not found")
            # Assign file to this hospital
            file_to_delete.append(old_banner_file_id) if old_banner_file_id else None
            banner_file_obj.hospital_id = hospital.hospital_id
        if file_to_delete and len(file_to_delete) > 0:
            await delete_file(db, file_to_delete)

        # Update fields if provided
        if name is not None:
            hospital.name = name
        if location is not None:
            hospital.location = location
        if latitude is not None:
            hospital.latitude = latitude
        if longitude is not None:
            hospital.longitude = longitude
        if contact_number is not None:
            hospital.contact_number = contact_number
        if opened_date is not None:
            hospital.opened_date = opened_date

        await db.commit()
        await db.refresh(hospital)

        # Reload with relationships
        result = await db.execute(
            select(Hospital)
            .options(
                selectinload(Hospital.admin).selectinload(User.role),
                selectinload(Hospital.admin).selectinload(User.files),
                selectinload(Hospital.files),
            )
            .where(Hospital.hospital_id == hospital_id)
        )
        updated_hospital = result.scalar_one()
        return updated_hospital
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def delete_hospital(
    db: AsyncSession, hospital_id: str, role: RoleEnum, current_user_id: str
):
    """Delete a hospital by its ID."""
    try:
        await db.begin()
        # Get the hospital first with files loaded
        result = await db.execute(
            select(Hospital)
            .options(
                selectinload(Hospital.files),
                selectinload(Hospital.admin).selectinload(User.files),
            )
            .where(Hospital.hospital_id == hospital_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

        # Delete associated files if exist
        for file in hospital.files:
            await delete_file(db, file.file_id)

        if hospital.admin and hospital.admin.files:
            file_ids_to_delete = [file.file_id for file in hospital.admin.files]
            await delete_file(db, file_ids_to_delete)
        await db.delete(hospital.admin)
        await db.delete(hospital)
        await db.commit()
        return {"message": "Hospital deleted successfully"}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# using vincenty's formula for distance calculation


async def get_closest_hospital_long_lat_vincenity(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    max_distance_km: float = 20,
):
    """Get hospitals within a certain distance from the given coordinates."""
    from geopy.distance import geodesic

    print("\n-------get_closest_hospital_long_lat-------\n")
    try:
        hospitals = await db.execute(
            select(Hospital).options(
                selectinload(Hospital.admin).selectinload(User.role),
                selectinload(Hospital.files),
            )
        )
        hospitals = hospitals.scalars().all()

        print("\n-------" + str(len(hospitals)) + "-------\n")
        nearby_hospitals = []
        for hosp in hospitals:
            hospital_coords = (hosp.latitude, hosp.longitude)
            user_coords = (latitude, longitude)
            distance = geodesic(hospital_coords, user_coords).km
            if distance <= max_distance_km:
                nearby_hospitals.append((hosp, distance))

        # Sort the list by distance (closest first)
        nearby_hospitals.sort(key=lambda item: item[1])
        print("\n-------" + str(nearby_hospitals) + "-------\n")

        # Return only hospitals, now perfectly ordered from closest to farthest
        return [hosp for hosp, distance in nearby_hospitals]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_closest_hospital_long_lat_haversine(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    max_distance_km: float = 20,
    page: int = 1,
    size: int = 10,
) -> Tuple[list[Hospital], int]:
    """Get hospitals within a certain distance from the given coordinates."""
    from geopy.distance import great_circle

    try:
        # Fetch all hospitals (ideally use spatial database index for performance)
        hospitals, _ = await get_all_hospitals(
            db,
            filters=FilterHospitaList(
                address=None,
                name=None,
                opened_date_from=None,
                opened_date_to=None,
                page=1,
                size=500,
            ),
        )

        nearby_hospitals = []
        for hosp in hospitals:
            hospital_coords = (hosp.latitude, hosp.longitude)
            user_coords = (latitude, longitude)

            # Use great_circle (Haversine formula)
            distance = great_circle(hospital_coords, user_coords).km

            if distance <= max_distance_km:
                nearby_hospitals.append((hosp, distance))

        # Sort by distance (closest first)
        nearby_hospitals.sort(key=lambda item: item[1])

        # Get total count before pagination
        total_count = len(nearby_hospitals)

        # Apply pagination
        offset = (page - 1) * size
        paginated_hospitals = nearby_hospitals[offset : offset + size]

        # Return only hospitals (without distance)
        return ([hosp for hosp, distance in paginated_hospitals], total_count)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# async def get_closest_hospitals(
#     db: AsyncSession,
#     user_id:str,
#     max_distance_km: float = 20,
# ) -> list[Hospital]:
#     """GEt closest hospitals to user's location"""
#     hospitals = await _get_closest_hospital_long_lat(
#         db, latitude, longitude, max_distance_km
#     )
#     return hospitals
