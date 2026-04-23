"""Seed authorization rules for the application."""
# pyright: reportUnusedImport=false

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.enums.role_enum import RoleEnum
from app.core.utils.string_utils import StringUtils
from app.db.database import AsyncSessionLocal
from app.modules.auth.v1.models import Authorization, Role

# Import all models to ensure they are registered with SQLAlchemy before running.
from app.modules.doctor.v1.models import Doctor
from app.modules.appointment.v1.models import Appointment
from app.modules.appointment.v1.changed_time_models import AppointmentChangedTime
from app.modules.department.v1.models import Department
from app.modules.file.v1.models import File
from app.modules.hospital.v1.models import Hospital
from app.modules.user.v1.models import User
from app.modules.patient.v1.models import Patient
from app.modules.notification.v1.models import Notification
from app.modules.availability.v1.models import Availability
from app.modules.dashboard.v1.models import ActivityLog
from app.modules.payment.v1.models import Payment

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
        # Super admin payment access
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/initiate", postMethod
        ),
        setAuthorizationPermissions(role, "/api/v1/payments/khalti/verify", postMethod),
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/final/initiate", postMethod
        ),
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/final/verify", postMethod
        ),
        setAuthorizationPermissions(role, "/api/v1/payments/cash/record", postMethod),
        setAuthorizationPermissions(
            role, "/api/v1/payments/appointment/{appointment_id}", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role, "/api/v1/payments/doctor/my-appointments", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role, "/api/v1/payments/hospital-admin/appointments", readOnlyMethods
        ),
        # Super admin notification access
        setAuthorizationPermissions(role, "/api/v1/notifications/send", postMethod),
        setAuthorizationPermissions(role, "/api/v1/notifications/me", readOnlyMethods),
        setAuthorizationPermissions(
            role,
            "/api/v1/notifications/{notification_id}/read",
            ["PATCH"],
        ),
        # Dashboard activity access
        setAuthorizationPermissions(
            role, "/api/v1/dashboard/activities", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role, "/api/v1/dashboard/activities/system", readOnlyMethods
        ),
        setAuthorizationPermissions(role, "/api/v1/dashboard/summary", readOnlyMethods),
        setAuthorizationPermissions(
            role,
            "/api/v1/dashboard/activities/hospital/{hospital_id}",
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
        # will chang to user/me for update later
        setAuthorizationPermissions(
            role, "/api/v1/users/{user_id}", readOnlyMethods + writeMethods
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
        setAuthorizationPermissions(
            role, "/api/v1/appointments/{appointment_id}/complete", ["PATCH"]
        ),
        # Hospital admin can create appointment changed times for appointments in their hospital
        setAuthorizationPermissions(
            role, "/api/v1/appointment-changed-times", postMethod
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
        # Hospital admin can create and manage departments in their hospital
        setAuthorizationPermissions(role, "/api/v1/departments", postMethod),
        setAuthorizationPermissions(role, "/api/v1/departments/my", readOnlyMethods),
        setAuthorizationPermissions(
            role, "/api/v1/departments/{department_id}", writeMethods
        ),
        # Hospital admin payment access
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/final/initiate", postMethod
        ),
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/final/verify", postMethod
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/payments/hospital-admin/appointments",
            readOnlyMethods,
        ),
        setAuthorizationPermissions(role, "/api/v1/payments/cash/record", postMethod),
        setAuthorizationPermissions(
            role, "/api/v1/payments/appointment/{appointment_id}", readOnlyMethods
        ),
        # Hospital admin notification access
        setAuthorizationPermissions(role, "/api/v1/notifications/send", postMethod),
        setAuthorizationPermissions(role, "/api/v1/notifications/me", readOnlyMethods),
        setAuthorizationPermissions(
            role,
            "/api/v1/notifications/{notification_id}/read",
            ["PATCH"],
        ),
        # Dashboard activity access (hospital scoped)
        setAuthorizationPermissions(
            role, "/api/v1/dashboard/activities", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role, "/api/v1/dashboard/hospital-admin/summary", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/dashboard/activities/hospital/{hospital_id}",
            readOnlyMethods,
        ),
    ]


def getUserPermissions(role: Role) -> List[Authorization]:
    return [
        # setAuthorizationPermissions(role, "/api/v1/doctors/upgrade", postMethod),
        setAuthorizationPermissions(
            role, "/api/v1/patient/profile/update/me", ["PATCH"]
        ),
        # Dashboard activity access (own activities)
        setAuthorizationPermissions(
            role, "/api/v1/dashboard/activities", readOnlyMethods
        ),
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
        # Patient can create appointment changed times for their appointments
        setAuthorizationPermissions(
            role, "/api/v1/appointment-changed-times", postMethod
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
        # Patient payment access
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/initiate", postMethod
        ),
        setAuthorizationPermissions(role, "/api/v1/payments/khalti/verify", postMethod),
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/final/initiate", postMethod
        ),
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/final/verify", postMethod
        ),
        setAuthorizationPermissions(
            role, "/api/v1/payments/appointment/{appointment_id}", readOnlyMethods
        ),
        # Patient notification access
        setAuthorizationPermissions(role, "/api/v1/notifications/me", readOnlyMethods),
        setAuthorizationPermissions(
            role,
            "/api/v1/notifications/{notification_id}/read",
            ["PATCH"],
        ),
        # setAuthorizationPermissions(
        #     role, "/users/me", readOnlyMethods + partialReadWriteMethods
        # )
    ]


def getDoctorPermissions(role: Role) -> List[Authorization]:
    return [
        setAuthorizationPermissions(role, "/api/v1/doctors/me", readOnlyMethods),
        # Dashboard activity access (own activities)
        setAuthorizationPermissions(
            role, "/api/v1/dashboard/activities", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role, "/api/v1/dashboard/doctor/summary", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role,
            "/api/v1/dashboard/doctor/upcoming-appointments",
            readOnlyMethods,
        ),
        setAuthorizationPermissions(
            role, "/api/v1/dashboard/doctor/today-appointments", readOnlyMethods
        ),
        setAuthorizationPermissions(role, "/api/v1/doctors/{doctor_id}", writeMethods),
        setAuthorizationPermissions(role, "/api/v1/availabilities", postMethod),
        setAuthorizationPermissions(role, "/api/v1/availabilities/me", readOnlyMethods),
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
            role, "/api/v1/appointments/{appointment_id}/complete", ["PATCH"]
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
        setAuthorizationPermissions(role, "/api/v1/payments/cash/record", postMethod),
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/final/initiate", postMethod
        ),
        setAuthorizationPermissions(
            role, "/api/v1/payments/khalti/final/verify", postMethod
        ),
        # Doctor payment access
        setAuthorizationPermissions(
            role, "/api/v1/payments/doctor/my-appointments", readOnlyMethods
        ),
        setAuthorizationPermissions(
            role, "/api/v1/payments/appointment/{appointment_id}", readOnlyMethods
        ),
        # Doctor notification access
        setAuthorizationPermissions(role, "/api/v1/notifications/me", readOnlyMethods),
        setAuthorizationPermissions(
            role,
            "/api/v1/notifications/{notification_id}/read",
            ["PATCH"],
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
