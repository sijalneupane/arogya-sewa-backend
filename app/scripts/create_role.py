# app/scripts/insert_roles.py

from app.db.database import SessionLocal
from app.db.database import sync_engine as engine
from app.enums.role_enum import RoleEnum
from app.models.base import Base
from app.models.role import Role
from app.utils.string_utils import StringUtils

# ✅ Ensure the table exists
Base.metadata.create_all(bind=engine)


def create_roles_if_not_exist():
    session = SessionLocal()
    try:
        roles = [
            RoleEnum.SUPER_ADMIN,
            RoleEnum.HOSPITAL_ADMIN,
            RoleEnum.DOCTOR,
            RoleEnum.PATIENT,
        ]
        roles_descriptions = [
            "Super Administrator with all permissions",
            "Hospital Administrator with elevated permissions",
            "Doctor with standard access",
            "Patient with limited access",
        ]

        for role_name, role_description in zip(roles, roles_descriptions):
            existing_role = session.query(Role).filter(Role.role == role_name).first()

            if not existing_role:
                new_role = Role(
                    id=StringUtils.randomAlphaNumeric(8),
                    role=role_name,
                    description=role_description,
                )
                session.add(new_role)
                print(f"✅ Created role: {role_name}")
            else:
                print(f"⚠️ Role already exists: {role_name}")

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"❌ Error while inserting roles: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    create_roles_if_not_exist()
