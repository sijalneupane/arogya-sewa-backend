from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.db.database import AsyncSessionLocal
from app.modules.auth.v1.models import Authorization, Role

# Import all models to ensure they're registered with SQLAlchemy before running
from app.modules.doctor.v1.models import Doctor  # Import Doctor model
from app.modules.file.v1.models import File
from app.modules.hospital.v1.models import Hospital
from app.modules.user.v1.models import User
from app.modules.patient.v1.models import Patient

# from app.modules.appointment.v1.models import Appointment
from app.modules.availability.v1.models import Availability

# Define HTTP methods
readOnlyMethods = ["GET"]
postMethod = ["POST"]
writeMethods = ["DELETE", "PUT", "PATCH"]


def setAuthorizationPermissions(
    role: Role, path: str, methods: List[str]
) -> Authorization:
    auth = Authorization()
    auth.id = StringUtils.randomAlphaNumeric(8)
    auth.role = role
    auth.path = path
    auth.methods = methods
    return auth


def getSuperAdminPermissions(role: Role) -> List[Authorization]:
    return [
        setAuthorizationPermissions(
            role, "/api/v1/users/{user_id}", readOnlyMethods + writeMethods
        ),
        setAuthorizationPermissions(role, "/api/v1/hospital", postMethod),
        setAuthorizationPermissions(
            role, "/api/v1/hospital/{hospital_id}", writeMethods
        ),
        # Super admin can view all appointments
        setAuthorizationPermissions(role, "/api/v1/appointments", readOnlyMethods),
        setAuthorizationPermissions(
            role, "/api/v1/appointments/{appointment_id}", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role, "/api/v1/appointments/admin/all", readOnlyMethods
        ),
        # Super admin can view all appointment changed times
        setAuthorizationPermissions(
            role, "/api/v1/appointment-changed-times/{changed_time_id}", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/appointment-changed-times/appointment/{appointment_id}",
            readOnlyMethods,
        ),
    ]


def getHospitalAdminPermissions(role: Role) -> List[Authorization]:
    return [
        # setAuthorizationPermissions(
        #     role, "/api/v1/users", readOnlyMethods + writeMethods
        # ),
        setAuthorizationPermissions(
            role, "/api/v1/hospital/{hospital_id}", writeMethods
        ),
        setAuthorizationPermissions(role, "/api/v1/hospital/my", readOnlyMethods),
        setAuthorizationPermissions(
            role, "/api/v1/doctors", postMethod + readOnlyMethods
        ),
        setAuthorizationPermissions(role, "/api/v1/doctors/{doctor_id}", writeMethods),
        setAuthorizationPermissions(role, "/api/v1/availabilities", postMethod),
        setAuthorizationPermissions(
            role,
            "/api/v1/availabilities/{availability_id}",
            writeMethods,
        ),
        # Hospital admin can view and manage appointments for their hospital
        setAuthorizationPermissions(role, "/api/v1/appointments", readOnlyMethods),
        setAuthorizationPermissions(
            role,
            "/api/v1/appointments/{appointment_id}",
            readOnlyMethods + writeMethods,
        ),
        setAuthorizationPermissions(
            role, "/api/v1/appointments/hospital-admin/appointments", readOnlyMethods
        ),
        # Hospital admin can view appointment changed times for their hospital
        setAuthorizationPermissions(
            role, "/api/v1/appointment-changed-times/{changed_time_id}", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/appointment-changed-times/appointment/{appointment_id}",
            readOnlyMethods,
        ),
    ]


def getUserPermissions(role: Role) -> List[Authorization]:
    return [
        setAuthorizationPermissions(role, "/api/v1/doctors/upgrade", postMethod),
        # Patient can book and view their appointments
        setAuthorizationPermissions(
            role, "/api/v1/appointments", postMethod + readOnlyMethods
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/appointments/{appointment_id}",
            readOnlyMethods + writeMethods,
        ),
        setAuthorizationPermissions(
            role, "/api/v1/appointments/patient/my-appointments", readOnlyMethods
        ),
        # Patient can view appointment changed times for their appointments
        setAuthorizationPermissions(
            role, "/api/v1/appointment-changed-times/{changed_time_id}", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/appointment-changed-times/appointment/{appointment_id}",
            readOnlyMethods,
        ),
        # setAuthorizationPermissions(
        #     role, "/users/me", readOnlyMethods + partialReadWriteMethods
        # )
    ]


def getDoctorPermissions(role: Role) -> List[Authorization]:
    return [
        setAuthorizationPermissions(role, "/api/v1/doctors/me", readOnlyMethods),
        setAuthorizationPermissions(role, "/api/v1/doctors/{doctor_id}", writeMethods),
        setAuthorizationPermissions(role, "/api/v1/availabilities", postMethod),
        setAuthorizationPermissions(
            role,
            "/api/v1/availabilities/{availability_id}",
            writeMethods,
        ),
        # Doctor can view their appointments
        setAuthorizationPermissions(role, "/api/v1/appointments", readOnlyMethods),
        setAuthorizationPermissions(
            role, "/api/v1/appointments/{appointment_id}", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role, "/api/v1/appointments/doctor/my-appointments", readOnlyMethods
        ),
        # Doctor can manage appointment changed times
        setAuthorizationPermissions(
            role, "/api/v1/appointment-changed-times", postMethod
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/appointment-changed-times/{changed_time_id}",
            readOnlyMethods + writeMethods,
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/appointment-changed-times/appointment/{appointment_id}",
            readOnlyMethods,
        ),
        # setAuthorizationPermissions(
        #     role, "/appointments", readOnlyMethods + writeMethods
        # ),
    ]


# ✅ Async version (recommended for FastAPI)
async def create_authorizations():
    async with AsyncSessionLocal() as session:
        try:
            # ✅ Check if all required roles exist
            required_roles = list(RoleEnum.__members__.keys())
            result = await session.execute(
                select(Role).filter(Role.role.in_(required_roles))
            )
            roles = list(result.scalars().all())

            if len(roles) != len(required_roles):
                missing_roles = set(required_roles) - {r.role for r in roles}
                raise Exception(
                    f"❌ One or more roles not found: {', '.join(missing_roles)}"
                )

            print("✅ All roles verified successfully")

            # Find each role
            super_admin = next(r for r in roles if r.role == RoleEnum.SUPER_ADMIN)
            hospital_admin = next(r for r in roles if r.role == RoleEnum.HOSPITAL_ADMIN)
            patient = next(r for r in roles if r.role == RoleEnum.PATIENT)
            doctor = next(r for r in roles if r.role == RoleEnum.DOCTOR)

            # ✅ Parallel permission creation (like Promise.all)
            from asyncio import gather

            authorizations_lists = await gather(
                *[
                    _create_permissions(session, getSuperAdminPermissions, super_admin),
                    _create_permissions(
                        session, getHospitalAdminPermissions, hospital_admin
                    ),
                    _create_permissions(session, getUserPermissions, patient),
                    _create_permissions(session, getDoctorPermissions, doctor),
                ]
            )

            # Flatten the lists
            all_authorizations = [
                auth for sublist in authorizations_lists for auth in sublist
            ]

            await session.commit()
            print("✅ Authorizations created successfully")
            return all_authorizations

        except Exception as e:
            await session.rollback()
            print(f"❌ Error while creating authorizations: {e}")
            raise


# helper for async gather
async def _create_permissions(
    session: AsyncSession, permission_fn, role: Role
) -> List[Authorization]:
    authorizations = permission_fn(role)
    session.add_all(authorizations)
    return authorizations


# Main execution
if __name__ == "__main__":
    import asyncio

    asyncio.run(create_authorizations())
