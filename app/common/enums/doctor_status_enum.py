from enum import Enum


class DoctorStatusEnum(Enum):
    ACTIVE = "Active"
    ON_LEAVE = "On Leave"
    ON_APPOINTMENT = "On Appointment"  # Fully booked / packed by appointments
    INACTIVE = "Inactive"
