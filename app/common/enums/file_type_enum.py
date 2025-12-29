from enum import Enum


class FileTypeEnum(str, Enum):
    PROFILE = "profile"
    LICENSE = "license"
    HOSPITAL_LOGO = "hospital_logo"
    HOSPITAL = "hospital"
    HOSPITAL_BANNER = "hospital_banner"
    MEDICAL_REPORT = "medical_report"
    PRESCRIPTION = "prescription"
    OTHER = "other"
