from enum import Enum


class FileTypeEnum(str, Enum):
    PROFILE = "profile"
    LICENSE = "license"
    HOSPITAL_LOGO = "hospital_logo"
    HOSPITAL = "hospital"
