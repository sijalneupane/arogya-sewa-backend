from enum import StrEnum


class AppointmentStatusEnum(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    INPROGRESS = "inprogress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
