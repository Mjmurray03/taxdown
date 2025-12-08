"""
Shared test fixtures for the Taxdown Assessment Analyzer test suite.

This module provides pytest fixtures for:
- Sample property data
- Comparable properties
- Database connections (mocked and real)
- Service instances
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.services import (
    ComparableService,
    ComparableProperty,
    PropertyCriteria,
    FairnessScorer,
    SavingsEstimator,
    AssessmentAnalyzer,
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_mock_row(**kwargs):
    """
    Create a mock database row with proper attribute access.

    Args:
        **kwargs: Field name and value pairs

    Returns:
        Mock object that behaves like a database row
    """
    mock_row = Mock()
    for key, value in kwargs.items():
        setattr(mock_row, key, value)
    return mock_row


# ============================================================================
# PROPERTY DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_property() -> Dict[str, Any]:
    """
    Sample property for testing.

    Returns property with realistic Bella Vista, AR values:
    - Total value: $250,000
    - Assessed value: $50,000 (20% statutory ratio)
    - Acreage: 0.5 acres
    - Type: Residential
    """
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "parcel_id": "01-12345-000",
        "address": "123 Test St, Bella Vista, AR 72714",
        "total_val_cents": 25000000,  # $250,000
        "assess_val_cents": 5000000,   # $50,000 (20%)
        "land_val_cents": 7500000,     # $75,000
        "imp_val_cents": 17500000,     # $175,000
        "acreage": 0.5,
        "property_type": "RES",
        "subdivision": "Test Subdivision",
        "owner_name": "Test Owner",
        "latitude": 36.3729,
        "longitude": -94.2088,
        "is_active": True
    }


@pytest.fixture
def over_assessed_property() -> Dict[str, Any]:
    """Property assessed at 25% instead of 20% (over-assessed)."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "parcel_id": "01-23456-000",
        "address": "456 Oak Ave, Bella Vista, AR 72714",
        "total_val_cents": 30000000,  # $300,000
        "assess_val_cents": 7500000,   # $75,000 (25%)
        "land_val_cents": 9000000,
        "imp_val_cents": 21000000,
        "acreage": 0.75,
        "property_type": "RES",
        "subdivision": "Test Subdivision",
        "owner_name": "Over Assessed Owner",
        "latitude": 36.3730,
        "longitude": -94.2089,
        "is_active": True
    }


@pytest.fixture
def under_assessed_property() -> Dict[str, Any]:
    """Property assessed at 15% instead of 20% (under-assessed)."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "parcel_id": "01-34567-000",
        "address": "789 Pine Rd, Bella Vista, AR 72714",
        "total_val_cents": 20000000,  # $200,000
        "assess_val_cents": 3000000,   # $30,000 (15%)
        "land_val_cents": 6000000,
        "imp_val_cents": 14000000,
        "acreage": 0.4,
        "property_type": "RES",
        "subdivision": "Test Subdivision",
        "owner_name": "Under Assessed Owner",
        "latitude": 36.3728,
        "longitude": -94.2087,
        "is_active": True
    }


@pytest.fixture
def sample_comparables() -> List[Dict[str, Any]]:
    """
    Sample comparable properties for testing.

    Returns 10 properties with varying assessment ratios:
    - 3 at 18% (under-assessed)
    - 4 at 20% (fair)
    - 3 at 22% (over-assessed)

    Median ratio: 20%
    """
    comparables = []

    # 3 properties at 18%
    for i in range(3):
        comparables.append({
            "parcel_id": f"01-{10000 + i}-000",
            "address": f"{100 + i} Main St",
            "total_val_cents": 24000000 + (i * 500000),
            "assess_val_cents": int((24000000 + (i * 500000)) * 0.18),
            "land_val_cents": 7000000,
            "imp_val_cents": 17000000,
            "acreage": 0.45 + (i * 0.02),
            "property_type": "RES",
            "subdivision": "Test Subdivision",
            "owner_name": f"Owner {i}",
            "distance_miles": 0.0,
            "match_type": "SUBDIVISION",
            "similarity_score": 85.0 + i,
            "assessment_ratio": 18.0,
            "value_difference_pct": 2.0 + i,
            "acreage_difference_pct": 5.0,
            "type_match_score": 100.0,
            "value_match_score": 90.0,
            "acreage_match_score": 85.0,
            "location_score": 100.0
        })

    # 4 properties at 20%
    for i in range(4):
        comparables.append({
            "parcel_id": f"01-{20000 + i}-000",
            "address": f"{200 + i} Oak Ave",
            "total_val_cents": 25000000 + (i * 300000),
            "assess_val_cents": int((25000000 + (i * 300000)) * 0.20),
            "land_val_cents": 7500000,
            "imp_val_cents": 17500000,
            "acreage": 0.48 + (i * 0.01),
            "property_type": "RES",
            "subdivision": "Test Subdivision",
            "owner_name": f"Owner {i + 3}",
            "distance_miles": 0.0,
            "match_type": "SUBDIVISION",
            "similarity_score": 90.0 + i,
            "assessment_ratio": 20.0,
            "value_difference_pct": 1.0,
            "acreage_difference_pct": 3.0,
            "type_match_score": 100.0,
            "value_match_score": 95.0,
            "acreage_match_score": 90.0,
            "location_score": 100.0
        })

    # 3 properties at 22%
    for i in range(3):
        comparables.append({
            "parcel_id": f"01-{30000 + i}-000",
            "address": f"{300 + i} Pine Rd",
            "total_val_cents": 26000000 + (i * 400000),
            "assess_val_cents": int((26000000 + (i * 400000)) * 0.22),
            "land_val_cents": 8000000,
            "imp_val_cents": 18000000,
            "acreage": 0.52 + (i * 0.02),
            "property_type": "RES",
            "subdivision": "Test Subdivision",
            "owner_name": f"Owner {i + 7}",
            "distance_miles": 0.0,
            "match_type": "SUBDIVISION",
            "similarity_score": 88.0 + i,
            "assessment_ratio": 22.0,
            "value_difference_pct": 3.0,
            "acreage_difference_pct": 4.0,
            "type_match_score": 100.0,
            "value_match_score": 92.0,
            "acreage_match_score": 88.0,
            "location_score": 100.0
        })

    return comparables


@pytest.fixture
def few_comparables() -> List[Dict[str, Any]]:
    """Only 3 comparable properties (edge case for confidence testing)."""
    return [
        {
            "parcel_id": "01-40000-000",
            "address": "400 Test St",
            "total_val_cents": 24000000,
            "assess_val_cents": 4800000,  # 20%
            "land_val_cents": 7000000,
            "imp_val_cents": 17000000,
            "acreage": 0.5,
            "property_type": "RES",
            "subdivision": "Test Subdivision",
            "owner_name": "Owner A",
            "distance_miles": 0.1,
            "match_type": "PROXIMITY",
            "similarity_score": 80.0,
            "assessment_ratio": 20.0,
            "value_difference_pct": 4.0,
            "acreage_difference_pct": 0.0,
            "type_match_score": 100.0,
            "value_match_score": 85.0,
            "acreage_match_score": 100.0,
            "location_score": 80.0
        },
        {
            "parcel_id": "01-40001-000",
            "address": "401 Test St",
            "total_val_cents": 26000000,
            "assess_val_cents": 5200000,  # 20%
            "land_val_cents": 7500000,
            "imp_val_cents": 18500000,
            "acreage": 0.55,
            "property_type": "RES",
            "subdivision": None,
            "owner_name": "Owner B",
            "distance_miles": 0.15,
            "match_type": "PROXIMITY",
            "similarity_score": 78.0,
            "assessment_ratio": 20.0,
            "value_difference_pct": 4.0,
            "acreage_difference_pct": 10.0,
            "type_match_score": 100.0,
            "value_match_score": 85.0,
            "acreage_match_score": 80.0,
            "location_score": 70.0
        },
        {
            "parcel_id": "01-40002-000",
            "address": "402 Test St",
            "total_val_cents": 25000000,
            "assess_val_cents": 5000000,  # 20%
            "land_val_cents": 7200000,
            "imp_val_cents": 17800000,
            "acreage": 0.48,
            "property_type": "RES",
            "subdivision": None,
            "owner_name": "Owner C",
            "distance_miles": 0.2,
            "match_type": "PROXIMITY",
            "similarity_score": 82.0,
            "assessment_ratio": 20.0,
            "value_difference_pct": 0.0,
            "acreage_difference_pct": 4.0,
            "type_match_score": 100.0,
            "value_match_score": 100.0,
            "acreage_match_score": 90.0,
            "location_score": 60.0
        }
    ]


# ============================================================================
# COMPARABLE PROPERTY OBJECTS
# ============================================================================

@pytest.fixture
def comparable_property_objects(sample_comparables) -> List[ComparableProperty]:
    """Convert sample comparables to ComparableProperty objects."""
    return [
        ComparableProperty(
            id=comp["parcel_id"],
            parcel_id=comp["parcel_id"],
            address=comp["address"],
            total_val_cents=comp["total_val_cents"],
            assess_val_cents=comp["assess_val_cents"],
            land_val_cents=comp["land_val_cents"],
            imp_val_cents=comp["imp_val_cents"],
            assessment_ratio=comp["assessment_ratio"],
            acreage=comp["acreage"],
            property_type=comp["property_type"],
            subdivision=comp["subdivision"],
            owner_name=comp["owner_name"],
            distance_miles=comp["distance_miles"],
            match_type=comp["match_type"],
            similarity_score=comp["similarity_score"],
            value_difference_pct=comp["value_difference_pct"],
            acreage_difference_pct=comp["acreage_difference_pct"],
            type_match_score=comp["type_match_score"],
            value_match_score=comp["value_match_score"],
            acreage_match_score=comp["acreage_match_score"],
            location_score=comp["location_score"]
        )
        for comp in sample_comparables
    ]


# ============================================================================
# DATABASE CONNECTION FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_engine():
    """Mock SQLAlchemy Engine for unit tests."""
    mock_engine = Mock(spec=Engine)
    mock_connection = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = Mock(return_value=mock_connection)
    mock_context.__exit__ = Mock(return_value=None)
    mock_engine.connect = Mock(return_value=mock_context)
    return mock_engine


@pytest.fixture
def mock_db_connection():
    """Mock SQLAlchemy Connection for unit tests."""
    return MagicMock()


@pytest.fixture
def db_engine():
    """
    Real database engine for integration tests.

    Uses DATABASE_URL from .env file. Tests marked with @pytest.mark.integration
    will use this fixture to test against actual database.
    """
    from src.config import get_engine
    return get_engine()


# ============================================================================
# SERVICE FIXTURES
# ============================================================================

@pytest.fixture
def comparable_service(mock_db_engine):
    """ComparableService instance with mocked database."""
    return ComparableService(mock_db_engine)


@pytest.fixture
def fairness_scorer():
    """FairnessScorer instance."""
    return FairnessScorer()


@pytest.fixture
def savings_estimator():
    """SavingsEstimator instance with default mill rate."""
    return SavingsEstimator(default_mill_rate=65.0)


@pytest.fixture
def assessment_analyzer(mock_db_engine):
    """AssessmentAnalyzer instance with mocked database."""
    return AssessmentAnalyzer(mock_db_engine, default_mill_rate=65.0)


# ============================================================================
# PROPERTY CRITERIA FIXTURES
# ============================================================================

@pytest.fixture
def sample_criteria() -> PropertyCriteria:
    """Sample PropertyCriteria for testing."""
    return PropertyCriteria(
        total_val_cents=25000000,  # $250,000
        acreage=0.5,
        property_type="RES",
        subdivision="Test Subdivision",
        latitude=36.3729,
        longitude=-94.2088
    )


@pytest.fixture
def invalid_criteria_negative_value() -> PropertyCriteria:
    """PropertyCriteria with invalid negative value."""
    return PropertyCriteria(
        total_val_cents=-1000000,
        acreage=0.5,
        property_type="RES",
        subdivision=None,
        latitude=36.3729,
        longitude=-94.2088
    )


@pytest.fixture
def invalid_criteria_zero_acreage() -> PropertyCriteria:
    """PropertyCriteria with invalid zero acreage."""
    return PropertyCriteria(
        total_val_cents=25000000,
        acreage=0.0,
        property_type="RES",
        subdivision=None,
        latitude=36.3729,
        longitude=-94.2088
    )


@pytest.fixture
def invalid_criteria_empty_type() -> PropertyCriteria:
    """PropertyCriteria with invalid empty property type."""
    return PropertyCriteria(
        total_val_cents=25000000,
        acreage=0.5,
        property_type="",
        subdivision=None,
        latitude=36.3729,
        longitude=-94.2088
    )


@pytest.fixture
def invalid_criteria_bad_coordinates() -> PropertyCriteria:
    """PropertyCriteria with invalid coordinates."""
    return PropertyCriteria(
        total_val_cents=25000000,
        acreage=0.5,
        property_type="RES",
        subdivision=None,
        latitude=95.0,  # Invalid latitude
        longitude=-94.2088
    )
