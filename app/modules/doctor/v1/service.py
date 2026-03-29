from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.doctor_status_enum import DoctorStatusEnum
from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.availability.v1.models import Availability
from app.modules.doctor.v1.models import Doctor
from app.modules.doctor.v1.schema import DoctorUserUpdateSchema
from app.modules.file.v1.models import File
from app.modules.file.v1.service import delete_file
from app.modules.hospital.v1.models import Hospital
from app.modules.user.v1.models import User
from app.modules.user.v1.service import create_user


async def get_upcoming_availability_by_doctor_ids(
    db: AsyncSession, doctor_ids: List[str], free_upcoming_only: bool = False
) -> Dict[str, Availability]:
    """Return each doctor's nearest upcoming availability keyed by doctor_id."""
    if not doctor_ids:
        return {}

    now = datetime.now(timezone.utc)
    query = select(Availability).where(
        Availability.doctor_id.in_(doctor_ids),
        Availability.start_date_time >= now,
    )
    if free_upcoming_only:
        query = query.where(Availability.is_booked.is_(False))

    result = await db.execute(
        query.order_by(Availability.doctor_id, Availability.start_date_time)
    )

    nearest_by_doctor: Dict[str, Availability] = {}
    for availability in result.scalars().all():
        if availability.doctor_id not in nearest_by_doctor:
            nearest_by_doctor[availability.doctor_id] = availability

    return nearest_by_doctor


async def create_doctor(
    db: AsyncSession,
    department_id: Optional[str],
    experience: str,
    license_certificate: str,
    user_name: str,
    user_email: str,
    user_password: str,
    user_phone: str,
    status: DoctorStatusEnum,
    hospital_admin_id: Optional[str] = None,
    bio: Optional[str] = None,
    profile_img_id: Optional[str] = None,
) -> Doctor:
    """Create a new doctor with an associated user account."""
    try:
        async with db.begin_nested():
            # Verify that the hospital_admin_id corresponds to the admin of the hospital
            hospital_result = await db.execute(
                select(Hospital).where(Hospital.admin_id == hospital_admin_id)
            )
            hospital = hospital_result.scalar_one_or_none()

            if not hospital:
                raise HTTPException(
                    status_code=404,
                    detail=f"Hospital not found for the provided hospital_admin_id {hospital_admin_id}",
                )

            # Validate department if provided
            if department_id:
                from app.modules.department.v1.models import Department

                dept_result = await db.execute(
                    select(Department).where(
                        Department.department_id == department_id,
                        Department.hospital_id == hospital.hospital_id,
                    )
                )
                if not dept_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=404,
                        detail="Department not found in this hospital",
                    )

            license_file = await db.execute(
                select(File).where(File.file_id == license_certificate)
            )
            license_file_obj = license_file.scalar_one_or_none()
            if not license_file_obj:
                raise HTTPException(
                    status_code=404, detail="License certificate file not found"
                )

            # Create user account for the doctor (has its own nested savepoint)
            doctor_user = await create_user(
                db=db,
                name=user_name,
                email=user_email,
                password=user_password,
                phone_number=user_phone,
                role=RoleEnum.DOCTOR,
                profile_img_id=profile_img_id,
            )

            # Create doctor record
            doctor = Doctor(
                doctor_id=StringUtils.randomAlphaNumeric(8),
                experience=experience,
                license_certificate=license_file_obj,
                user_id=doctor_user.id,
                hospital_id=hospital.hospital_id if hospital else None,
                department_id=department_id,
                bio=bio,
                status=status,
            )
            db.add(doctor)
            await db.flush()

        # Savepoint released — commit the full transaction atomically
        await db.commit()

        # Return doctor with relationships loaded
        result = await db.execute(
            select(Doctor)
            .join(Doctor.user)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.department),
            )
            .where(Doctor.doctor_id == doctor.doctor_id)
        )
        return result.scalar_one()

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise


# async def upgrade_user_to_doctor(
#     db: AsyncSession,
#     user_id: str,
#     specialization_department: str,
#     experience_years: int,
#     license_certificate_id: str,
# ) -> Doctor:
#     """Upgrade an existing user to doctor role. Both user role update and doctor creation must succeed."""
#     try:
#         # Start transaction explicitly
#         async with db.begin():
#             # First, verify user exists and is eligible for upgrade
#             result = await db.execute(
#                 select(User).options(selectinload(User.role)).where(User.id == user_id)
#             )
#             user = result.scalar_one_or_none()
#             if not user:
#                 raise HTTPException(status_code=404, detail="User not found")

#             # Check if user already has a doctor profile
#             doctor_check = await db.execute(
#                 select(Doctor).where(Doctor.user_id == user_id)
#             )
#             existing_doctor = doctor_check.scalar_one_or_none()
#             if existing_doctor:
#                 raise HTTPException(
#                     status_code=400, detail="User already has a doctor profile"
#                 )

#             # Check if user role is eligible for upgrade (PATIENT or USER)
#             if user.role.role not in [RoleEnum.PATIENT]:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Cannot upgrade user with role {user.role.role} to doctor. Only patients can be upgraded.",
#                 )
#             license_file = await db.execute(
#                 select(File).where(File.file_id == license_certificate_id)
#             )
#             license_file_obj = license_file.scalar_one_or_none()
#             if not license_file_obj:
#                 raise HTTPException(
#                     status_code=404, detail="License certificate file not found"
#                 )
#             # Update user role to DOCTOR (this will auto-rollback if doctor creation fails)
#             updated_user = await update_user_role(db, user_id, RoleEnum.DOCTOR)

#             # Create doctor record (hospital_id is None as specified)
#             doctor = Doctor(
#                 doctor_id=StringUtils.randomAlphaNumeric(8),
#                 specialization_department=specialization_department,
#                 experience_years=experience_years,
#                 license_certificate=license_file_obj,
#                 user=updated_user,
#                 hospital_id=None,  # Explicitly set to None for user upgrades
#             )

#             db.add(doctor)
#             await db.flush()  # Ensure doctor is created before returning

#             # Return doctor with relationships loaded
#             result = await db.execute(
#                 select(Doctor)
#                 .options(
#                     selectinload(Doctor.user).selectinload(User.role),
#                     selectinload(Doctor.hospital),
#                 )
#                 .where(Doctor.doctor_id == doctor.doctor_id)
#             )
#             return result.scalar_one()

#     except HTTPException:
#         # HTTPExceptions are already properly formatted
#         raise
#     except Exception as e:
#         # Any other exception should rollback the transaction automatically
#         raise HTTPException(
#             status_code=500, detail=f"Failed to upgrade user to doctor: {str(e)}"
#         )


async def get_all_doctors(
    db: AsyncSession,
    name: Optional[str] = None,
    status: Optional[DoctorStatusEnum] = None,
    department_id: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> Tuple[List[Doctor], int]:
    """Get all doctors with their user and hospital details, with optional filters and pagination."""
    try:
        base_query = (
            select(Doctor)
            .join(Doctor.user)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital),
                selectinload(Doctor.department),
            )
        )
        if name:
            base_query = base_query.where(User.name.ilike(f"%{name}%"))
        if status:
            base_query = base_query.where(Doctor.status == status)
        if department_id:
            base_query = base_query.where(Doctor.department_id == department_id)

        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        result = await db.execute(base_query.offset((page - 1) * size).limit(size))
        return list(result.scalars().all()), total
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_doctor_by_id(db: AsyncSession, doctor_id: str) -> Doctor:
    """Get a doctor by their ID with all relationships."""
    try:
        result = await db.execute(
            select(Doctor)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital).selectinload(Hospital.files),
                selectinload(Doctor.department),
            )
            .where(Doctor.doctor_id == doctor_id)
        )
        doctor = result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return doctor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_doctor_by_user_id(db: AsyncSession, user_id: str) -> Doctor:
    """Get a doctor by their user ID."""
    try:
        result = await db.execute(
            select(Doctor)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital).selectinload(Hospital.files),
                selectinload(Doctor.department),
            )
            .where(
                Doctor.user_id == user_id,
            )
        )

        doctor = result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="Doctor profile not found for this user ",
            )
        return doctor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_doctors_by_hospital(
    db: AsyncSession,
    hospital_id: str,
    name: Optional[str] = None,
    status: Optional[DoctorStatusEnum] = None,
    department_id: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> Tuple[List[Doctor], int]:
    """Get all doctors for a specific hospital, with optional filters and pagination."""
    try:
        # Verify hospital exists
        hospital_result = await db.execute(
            select(Hospital).where(Hospital.hospital_id == hospital_id)
        )
        hospital = hospital_result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

        base_query = (
            select(Doctor)
            .join(Doctor.user)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital),
                selectinload(Doctor.department),
            )
            .where(Doctor.hospital_id == hospital_id)
        )
        if name:
            base_query = base_query.where(User.name.ilike(f"%{name}%"))
        if status:
            base_query = base_query.where(Doctor.status == status)
        if department_id:
            base_query = base_query.where(Doctor.department_id == department_id)

        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        result = await db.execute(base_query.offset((page - 1) * size).limit(size))
        return list(result.scalars().all()), total
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_doctors_of_logged_in_hospital_admin(
    db: AsyncSession,
    hospital_admin_id: str,
    name: Optional[str] = None,
    status: Optional[DoctorStatusEnum] = None,
    department_id: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> Tuple[List[Doctor], int]:
    """Get all doctors for the logged-in hospital admin's hospital, with optional filters and pagination."""
    try:
        hospital_of_admin_result = await db.execute(
            select(Hospital).where(Hospital.admin_id == hospital_admin_id)
        )
        hospital_of_admin = hospital_of_admin_result.scalar_one_or_none()
        if not hospital_of_admin:
            raise HTTPException(
                status_code=404,
                detail="Hospital not found for the logged-in hospital admin",
            )

        base_query = (
            select(Doctor)
            .join(Doctor.user)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital),
                selectinload(Doctor.department),
            )
            .where(Doctor.hospital_id == hospital_of_admin.hospital_id)
        )
        if name:
            base_query = base_query.where(User.name.ilike(f"%{name}%"))
        if status:
            base_query = base_query.where(Doctor.status == status)
        if department_id:
            base_query = base_query.where(Doctor.department_id == department_id)

        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        result = await db.execute(base_query.offset((page - 1) * size).limit(size))
        return list(result.scalars().all()), total
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def update_doctor(
    db: AsyncSession,
    doctor_id: str,
    current_user_id: str,
    role: RoleEnum,
    experience: Optional[str] = None,
    license_certificate_id: Optional[str] = None,
    department_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    status: Optional[DoctorStatusEnum] = None,
    bio: Optional[str] = None,
    user: Optional[DoctorUserUpdateSchema] = None,
) -> Doctor:
    """Update doctor details."""
    try:
        # Get the doctor first
        result = await db.execute(
            select(Doctor)
            .options(
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital),
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.department),
            )
            .where(Doctor.doctor_id == doctor_id)
        )
        doctor = result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # Authorization check
        if role == RoleEnum.SUPER_ADMIN:
            # Super admin can update any doctor
            pass
        elif role == RoleEnum.HOSPITAL_ADMIN:
            # Hospital admin can update doctors in their hospital
            if not doctor.hospital_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. Doctor is not associated with any hospital.",
                )
            # Get admin's hospital
            admin_hospital_result = await db.execute(
                select(Hospital).where(Hospital.admin_id == current_user_id)
            )
            admin_hospital = admin_hospital_result.scalar_one_or_none()
            if not admin_hospital or admin_hospital.hospital_id != doctor.hospital_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. You can only update doctors in your hospital.",
                )
        elif role == RoleEnum.DOCTOR:
            # Doctor can only update their own profile
            if doctor.user_id != current_user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. You can only update your own profile.",
                )
        else:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Insufficient permissions to update doctor.",
            )

        # Validate hospital if being changed
        if hospital_id is not None and hospital_id != doctor.hospital_id:
            if hospital_id:  # If assigning to a hospital
                hospital_result = await db.execute(
                    select(Hospital).where(Hospital.hospital_id == hospital_id)
                )
                hospital = hospital_result.scalar_one_or_none()
                if not hospital:
                    raise HTTPException(status_code=404, detail="Hospital not found")

        # Update fields if provided
        if experience is not None:
            doctor.experience = experience
        if department_id is not None:
            from app.modules.department.v1.models import Department

            dept_result = await db.execute(
                select(Department).where(
                    Department.department_id == department_id,
                    Department.hospital_id == doctor.hospital_id,
                )
            )
            if not dept_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=404,
                    detail="Department not found in this doctor's hospital",
                )
            doctor.department_id = department_id
        if license_certificate_id is not None:
            license_file = await db.execute(
                select(File).where(File.file_id == license_certificate_id)
            )
            license_file_obj = license_file.scalar_one_or_none()
            if not license_file_obj:
                raise HTTPException(
                    status_code=404, detail="License certificate file not found"
                )
            doctor.license_certificate = license_file_obj
        if hospital_id is not None:
            doctor.hospital_id = hospital_id if hospital_id else None
        if status is not None:
            doctor.status = status
        if bio is not None:
            doctor.bio = bio

        # Update user fields if provided
        if user:
            from app.core.security import pwd_context

            if user.name is not None:
                doctor.user.name = user.name
            if user.email is not None:
                new_email = user.email
                if new_email != doctor.user.email:
                    email_check = await db.execute(
                        select(User).where(User.email == new_email)
                    )
                    if email_check.scalar_one_or_none():
                        raise HTTPException(
                            status_code=400, detail="Email is already registered"
                        )
                    doctor.user.email = new_email
            if user.phone_number is not None:
                doctor.user.phone_number = user.phone_number
            if user.password is not None:
                doctor.user.password = pwd_context.hash(user.password)
            if user.profile_image_id is not None:
                file_result = await db.execute(
                    select(File)
                    .options(selectinload(File.user))
                    .where(File.file_id == user.profile_image_id)
                )
                profile_file = file_result.scalar_one_or_none()
                if not profile_file:
                    raise HTTPException(
                        status_code=400, detail="Invalid profile image ID"
                    )
                from app.common.enums.file_type_enum import FileTypeEnum

                if profile_file.file_type not in (
                    FileTypeEnum.OTHER,
                    FileTypeEnum.PROFILE,
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="File must be of type OTHER or PROFILE for profile image",
                    )
                profile_file.user_id = doctor.user.id
                profile_file.file_type = FileTypeEnum.PROFILE

        await db.commit()
        await db.refresh(doctor)

        # Reload with relationships
        result = await db.execute(
            select(Doctor)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.department),
                # selectinload(Doctor.hospital),
            )
            .where(Doctor.doctor_id == doctor_id)
        )
        return result.scalar_one()

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def delete_doctor(
    db: AsyncSession, doctor_id: str, current_user_id: str, role: RoleEnum
):
    """Delete a doctor."""
    try:
        # Get the doctor first
        result = await db.execute(
            select(Doctor)
            .options(
                selectinload(Doctor.user), selectinload(Doctor.license_certificate)
            )
            .where(Doctor.doctor_id == doctor_id)
        )
        doctor = result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # Authorization check
        if role == RoleEnum.SUPER_ADMIN:
            # Super admin can delete any doctor
            pass
        elif role != RoleEnum.HOSPITAL_ADMIN:
            # Hospital admin can delete doctors in their hospital
            # if not doctor.hospital_id:
            #     raise HTTPException(
            #         status_code=403,
            #         detail="Access denied. Doctor is not associated with any hospital.",
            #     )
            # Get admin's hospital
            # admin_hospital_result = await db.execute(
            #     select(Hospital).where(Hospital.admin_id == current_user_id)
            # )
            # admin_hospital = admin_hospital_result.scalar_one_or_none()
            # if not admin_hospital or admin_hospital.hospital_id != doctor.hospital_id:
            #     raise HTTPException(
            #         status_code=403,
            #         detail="Access denied. You can only delete doctors in your hospital.",
            #     )
            # else:
            raise HTTPException(
                status_code=403,
                detail="Access denied. Insufficient permissions to delete doctor.",
            )

        await db.delete(doctor)
        if doctor.license_certificate:
            await delete_file(db, [doctor.license_certificate.file_id])
        await db.delete(
            doctor.user
        )  # Also delete associated user account, call the funitons of user service later
        await db.commit()
        return {"message": "Doctor deleted successfully"}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
