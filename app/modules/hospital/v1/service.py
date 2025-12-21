from typing import Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules import hospital
from app.modules.hospital.v1.models import Hospital
from app.modules.user.v1 import service as UserService
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
    admin_details: UserCreate,
) -> Hospital:
    try:
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
        await db.commit()
        await db.refresh(hospital)

        # Ensure the admin relationship is loaded
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin))
            .where(Hospital.hospital_id == hospital.hospital_id)
        )
        hospital_with_admin = result.scalar_one()
        return hospital_with_admin
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def get_all_hospitals(db: AsyncSession) -> list[Hospital]:
    """Get all hospitals with their admin details."""
    try:
        result = await db.execute(
            select(Hospital).options(
                selectinload(Hospital.admin).selectinload(User.role)
            )
        )
        hospitals = result.scalars().all()
        return list(hospitals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_hospital_by_id(db: AsyncSession, hospital_id: str) -> Hospital:
    """Get a hospital by its ID with admin details."""
    try:
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin).selectinload(User.role))
            .where(Hospital.hospital_id == hospital_id)
        )
        hospital = result.scalar_one_or_none()
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
            .options(selectinload(Hospital.admin))
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
) -> Hospital:
    """Update hospital details."""
    try:
        # Get the hospital first
        result = await db.execute(
            select(Hospital)
            .options(selectinload(Hospital.admin).selectinload(User.role))
            .where(Hospital.hospital_id == hospital_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

        # Authorization check
        if role == RoleEnum.SUPER_ADMIN:
            # Super admin can update any hospital
            pass
        elif role == RoleEnum.HOSPITAL_ADMIN:
            # Hospital admin can only update their own hospital
            if hospital.admin_id != current_user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. You can only update your own hospital.",
                )
        else:
            # Other roles are not allowed to update hospitals
            raise HTTPException(
                status_code=403,
                detail="Access denied. Insufficient permissions to update hospital.",
            )

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
            .options(selectinload(Hospital.admin).selectinload(User.role))
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
        # Get the hospital first
        result = await db.execute(
            select(Hospital).where(Hospital.hospital_id == hospital_id)
        )
        hospital = result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

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
                selectinload(Hospital.admin).selectinload(User.role)
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
):
    """Get hospitals within a certain distance from the given coordinates."""
    # --- CHANGE: Import great_circle instead of geodesic ---
    from geopy.distance import great_circle

    print("\n-------get_closest_hospital_long_lat-------\n")
    try:
        # NOTE: This part (fetching ALL hospitals) should ideally be optimized using
        # a spatial database index for performance.
        hospitals = await db.execute(
            select(Hospital).options(
                selectinload(Hospital.admin).selectinload(User.role)
            )
        )
        hospitals = hospitals.scalars().all()

        print("\n-------" + str(len(hospitals)) + "-------\n")
        nearby_hospitals = []
        for hosp in hospitals:
            hospital_coords = (hosp.latitude, hosp.longitude)
            user_coords = (latitude, longitude)

            # --- CHANGE: Use great_circle() instead of geodesic() ---
            # great_circle implements the Haversine formula.
            distance = great_circle(hospital_coords, user_coords).km

            if distance <= max_distance_km:
                nearby_hospitals.append((hosp, distance))

        # Sort the list by distance (closest first)
        nearby_hospitals.sort(key=lambda item: item[1])
        print("\n-------" + str(nearby_hospitals) + "-------\n")

        # Return only hospitals, now perfectly ordered from closest to farthest
        return [hosp for hosp, distance in nearby_hospitals]
    except Exception as e:
        # In a production app, it's better to log the exception (e)
        # and raise a more generic error for the user.
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
