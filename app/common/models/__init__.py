from app.db.base import Base

# from app.modules.doctor.v1 import doctor
from app.modules.file.v1.models import File
from app.modules.hospital.v1.models import Hospital
from app.modules.user.v1.models import User

__all__ = [
    "Base",
    "File",
    "Hospital",
    "User",
]
