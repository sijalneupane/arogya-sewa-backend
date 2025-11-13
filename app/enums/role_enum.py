from enum import StrEnum


class RoleEnum(StrEnum):
    SUPER_ADMIN = "super_admin"
    HOSPITAL_ADMIN = "hospital_admin"
    DOCTOR = "doctor"
    PATIENT = "patient"
