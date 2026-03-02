from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.doctor_status_enum import DoctorStatusEnum
from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.modules.doctor.v1.models import Doctor
from app.modules.file.v1.models import File
from app.modules.file.v1.service import delete_file
from app.modules.hospital.v1.models import Hospital
from app.modules.user.v1.models import User
from app.modules.user.v1.service import create_user


async def create_doctor(
    db: AsyncSession,
    department_id: Optional[str],
    experience_years: int,
    license_certificate: str,
    user_name: str,
    user_email: str,
    user_password: str,
    user_phone: str,
    hospital_admin_id: Optional[str] = None,
    bio: Optional[str] = None,
) -> Doctor:
    """Create a new doctor with an associated user account."""
    try:
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

        # Create user account for the doctor
        doctor_user = await create_user(
            db=db,
            name=user_name,
            email=user_email,
            password=user_password,
            phone_number=user_phone,
            role=RoleEnum.DOCTOR,
        )
        # Create doctor record
        doctor = Doctor(
            doctor_id=StringUtils.randomAlphaNumeric(8),
            experience_years=experience_years,
            license_certificate=license_file_obj,
            user_id=doctor_user.id,
            hospital_id=hospital.hospital_id if hospital else None,
            department_id=department_id,
            bio=bio,
        )

        db.add(doctor)
        await db.commit()
        await db.refresh(doctor)
        # Return doctor with relationships loaded
        result = await db.execute(
            select(Doctor)
            .join(Doctor.user)
            # .join(Doctor.license_certificate)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.department),
                # selectinload(Doctor.hospital),
            )
            .where(Doctor.doctor_id == doctor.doctor_id)
        )
        return result.scalar_one()

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        # raise HTTPException(status_code=500, detail=str(e))
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


async def get_all_doctors(db: AsyncSession) -> List[Doctor]:
    """Get all doctors with their user and hospital details."""
    try:
        result = await db.execute(
            select(Doctor).options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital),
                selectinload(Doctor.department),
            )
        )
        return list(result.scalars().all())
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


async def get_doctors_by_hospital(db: AsyncSession, hospital_id: str) -> List[Doctor]:
    """Get all doctors for a specific hospital."""
    try:
        # Verify hospital exists
        hospital_result = await db.execute(
            select(Hospital).where(Hospital.hospital_id == hospital_id)
        )
        hospital = hospital_result.scalar_one_or_none()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")

        result = await db.execute(
            select(Doctor)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital),
                selectinload(Doctor.department),
            )
            .where(Doctor.hospital_id == hospital_id)
        )
        return list(result.scalars().all())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_doctors_of_logged_in_hospital_admin(
    db: AsyncSession, hospital_admin_id: str
) -> List[Doctor]:
    """Get all doctors not associated with any hospital."""
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
        result = await db.execute(
            select(Doctor)
            .options(
                selectinload(Doctor.license_certificate),
                selectinload(Doctor.user).selectinload(User.role),
                selectinload(Doctor.user).selectinload(User.files),
                selectinload(Doctor.hospital),
                selectinload(Doctor.department),
            )
            .where(Doctor.hospital_id == hospital_of_admin.hospital_id)
        )
        return list(result.scalars().all())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def update_doctor(
    db: AsyncSession,
    doctor_id: str,
    current_user_id: str,
    role: RoleEnum,
    experience_years: Optional[int] = None,
    license_certificate: Optional[str] = None,
    department_id: Optional[str] = None,
    hospital_id: Optional[str] = None,
    status: Optional[DoctorStatusEnum] = None,
    bio: Optional[str] = None,
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
        if experience_years is not None:
            doctor.experience_years = experience_years
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
        if license_certificate is not None:
            license_file = await db.execute(
                select(File).where(File.file_id == license_certificate)
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
