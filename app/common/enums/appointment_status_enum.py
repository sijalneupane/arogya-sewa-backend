from enum import StrEnum


class AppointmentStatusEnum(StrEnum):
    PENDING_PAYMENT = "Pending Payment"
    CONFIRMED = "Confirmed"
    INPROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    RESCHEDULED = "Rescheduled"
