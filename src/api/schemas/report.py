"""
Report generation schemas for the Taxdown API.

Contains request/response models for report generation endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class ReportFormat(str, Enum):
    """Supported report output formats"""
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"


class ReportType(str, Enum):
    """Types of reports that can be generated"""
    PORTFOLIO_SUMMARY = "portfolio_summary"
    APPEAL_PACKAGE = "appeal_package"
    PROPERTY_ANALYSIS = "property_analysis"
    COMPARABLES = "comparables"


class GenerateReportRequest(BaseModel):
    """Request model for generating reports"""
    portfolio_id: Optional[str] = None
    property_id: Optional[str] = None
    report_type: ReportType = ReportType.PORTFOLIO_SUMMARY
    format: ReportFormat = ReportFormat.PDF

    # Options
    include_executive_summary: bool = True
    include_property_details: bool = True
    include_analysis_results: bool = True
    include_recommendations: bool = True
    include_comparables: bool = False
    include_geographic_breakdown: bool = True

    # Filters
    only_appeal_candidates: bool = False
    min_fairness_score: Optional[int] = Field(None, ge=0, le=100)

    # Sorting
    sort_by: str = Field("savings", pattern="^(savings|fairness_score|value|address)$")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


class ReportJobResponse(BaseModel):
    """Response model for async report generation jobs"""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    report_type: str
    format: str
    download_url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class ReportMetadata(BaseModel):
    """Metadata about a generated report"""
    filename: str
    format: str
    size_bytes: int
    generated_at: str
    properties_included: int
    total_value: Optional[float] = None
    total_savings: Optional[float] = None
