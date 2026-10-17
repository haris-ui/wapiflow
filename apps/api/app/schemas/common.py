from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with ORM mode enabled."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response envelope."""

    items: List[T]
    total: int = Field(..., ge=0, description="Total matching items across all pages")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages available")
    has_next: bool = Field(..., description="Whether a next page exists")


class ErrorResponse(BaseModel):
    """Standardized error response envelope preventing raw stack trace exposure."""

    error: str = Field(..., description="Error classification code")
    message: str = Field(..., description="Human-readable error description")
    request_id: Optional[str] = Field(None, description="Correlation identifier for tracing")
    details: Optional[Any] = Field(None, description="Detailed validation or context errors")


class SuccessResponse(BaseModel):
    """Standardized success response envelope."""

    message: str
    data: Optional[Any] = None
