"""
Global pagination schemas for API requests and responses.
"""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class PaginationQuery(BaseModel):
    """Query parameters for pagination"""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(100, ge=1, le=500, description="Number of items per page")


class PaginationMeta(BaseModel):
    """Pagination metadata for responses"""

    currentPage: int = Field(..., description="Current page number")
    totalPages: int = Field(..., description="Total number of pages")
    pageSize: int = Field(..., description="Number of items per page")
    totalRecords: int = Field(..., description="Total number of records")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Generic paginated response wrapper"""

    message: str
    data: DataT
    paginationMeta: PaginationMeta
