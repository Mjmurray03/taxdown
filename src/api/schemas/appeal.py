from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class AppealStatus(str, Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    WITHDRAWN = "WITHDRAWN"


class TemplateStyle(str, Enum):
    FORMAL = "formal"
    DETAILED = "detailed"
    CONCISE = "concise"


class GenerateAppealRequest(BaseModel):
    """Request to generate an appeal"""
    property_id: Optional[str] = Field(None, description="Property UUID")
    parcel_id: Optional[str] = Field(None, description="Parcel ID (alternative)")

    # Options
    style: TemplateStyle = Field(TemplateStyle.FORMAL, description="Letter style")
    include_comparables: bool = Field(True, description="Include comparables table")
    save_to_database: bool = Field(True, description="Save appeal to database (default: true)")

    # Override values (optional)
    mill_rate: float = Field(65.0, description="Mill rate for calculations")


class AppealPackageResponse(BaseModel):
    """Generated appeal package"""
    # Identifiers
    appeal_id: Optional[str] = None
    property_id: str
    parcel_id: str
    address: Optional[str] = None

    # Owner info
    owner_name: Optional[str] = None

    # Values
    current_assessed_value: Optional[float] = None
    requested_assessed_value: Optional[float] = None
    estimated_annual_savings: Optional[float] = None

    # Generated content
    appeal_letter: str
    executive_summary: Optional[str] = None
    evidence_summary: Optional[str] = None

    # Analysis backing
    fairness_score: int
    confidence_level: int
    comparable_count: int

    # Filing info
    jurisdiction: str = "Benton County Board of Equalization"
    filing_deadline: Optional[date] = None
    required_forms: List[str] = ["Written Statement of Appeal"]
    statute_reference: str = "Arkansas Code § 26-27-301"

    # Metadata
    generated_at: datetime
    generator_type: str  # "TEMPLATE" or "CLAUDE_API"
    template_style: str
    word_count: int

    # Status
    status: AppealStatus = AppealStatus.GENERATED


class AppealListItem(BaseModel):
    """Brief appeal info for lists"""
    appeal_id: str
    property_id: str
    parcel_id: str
    address: Optional[str] = None
    status: AppealStatus
    estimated_savings: Optional[float] = None
    generated_at: datetime


class AppealDownloadRequest(BaseModel):
    """Request to download appeal as file"""
    format: str = Field("pdf", pattern="^(pdf|txt|docx)$")


class BatchAppealRequest(BaseModel):
    """Request to generate appeals for multiple properties"""
    property_ids: List[str] = Field(..., max_length=20)
    style: TemplateStyle = TemplateStyle.FORMAL
    save_to_database: bool = False


class BatchAppealResponse(BaseModel):
    """Batch appeal generation results"""
    total_requested: int
    generated: int
    skipped: int  # Properties that don't qualify
    errors: int

    total_potential_savings: float
    appeals: List[AppealPackageResponse]
