"""
Portfolio management schemas.

Contains Pydantic models for user accounts, portfolios, and portfolio properties.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class UserType(str, Enum):
    INVESTOR = "INVESTOR"
    AGENT = "AGENT"
    HOMEOWNER = "HOMEOWNER"


class SubscriptionTier(str, Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class OwnershipType(str, Enum):
    OWNER = "OWNER"
    TRACKING = "TRACKING"
    INTERESTED = "INTERESTED"


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    user_type: UserType = UserType.INVESTOR


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    user_type: UserType
    subscription_tier: SubscriptionTier
    created_at: datetime
    last_login: Optional[datetime] = None


# Portfolio schemas
class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    default_mill_rate: float = Field(65.0, ge=0)
    auto_analyze: bool = True


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    default_mill_rate: Optional[float] = Field(None, ge=0)
    auto_analyze: Optional[bool] = None


class PortfolioSummaryResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    property_count: int
    total_value: Optional[float] = None
    total_assessed_value: Optional[float] = None
    estimated_annual_tax: Optional[float] = None
    total_potential_savings: Optional[float] = None
    appeal_candidates: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class PortfolioDetailResponse(PortfolioSummaryResponse):
    default_mill_rate: float
    auto_analyze: bool
    properties: List["PortfolioPropertyResponse"] = []


# Portfolio Property schemas
class AddPropertyRequest(BaseModel):
    property_id: Optional[str] = None
    parcel_id: Optional[str] = None
    ownership_type: OwnershipType = OwnershipType.OWNER
    ownership_percentage: float = Field(100.0, ge=0, le=100)
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None  # Dollars
    notes: Optional[str] = None
    tags: List[str] = []
    is_primary_residence: bool = False


class UpdatePropertyRequest(BaseModel):
    ownership_type: Optional[OwnershipType] = None
    ownership_percentage: Optional[float] = Field(None, ge=0, le=100)
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_primary_residence: Optional[bool] = None


class PortfolioPropertyResponse(BaseModel):
    id: str
    portfolio_id: str
    property_id: str
    parcel_id: str
    address: Optional[str] = None
    city: Optional[str] = None
    owner_name: Optional[str] = None

    # Ownership details
    ownership_type: OwnershipType
    ownership_percentage: float
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None

    # Current values (dollars)
    market_value: Optional[float] = None
    assessed_value: Optional[float] = None
    estimated_annual_tax: Optional[float] = None

    # Analysis results
    fairness_score: Optional[int] = None
    recommended_action: Optional[str] = None
    estimated_savings: Optional[float] = None
    last_analyzed: Optional[datetime] = None

    # Metadata
    notes: Optional[str] = None
    tags: List[str] = []
    is_primary_residence: bool = False
    added_at: datetime


# Bulk import
class BulkImportRequest(BaseModel):
    properties: List[AddPropertyRequest]


class BulkImportResponse(BaseModel):
    total_requested: int
    added: int
    duplicates: int
    not_found: int
    errors: int
    error_details: List[str] = []
    properties_added: List[PortfolioPropertyResponse] = []


# Dashboard
class DashboardMetrics(BaseModel):
    total_properties: int
    total_market_value: float
    total_assessed_value: float
    estimated_annual_tax: float
    total_potential_savings: float
    appeal_candidates: int
    average_fairness_score: Optional[float] = None

    # Breakdowns
    by_ownership_type: Dict[str, int] = {}
    by_city: Dict[str, int] = {}
    by_recommendation: Dict[str, int] = {}


class TopProperty(BaseModel):
    property_id: str
    parcel_id: str
    address: Optional[str] = None
    value: float  # The metric being ranked by
    metric_name: str


class DashboardResponse(BaseModel):
    portfolio_id: str
    portfolio_name: str
    metrics: DashboardMetrics
    top_savings_opportunities: List[TopProperty]
    top_over_assessed: List[TopProperty]
    recent_analyses: List[Dict[str, Any]]
    appeal_deadline: Optional[date] = None
    days_until_deadline: Optional[int] = None


# Forward reference resolution
PortfolioDetailResponse.model_rebuild()
