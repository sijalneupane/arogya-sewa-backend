from enum import StrEnum


class AppointmentStatusEnum(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    INPROGRESS = "inprogress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
