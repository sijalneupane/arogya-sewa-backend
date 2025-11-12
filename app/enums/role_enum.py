from enum import Enum


class RoleEnum(str, Enum):
    SUPER_ADMIN = "super_admin"
    HOSPITAL_ADMIN = "hospital_admin"
    DOCTOR = "doctor"
    PATIENT = "patient"
