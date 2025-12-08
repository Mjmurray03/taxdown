"""
Appeal Generation Data Models

This module contains dataclasses and configuration models for the appeal generation system.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class AppealStatus(str, Enum):
    """Status of an appeal through its lifecycle."""
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    WITHDRAWN = "WITHDRAWN"


class TemplateStyle(str, Enum):
    """Style options for appeal letter generation."""
    FORMAL = "formal"
    DETAILED = "detailed"
    CONCISE = "concise"


class GeneratorType(str, Enum):
    """Type of generator used to create the appeal."""
    TEMPLATE = "TEMPLATE"
    CLAUDE_API = "CLAUDE_API"


@dataclass
class GeneratorConfig:
    """
    Configuration for the AppealGenerator.

    Attributes:
        template_style: Style of appeal letter (formal, detailed, concise)
        mill_rate: Mill rate for tax calculations (default: 65.0 for Benton County)
        save_to_database: Whether to persist generated appeals
        include_comparables: Whether to include comparable properties table
        use_claude_api: Whether to use Claude API for enhanced letter generation
        jurisdiction: Tax jurisdiction name
        filing_deadline_month: Month when appeals are due (default: 5 for May)
        filing_deadline_day: Day when appeals are due (default: 31)
    """
    template_style: str = "formal"
    mill_rate: float = 65.0
    save_to_database: bool = False
    include_comparables: bool = True
    use_claude_api: bool = False
    jurisdiction: str = "Benton County Board of Equalization"
    filing_deadline_month: int = 5
    filing_deadline_day: int = 31

    def get_filing_deadline(self) -> date:
        """Calculate the next filing deadline."""
        today = date.today()
        deadline = date(today.year, self.filing_deadline_month, self.filing_deadline_day)
        if today > deadline:
            deadline = date(today.year + 1, self.filing_deadline_month, self.filing_deadline_day)
        return deadline


@dataclass
class ComparablePropertySummary:
    """Summary of a comparable property for appeal documentation."""
    parcel_id: str
    address: str
    total_value_cents: int
    assessed_value_cents: int
    assessment_ratio: float
    square_footage: Optional[int] = None
    year_built: Optional[int] = None
    distance_miles: Optional[float] = None
    similarity_score: Optional[float] = None

    @property
    def total_value_dollars(self) -> float:
        return self.total_value_cents / 100.0

    @property
    def assessed_value_dollars(self) -> float:
        return self.assessed_value_cents / 100.0


@dataclass
class AppealPackage:
    """
    Complete appeal package containing all generated content and metadata.

    This is the primary output of the AppealGenerator, containing everything
    needed to file a property tax appeal.
    """
    # Identifiers
    appeal_id: Optional[str] = None
    property_id: str = ""
    parcel_id: str = ""
    address: Optional[str] = None

    # Owner information
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None

    # Current assessment values (in cents)
    current_assessed_value_cents: int = 0
    current_total_value_cents: int = 0
    current_assessment_ratio: float = 0.0

    # Requested values (in cents)
    requested_assessed_value_cents: int = 0
    requested_total_value_cents: int = 0
    target_assessment_ratio: float = 0.0

    # Savings estimates (in cents)
    estimated_annual_savings_cents: int = 0
    estimated_five_year_savings_cents: int = 0
    reduction_amount_cents: int = 0

    # Generated content
    appeal_letter_text: str = ""
    executive_summary: Optional[str] = None
    evidence_summary: Optional[str] = None
    comparables_table: Optional[str] = None

    # Analysis backing
    fairness_score: int = 0
    confidence_level: int = 0
    interpretation: str = ""
    comparable_count: int = 0
    comparables: List[ComparablePropertySummary] = field(default_factory=list)

    # Filing information
    jurisdiction: str = "Benton County Board of Equalization"
    jurisdiction_address: str = "215 E Central Ave, Suite 217\nBentonville, AR 72712"
    filing_deadline: Optional[date] = None
    required_forms: List[str] = field(default_factory=lambda: ["Written Statement of Appeal"])
    statute_reference: str = "Arkansas Code § 26-27-301"

    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    generator_type: str = "TEMPLATE"
    template_style: str = "formal"
    model_version: str = "1.0.0"

    # Status tracking
    status: str = "GENERATED"

    def __post_init__(self):
        """Generate appeal_id if not provided."""
        if not self.appeal_id:
            self.appeal_id = str(uuid.uuid4())

    @property
    def current_assessed_value_dollars(self) -> float:
        return self.current_assessed_value_cents / 100.0

    @property
    def requested_assessed_value_dollars(self) -> float:
        return self.requested_assessed_value_cents / 100.0

    @property
    def estimated_annual_savings_dollars(self) -> float:
        return self.estimated_annual_savings_cents / 100.0

    @property
    def word_count(self) -> int:
        return len(self.appeal_letter_text.split()) if self.appeal_letter_text else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'appeal_id': self.appeal_id,
            'property_id': self.property_id,
            'parcel_id': self.parcel_id,
            'address': self.address,
            'owner_name': self.owner_name,
            'current_assessed_value_cents': self.current_assessed_value_cents,
            'requested_assessed_value_cents': self.requested_assessed_value_cents,
            'estimated_annual_savings_cents': self.estimated_annual_savings_cents,
            'estimated_five_year_savings_cents': self.estimated_five_year_savings_cents,
            'appeal_letter_text': self.appeal_letter_text,
            'executive_summary': self.executive_summary,
            'evidence_summary': self.evidence_summary,
            'fairness_score': self.fairness_score,
            'confidence_level': self.confidence_level,
            'comparable_count': self.comparable_count,
            'jurisdiction': self.jurisdiction,
            'filing_deadline': self.filing_deadline.isoformat() if self.filing_deadline else None,
            'required_forms': self.required_forms,
            'statute_reference': self.statute_reference,
            'generated_at': self.generated_at.isoformat(),
            'generator_type': self.generator_type,
            'template_style': self.template_style,
            'status': self.status,
            'word_count': self.word_count,
        }


@dataclass
class BatchAppealResult:
    """Results from batch appeal generation."""
    total_requested: int = 0
    generated: int = 0
    skipped: int = 0
    errors: int = 0
    total_potential_savings_cents: int = 0
    appeals: List[AppealPackage] = field(default_factory=list)
    error_details: List[Dict[str, str]] = field(default_factory=list)

    @property
    def total_potential_savings_dollars(self) -> float:
        return self.total_potential_savings_cents / 100.0

    @property
    def success_rate(self) -> float:
        if self.total_requested == 0:
            return 0.0
        return self.generated / self.total_requested * 100
