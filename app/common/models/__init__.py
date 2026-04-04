from app.db.base import Base

from app.modules.file.v1.models import File
from app.modules.hospital.v1.models import Hospital
from app.modules.user.v1.models import User
from app.modules.dashboard.v1.models import ActivityLog
# Import Doctor separately to avoid circular imports
# from app.modules.doctor.v1.models import Doctor

__all__ = [
    "Base",
    "File",
    "Hospital",
    "User",
    "ActivityLog",
]
