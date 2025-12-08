"""
Services package for Taxdown Assessment Analyzer.

This package contains business logic services that wrap database operations
and provide clean, reusable interfaces for the application layer.
"""

from .comparable_service import (
    ComparableService,
    ComparableProperty,
    PropertyCriteria,
    PropertyNotFoundError,
    ServiceError,
    DatabaseError,
)
from .fairness_scorer import (
    FairnessScorer,
    FairnessResult,
)
from .savings_estimator import (
    SavingsEstimator,
    SavingsEstimate,
)
from .assessment_analyzer import (
    AssessmentAnalyzer,
    AssessmentAnalysis,
)

__all__ = [
    "ComparableService",
    "ComparableProperty",
    "PropertyCriteria",
    "PropertyNotFoundError",
    "ServiceError",
    "DatabaseError",
    "FairnessScorer",
    "FairnessResult",
    "SavingsEstimator",
    "SavingsEstimate",
    "AssessmentAnalyzer",
    "AssessmentAnalysis",
]
