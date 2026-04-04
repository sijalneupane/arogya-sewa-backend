from enum import StrEnum


class ActivityLogActionTypeEnum(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CANCEL = "CANCEL"
    APPROVE = "APPROVE"
