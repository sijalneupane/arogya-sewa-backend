from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreateSchema(BaseModel):
    """Schema for creating a new department"""

    name: str = Field(..., min_length=1, max_length=150)
    description: str = Field(..., min_length=1)
    is_active: bool = Field(True)


class DepartmentUpdateSchema(BaseModel):
    """Schema for updating an existing department"""

    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class DepartmentResponseSchema(BaseModel):
    """Schema for department response"""

    model_config = ConfigDict(from_attributes=True)

    department_id: str
    name: str
    description: str
    is_active: bool
    hospital_id: str
    created_at: datetime
    updated_at: datetime


class DepartmentDetailResponseSchema(BaseModel):
    """Schema for single department detail response"""

    message: str = "Department fetched successfully"
    data: DepartmentResponseSchema


class DepartmentListResponseSchema(BaseModel):
    """Schema for list of departments response"""

    message: str = "Departments fetched successfully"
    data: list[DepartmentResponseSchema]


class DepartmentFilterQuery(BaseModel):
    """Query parameters for filtering department list"""

    name: Optional[str] = Field(None, description="Search by department name")
