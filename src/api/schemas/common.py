"""
Common API schemas used across all endpoints.

Contains base response structures, pagination helpers, and utility functions.
"""

from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional, List, Any
from enum import Enum
from datetime import datetime


# Type variable for generic responses
T = TypeVar("T")


class ResponseStatus(str, Enum):
    """Standard API response status"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class ErrorDetail(BaseModel):
    """Error detail structure"""
    code: str
    message: str
    field: Optional[str] = None


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.

    All successful responses use this structure with data containing the payload.
    """
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: Optional[T] = None
    message: Optional[str] = None
    errors: Optional[List[ErrorDetail]] = None

    class Config:
        from_attributes = True


class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = None
    sort_order: SortOrder = SortOrder.DESC


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: List[T]
    pagination: PaginationMeta
    message: Optional[str] = None


def create_paginated_response(
    data: List[Any],
    page: int,
    page_size: int,
    total_items: int
) -> dict:
    """
    Create a paginated response structure.

    Args:
        data: List of items for current page
        page: Current page number
        page_size: Items per page
        total_items: Total number of items

    Returns:
        Dictionary with data and pagination metadata
    """
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "status": ResponseStatus.SUCCESS,
        "data": data,
        "pagination": PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    }


def cents_to_dollars(cents) -> Optional[float]:
    """
    Convert cents to dollars.

    Args:
        cents: Amount in cents (can be int, float, or Decimal)

    Returns:
        Amount in dollars, or None if input is None
    """
    if cents is None:
        return None
    return float(cents) / 100.0
