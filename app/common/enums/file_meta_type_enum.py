from enum import Enum


class FileMetaTypeEnum(str, Enum):
    image = "image"
    video = "video"
    pdf = "pdf"
