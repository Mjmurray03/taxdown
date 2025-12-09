"""
Property schemas for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class PropertyType(str, Enum):
    """Property type classification codes."""
    RESIDENTIAL = "RES"
    COMMERCIAL = "COM"
    INDUSTRIAL = "IND"
    AGRICULTURAL = "AG"
    VACANT = "VAC"


class AssessmentCategory(str, Enum):
    """Assessment fairness categories based on fairness score."""
    FAIRLY_ASSESSED = "fairly_assessed"  # 0-30
    SLIGHTLY_OVER = "slightly_over"      # 31-50
    MODERATELY_OVER = "moderately_over"  # 51-70
    SIGNIFICANTLY_OVER = "significantly_over"  # 71-100
    UNANALYZED = "unanalyzed"            # No analysis yet


class PropertyBase(BaseModel):
    """Base property fields."""
    parcel_id: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: str = "AR"
    zip_code: Optional[str] = None
    county: str = "Benton"


class PropertySummary(PropertyBase):
    """Brief property info for lists."""
    id: str
    owner_name: Optional[str] = None
    total_value: Optional[float] = None  # Dollars
    assessed_value: Optional[float] = None
    property_type: Optional[str] = None
    subdivision: Optional[str] = None

    class Config:
        from_attributes = True


class PropertyDetail(PropertyBase):
    """Full property details."""
    id: str

    # Owner
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None

    # Values (in dollars)
    total_value: Optional[float] = None
    assessed_value: Optional[float] = None
    land_value: Optional[float] = None
    improvement_value: Optional[float] = None

    # Characteristics
    property_type: Optional[str] = None
    subdivision: Optional[str] = None
    neighborhood_code: Optional[str] = None
    legal_description: Optional[str] = None
    tax_area_acres: Optional[float] = None

    # Tax info
    tax_district: Optional[str] = None
    mill_rate: float = 65.0
    estimated_annual_tax: Optional[float] = None

    # Metadata
    source_date: Optional[date] = None
    last_updated: Optional[datetime] = None

    # Analysis (if available)
    fairness_score: Optional[int] = None
    recommended_action: Optional[str] = None
    estimated_savings: Optional[float] = None
    last_analyzed: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropertySearchRequest(BaseModel):
    """Search request parameters."""
    query: Optional[str] = Field(None, description="Search by address or owner name")
    parcel_id: Optional[str] = Field(None, description="Exact parcel ID match")

    # Filters
    city: Optional[str] = None
    subdivision: Optional[str] = None
    property_type: Optional[str] = None

    # Value range (in dollars)
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    # Assessment filters
    min_fairness_score: Optional[int] = Field(None, ge=0, le=100)
    max_fairness_score: Optional[int] = Field(None, ge=0, le=100)
    assessment_category: Optional[str] = Field(
        None,
        description="Filter by assessment category: fairly_assessed (0-30), slightly_over (31-50), moderately_over (51-70), significantly_over (71-100), unanalyzed"
    )
    only_appeal_candidates: bool = False

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    # Sorting
    sort_by: str = Field(default="address", pattern="^(address|value|assessed_value|fairness_score)$")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")


class PropertySearchResponse(BaseModel):
    """Search results."""
    properties: List[PropertySummary]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_more: bool


class PropertyListItem(BaseModel):
    """Minimal property for dropdowns/autocomplete."""
    id: str
    parcel_id: str
    address: str
    city: Optional[str] = None


class AddressSuggestion(BaseModel):
    """Address autocomplete suggestion."""
    property_id: str
    parcel_id: str
    address: str
    city: Optional[str] = None
    match_score: float
