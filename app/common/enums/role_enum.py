from enum import StrEnum


class RoleEnum(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    HOSPITAL_ADMIN = "HOSPITAL_ADMIN"
    DOCTOR = "DOCTOR"
    PATIENT = "PATIENT"
