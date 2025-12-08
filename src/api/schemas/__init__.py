"""
API schemas package.

Contains Pydantic models for request/response validation.
"""

from .common import (
    ResponseStatus,
    ErrorDetail,
    APIResponse,
    PaginationParams,
    PaginatedResponse,
    SortOrder,
    create_paginated_response,
    cents_to_dollars,
)

from .property import (
    PropertyType,
    PropertyBase,
    PropertySummary,
    PropertyDetail,
    PropertySearchRequest,
    PropertySearchResponse,
    PropertyListItem,
    AddressSuggestion,
)

__all__ = [
    # Common
    "ResponseStatus",
    "ErrorDetail",
    "APIResponse",
    "PaginationParams",
    "PaginatedResponse",
    "SortOrder",
    "create_paginated_response",
    "cents_to_dollars",
    # Property
    "PropertyType",
    "PropertyBase",
    "PropertySummary",
    "PropertyDetail",
    "PropertySearchRequest",
    "PropertySearchResponse",
    "PropertyListItem",
    "AddressSuggestion",
]
