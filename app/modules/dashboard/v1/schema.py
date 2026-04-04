from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.common.enums.activity_log_action_type_enum import ActivityLogActionTypeEnum
from app.common.schema.pagination import PaginationQuery


class ActivityLogResponse(BaseModel):
    activity_log_id: str
    user_id: str
    hospital_id: Optional[str] = None
    action_type: ActivityLogActionTypeEnum
    entity_type: str
    entity_id: str
    description: str
    created_at: datetime
    metadata: Optional[dict] = None

    # Computed fields for user and hospital info
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class ActivityLogCreate(BaseModel):
    user_id: str
    hospital_id: Optional[str] = None
    action_type: ActivityLogActionTypeEnum
    entity_type: str = Field(
        ..., description="Entity type like 'Appointment', 'User', etc."
    )
    entity_id: str = Field(..., description="Raw entity ID, not a relationship")
    description: str
    metadata: Optional[dict] = None


class DashboardActivityFilters(PaginationQuery):
    user_id: Optional[str] = None
    hospital_id: Optional[str] = None
    action_type: Optional[ActivityLogActionTypeEnum] = None
    entity_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
