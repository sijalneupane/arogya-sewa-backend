from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.enums.role_enum import RoleEnum
from app.models.authorization import Authorization
from app.models.role import Role
from app.utils.string_utils import StringUtils

# Define HTTP methods
readOnlyMethods = ["GET"]
partialReadWriteMethods = ["POST"]
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
    return [setAuthorizationPermissions(role, "/**", readOnlyMethods + writeMethods)]


def getHospitalAdminPermissions(role: Role) -> List[Authorization]:
    return [setAuthorizationPermissions(role, "/users", readOnlyMethods + writeMethods)]


def getUserPermissions(role: Role) -> List[Authorization]:
    return [
        setAuthorizationPermissions(
            role, "/users/me", readOnlyMethods + partialReadWriteMethods
        )
    ]


def getDoctorPermissions(role: Role) -> List[Authorization]:
    return [
        setAuthorizationPermissions(role, "/doctor/me", readOnlyMethods + writeMethods),
        setAuthorizationPermissions(
            role, "/appointments", readOnlyMethods + writeMethods
        ),
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
