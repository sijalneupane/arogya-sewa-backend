from enum import StrEnum


class PaymentTransactionStatusEnum(StrEnum):
    PENDING = "Pending"
    SUCCESS = "Success"
    FAILED = "Failed"
    REFUNDED = "Refunded"
