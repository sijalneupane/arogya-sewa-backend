from enum import StrEnum


class NotificationTypeEnum(StrEnum):
    SYSTEM = "System"
    APPOINTMENT = "Appointment"
    PAYMENT = "Payment"
    REMINDER = "Reminder"
    PROMOTION = "Promotion"
