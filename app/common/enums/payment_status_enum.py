from enum import StrEnum


class PaymentStatusEnum(StrEnum):
    UNPAID = "Unpaid"
    PARTIAL = "Partial"
    PAID = "Paid"
    REFUNDED = "Refunded"
