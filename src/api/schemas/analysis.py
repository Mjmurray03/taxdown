"""
Analysis API Schemas

Pydantic models for assessment analysis request/response validation.

SCORING SYSTEM (Sales Comparison Approach):
The fairness_score indicates how fairly a property is assessed relative to
comparable properties in the same neighborhood. Higher score = FAIRER.

- 90-100: Fairly assessed (at or below comparable median)
- 70-89: Slightly above comparables (probably fair)
- 50-69: Moderately above comparables (worth reviewing)
- 30-49: Significantly above comparables (appeal candidate)
- 0-29: Greatly above comparables (strong appeal candidate)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RecommendedAction(str, Enum):
    APPEAL = "APPEAL"
    MONITOR = "MONITOR"
    NONE = "NONE"


class ComparablePropertySchema(BaseModel):
    """Comparable property in analysis"""
    property_id: str
    parcel_id: str
    address: Optional[str] = None
    total_value: Optional[float] = None
    assessed_value: Optional[float] = None
    assessment_ratio: Optional[float] = None
    distance_miles: Optional[float] = None
    similarity_score: Optional[float] = None


class AssessmentAnalysisResult(BaseModel):
    """
    Full analysis result using the Sales Comparison Approach.

    The analysis compares the subject property's total market value to
    comparable properties in the same neighborhood to identify potential
    over-assessments.

    fairness_score interpretation (higher = FAIRER):
    - 90-100: Fairly assessed
    - 70-89: Slightly above comparables
    - 50-69: Moderately above comparables (worth reviewing)
    - 30-49: Significantly above comparables (appeal candidate)
    - 0-29: Greatly above comparables (strong appeal candidate)
    """
    property_id: str
    parcel_id: str
    address: Optional[str] = None

    # Current values (dollars)
    current_market_value: Optional[float] = None
    current_assessed_value: Optional[float] = None
    current_assessment_ratio: Optional[float] = None  # Always ~20% for Benton County

    # Analysis results
    fairness_score: int = Field(..., ge=0, le=100, description="0-100, higher = fairer assessment")
    confidence_level: int = Field(..., ge=0, le=100)

    # Recommendation
    recommended_action: RecommendedAction
    fair_assessed_value: Optional[float] = Field(None, description="What assessment SHOULD be based on comparables (dollars)")
    estimated_annual_savings: Optional[float] = None

    # Comparables summary
    comparable_count: int
    median_comparable_value: Optional[float] = Field(None, description="Median market value of comparable properties (dollars)")
    percentile_rank: Optional[int] = None

    # Backward compatibility alias
    @property
    def median_comparable_ratio(self) -> Optional[float]:
        """Backward compatibility - same as median_comparable_value."""
        return self.median_comparable_value

    # Detailed comparables (optional)
    comparables: Optional[List[ComparablePropertySchema]] = None

    # Metadata
    analysis_date: datetime
    mill_rate_used: float = 65.0

    class Config:
        from_attributes = True


class AnalyzePropertyRequest(BaseModel):
    """Request to analyze a single property"""
    property_id: Optional[str] = Field(None, description="Property UUID")
    parcel_id: Optional[str] = Field(None, description="Parcel ID")

    # Options
    force_reanalyze: bool = Field(False, description="Force new analysis even if recent exists")
    include_comparables: bool = Field(True, description="Include comparable properties in response")
    mill_rate: float = Field(65.0, description="Mill rate for tax calculations")


class BulkAnalyzeRequest(BaseModel):
    """Request to analyze multiple properties"""
    property_ids: List[str] = Field(..., max_length=100)
    force_reanalyze: bool = False
    mill_rate: float = 65.0


class BulkAnalyzeResponse(BaseModel):
    """Bulk analysis results"""
    total_requested: int
    analyzed: int
    skipped: int
    errors: int

    # Aggregate metrics
    appeal_candidates_found: int
    total_potential_savings: float

    # Per-property results
    results: List[AssessmentAnalysisResult]

    # Timing
    duration_seconds: float


class AnalysisSummary(BaseModel):
    """Brief analysis summary for lists"""
    property_id: str
    parcel_id: str
    fairness_score: int
    recommended_action: str
    estimated_savings: Optional[float] = None
    analysis_date: datetime
