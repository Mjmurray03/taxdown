"""
Comprehensive unit tests for Taxdown Assessment Analyzer services.

This test suite provides full coverage for:
1. ComparableService - Property matching and similarity scoring
2. FairnessScorer - Statistical fairness analysis
3. SavingsEstimator - Tax savings calculations
4. AssessmentAnalyzer - Full analysis workflow integration

Test categories:
- Unit tests: Test individual methods with mocked dependencies
- Integration tests: Test with real database (marked with @pytest.mark.integration)
- Edge cases: Test boundary conditions and error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import statistics

from src.services import (
    ComparableService,
    ComparableProperty,
    PropertyCriteria,
    PropertyNotFoundError,
    ServiceError,
    DatabaseError,
    FairnessScorer,
    FairnessResult,
    SavingsEstimator,
    SavingsEstimate,
    AssessmentAnalyzer,
    AssessmentAnalysis,
)



# ============================================================================
# COMPARABLE SERVICE TESTS
# ============================================================================

class TestComparableServiceInit:
    """Test ComparableService initialization."""

    def test_init_with_engine(self, mock_db_engine):
        """Test initialization with SQLAlchemy Engine."""
        service = ComparableService(mock_db_engine)
        assert service.db == mock_db_engine
        assert service.config is not None

    def test_init_with_connection(self, mock_db_connection):
        """Test initialization with SQLAlchemy Connection."""
        service = ComparableService(mock_db_connection)
        assert service.db == mock_db_connection

    def test_init_with_custom_config(self, mock_db_engine):
        """Test initialization with custom configuration."""
        from src.services.comparable_service import ComparableConfig
        custom_config = ComparableConfig(
            min_comparables=10,
            max_comparables=30
        )
        service = ComparableService(mock_db_engine, config=custom_config)
        assert service.config.min_comparables == 10
        assert service.config.max_comparables == 30


class TestComparableServiceFindComparables:
    """Test ComparableService.find_comparables method."""

    def test_find_comparables_returns_results(
        self, comparable_service, sample_comparables
    ):
        """Test that find_comparables returns list of comparables."""
        # Mock database response
        mock_rows = [Mock(**comp) for comp in sample_comparables]
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows

        mock_conn = comparable_service.db.connect.return_value.__enter__.return_value
        mock_conn.execute.return_value = mock_result

        # Execute
        comparables = comparable_service.find_comparables("01-12345-000", limit=10)

        # Assert
        assert len(comparables) == 10
        assert all(isinstance(c, ComparableProperty) for c in comparables)
        assert comparables[0].parcel_id == sample_comparables[0]["parcel_id"]

    def test_find_comparables_respects_limit(
        self, comparable_service, sample_comparables
    ):
        """Test that limit parameter is respected."""
        # Mock database response with 5 comparables
        mock_rows = [Mock(**comp) for comp in sample_comparables[:5]]
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows

        mock_conn = comparable_service.db.connect.return_value.__enter__.return_value
        mock_conn.execute.return_value = mock_result

        # Execute with limit=5
        comparables = comparable_service.find_comparables("01-12345-000", limit=5)

        # Assert
        assert len(comparables) == 5
        # Verify SQL was called with correct limit
        call_args = mock_conn.execute.call_args
        assert call_args[0][1]["limit"] == 5

    def test_find_comparables_property_not_found(self, comparable_service):
        """Test PropertyNotFoundError when property doesn't exist."""
        # Mock no results from find_comparables query
        mock_result = Mock()
        mock_result.fetchall.return_value = []

        # Mock property_exists check returning False
        mock_conn = comparable_service.db.connect.return_value.__enter__.return_value
        mock_conn.execute.side_effect = [
            mock_result,  # First call: find_comparables returns empty
            Mock(fetchone=Mock(return_value=None))  # Second call: property_exists returns False
        ]

        # Execute and assert
        with pytest.raises(PropertyNotFoundError) as exc_info:
            comparable_service.find_comparables("INVALID-PARCEL")

        assert "INVALID-PARCEL" in str(exc_info.value)

    def test_find_comparables_empty_results_valid_property(
        self, comparable_service
    ):
        """Test empty list returned when valid property has no comparables."""
        # Mock no results but property exists
        mock_result = Mock()
        mock_result.fetchall.return_value = []

        mock_conn = comparable_service.db.connect.return_value.__enter__.return_value
        mock_conn.execute.side_effect = [
            mock_result,  # find_comparables returns empty
            Mock(fetchone=Mock(return_value=Mock()))  # property_exists returns True
        ]

        # Execute
        comparables = comparable_service.find_comparables("01-ISOLATED-000")

        # Assert - should return empty list, not raise error
        assert comparables == []

    def test_find_comparables_invalid_limit_raises_error(self, comparable_service):
        """Test ValueError for invalid limit values."""
        with pytest.raises(ValueError, match="limit must be between 1 and 50"):
            comparable_service.find_comparables("01-12345-000", limit=0)

        with pytest.raises(ValueError, match="limit must be between 1 and 50"):
            comparable_service.find_comparables("01-12345-000", limit=51)

    def test_similarity_scoring_calculation(
        self, comparable_service, sample_comparables
    ):
        """Test that similarity scores are properly calculated."""
        mock_rows = [Mock(**sample_comparables[0])]
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows

        mock_conn = comparable_service.db.connect.return_value.__enter__.return_value
        mock_conn.execute.return_value = mock_result

        comparables = comparable_service.find_comparables("01-12345-000", limit=1)

        comp = comparables[0]
        assert comp.similarity_score == sample_comparables[0]["similarity_score"]
        assert comp.type_match_score == 100.0
        assert comp.value_match_score == sample_comparables[0]["value_match_score"]

    def test_subdivision_matching_priority(
        self, comparable_service, sample_comparables
    ):
        """Test that subdivision matches are prioritized."""
        # Filter to only subdivision matches
        subdivision_comps = [
            c for c in sample_comparables if c["match_type"] == "SUBDIVISION"
        ]
        mock_rows = [Mock(**comp) for comp in subdivision_comps]
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows

        mock_conn = comparable_service.db.connect.return_value.__enter__.return_value
        mock_conn.execute.return_value = mock_result

        comparables = comparable_service.find_comparables("01-12345-000")

        # All should be subdivision matches
        assert all(c.match_type == "SUBDIVISION" for c in comparables)
        assert all(c.distance_miles == 0.0 for c in comparables)


class TestPropertyCriteriaValidation:
    """Test PropertyCriteria validation."""

    def test_valid_criteria_passes(self, sample_criteria):
        """Test that valid criteria passes validation."""
        sample_criteria.validate()  # Should not raise

    def test_negative_value_raises_error(self, invalid_criteria_negative_value):
        """Test that negative total value raises ValueError."""
        with pytest.raises(ValueError, match="total_val_cents must be positive"):
            invalid_criteria_negative_value.validate()

    def test_zero_acreage_raises_error(self, invalid_criteria_zero_acreage):
        """Test that zero acreage raises ValueError."""
        with pytest.raises(ValueError, match="acreage must be positive"):
            invalid_criteria_zero_acreage.validate()

    def test_empty_property_type_raises_error(self, invalid_criteria_empty_type):
        """Test that empty property type raises ValueError."""
        with pytest.raises(ValueError, match="property_type cannot be empty"):
            invalid_criteria_empty_type.validate()

    def test_invalid_coordinates_raise_error(self, invalid_criteria_bad_coordinates):
        """Test that invalid coordinates raise ValueError."""
        with pytest.raises(ValueError, match="latitude must be between"):
            invalid_criteria_bad_coordinates.validate()


# ============================================================================
# FAIRNESS SCORER TESTS
# ============================================================================

class TestFairnessScorer:
    """Test FairnessScorer calculations."""

    def test_fairly_assessed_property(self, fairness_scorer):
        """Test property with ratio equal to median (fairly assessed)."""
        comparable_ratios = [0.18, 0.19, 0.20, 0.20, 0.21, 0.22]
        subject_ratio = 0.20  # Equal to median

        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=subject_ratio,
            comparable_ratios=comparable_ratios
        )

        assert result is not None
        assert 21 <= result.fairness_score <= 40  # Fair range
        assert result.interpretation == "FAIR"
        assert result.subject_ratio == 0.20
        assert result.median_ratio == 0.20
        assert abs(result.z_score) < 0.5  # Close to median

    def test_over_assessed_property(self, fairness_scorer):
        """Test property with ratio significantly above median."""
        comparable_ratios = [0.18, 0.19, 0.20, 0.20, 0.21, 0.22]
        median = statistics.median(comparable_ratios)
        subject_ratio = median * 1.3  # 30% above median

        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=subject_ratio,
            comparable_ratios=comparable_ratios
        )

        assert result is not None
        assert result.fairness_score >= 41  # Over-assessed range
        assert result.interpretation == "OVER_ASSESSED"
        assert result.z_score > 0  # Above median

    def test_under_assessed_property(self, fairness_scorer):
        """Test property with ratio significantly below median."""
        comparable_ratios = [0.18, 0.19, 0.20, 0.20, 0.21, 0.22]
        median = statistics.median(comparable_ratios)
        subject_ratio = median * 0.7  # 30% below median

        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=subject_ratio,
            comparable_ratios=comparable_ratios
        )

        assert result is not None
        assert result.fairness_score <= 20  # Under-assessed range
        assert result.interpretation == "UNDER_ASSESSED"
        assert result.z_score < 0  # Below median

    def test_confidence_with_many_comparables(self, fairness_scorer):
        """Test that confidence is high with many consistent comparables."""
        # 20 comparables with low variance
        comparable_ratios = [0.20] * 15 + [0.19, 0.19, 0.21, 0.21, 0.20]
        subject_ratio = 0.25

        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=subject_ratio,
            comparable_ratios=comparable_ratios
        )

        assert result is not None
        assert result.confidence >= 70  # High confidence
        assert result.comparable_count == 20

    def test_confidence_with_few_comparables(self, fairness_scorer):
        """Test that confidence is lower with few comparables."""
        # Only 3 comparables
        comparable_ratios = [0.18, 0.20, 0.22]
        subject_ratio = 0.25

        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=subject_ratio,
            comparable_ratios=comparable_ratios
        )

        assert result is not None
        assert result.confidence <= 55  # Low confidence with <3 comparables
        assert result.comparable_count == 3

    def test_edge_case_no_comparables(self, fairness_scorer):
        """Test that None is returned when no comparables provided."""
        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.20,
            comparable_ratios=[]
        )

        assert result is None

    def test_edge_case_zero_subject_ratio(self, fairness_scorer):
        """Test that None is returned for zero subject ratio."""
        comparable_ratios = [0.18, 0.19, 0.20, 0.21, 0.22]

        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.0,
            comparable_ratios=comparable_ratios
        )

        assert result is None

    def test_edge_case_all_invalid_comparables(self, fairness_scorer):
        """Test handling of all invalid comparable ratios."""
        comparable_ratios = [0.0, -0.1, 0.0, -0.5]  # All invalid

        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.20,
            comparable_ratios=comparable_ratios
        )

        assert result is None

    def test_z_score_to_fairness_conversion(self, fairness_scorer):
        """Test z-score to fairness score conversion formula."""
        comparable_ratios = [0.20] * 10
        std_dev = 0.01  # Small std dev

        # Test z=0 (at median) should give fairness around 30
        result_median = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.20,
            comparable_ratios=comparable_ratios
        )
        assert 25 <= result_median.fairness_score <= 35

        # Test z≈+2 (2 std devs above) should give fairness around 80
        result_high = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.22,  # 2 std devs above if std=0.01
            comparable_ratios=comparable_ratios
        )
        assert result_high.fairness_score >= 60

    def test_percentile_calculation(self, fairness_scorer):
        """Test percentile calculation accuracy."""
        comparable_ratios = [0.10, 0.15, 0.20, 0.25, 0.30]

        # Subject at 50th percentile (median)
        result_50th = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.20,
            comparable_ratios=comparable_ratios
        )
        assert 40 <= result_50th.percentile <= 60

        # Subject at high percentile
        result_90th = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.28,
            comparable_ratios=comparable_ratios
        )
        assert result_90th.percentile >= 80

    def test_fairness_result_to_dict(self, fairness_scorer):
        """Test FairnessResult to_dict serialization."""
        comparable_ratios = [0.18, 0.19, 0.20, 0.21, 0.22]
        subject_ratio = 0.20

        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=subject_ratio,
            comparable_ratios=comparable_ratios
        )

        result_dict = result.to_dict()

        assert "fairness_score" in result_dict
        assert "subject_ratio" in result_dict
        assert "median_ratio" in result_dict
        assert "confidence" in result_dict
        assert "interpretation" in result_dict
        assert isinstance(result_dict["fairness_score"], int)

    def test_get_recommendation(self, fairness_scorer):
        """Test recommendation generation based on fairness score."""
        comparable_ratios = [0.20] * 5

        # Test strong appeal case (score >= 81)
        result_strong = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.30,
            comparable_ratios=comparable_ratios
        )
        if result_strong.fairness_score >= 81:
            assert result_strong.get_recommendation() == "STRONG_APPEAL_RECOMMENDED"

        # Test moderate appeal case (score 61-80)
        result_moderate = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.24,
            comparable_ratios=comparable_ratios
        )
        if 61 <= result_moderate.fairness_score < 81:
            assert result_moderate.get_recommendation() == "APPEAL_RECOMMENDED"

        # Test monitor case (score 41-60)
        result_monitor = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.22,
            comparable_ratios=comparable_ratios
        )
        if 41 <= result_monitor.fairness_score < 61:
            assert result_monitor.get_recommendation() == "MONITOR"

        # Test no action case (score 21-40)
        result_fair = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.20,
            comparable_ratios=comparable_ratios
        )
        if 21 <= result_fair.fairness_score <= 40:
            assert result_fair.get_recommendation() == "NO_ACTION_NEEDED"


# ============================================================================
# SAVINGS ESTIMATOR TESTS
# ============================================================================

class TestSavingsEstimator:
    """Test SavingsEstimator calculations."""

    def test_basic_savings_calculation(self, savings_estimator):
        """Test basic tax savings calculation."""
        savings = savings_estimator.estimate_savings(
            current_assessed_cents=5000000,  # $50,000
            target_assessed_cents=4500000,   # $45,000
            mill_rate=65.0
        )

        assert savings.reduction_cents == 500000  # $5,000
        assert savings.reduction_percent == 10.0
        # Tax savings: $5,000 * 0.065 = $325
        assert savings.annual_savings_cents == 32500
        # 5-year: $325 * 5 = $1,625
        assert savings.five_year_savings_cents == 162500

    def test_no_savings_when_target_higher(self, savings_estimator):
        """Test zero savings when target is higher than current."""
        savings = savings_estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=5500000,
            mill_rate=65.0
        )

        assert savings.reduction_cents == 0
        assert savings.annual_savings_cents == 0
        assert savings.five_year_savings_cents == 0
        assert savings.is_worthwhile is False

    def test_five_year_projection(self, savings_estimator):
        """Test 5-year savings projection accuracy."""
        savings = savings_estimator.estimate_savings(
            current_assessed_cents=10000000,  # $100,000
            target_assessed_cents=8000000,    # $80,000
            mill_rate=70.0
        )

        # Annual: $20,000 * 0.070 = $1,400
        assert savings.annual_savings_cents == 140000
        # 5-year: $1,400 * 5 = $7,000
        assert savings.five_year_savings_cents == 700000

    def test_custom_mill_rate(self, savings_estimator):
        """Test savings with custom mill rate."""
        reduction = 500000  # $5,000

        savings_50 = savings_estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            mill_rate=50.0
        )

        savings_80 = savings_estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            mill_rate=80.0
        )

        # $5,000 * 0.050 = $250
        assert savings_50.annual_savings_cents == 25000
        # $5,000 * 0.080 = $400
        assert savings_80.annual_savings_cents == 40000

    def test_zero_assessment_edge_case(self, savings_estimator):
        """Test handling of zero assessment values."""
        savings = savings_estimator.estimate_savings(
            current_assessed_cents=0,
            target_assessed_cents=0,
            mill_rate=65.0
        )

        assert savings.reduction_cents == 0
        assert savings.reduction_percent == 0.0
        assert savings.annual_savings_cents == 0

    def test_estimate_from_fairness(self, savings_estimator):
        """Test savings calculation from fairness ratio."""
        # Property at 25% should be 20%
        savings = savings_estimator.estimate_from_fairness(
            current_assessed_cents=6250000,   # $62,500 (25%)
            current_total_cents=25000000,     # $250,000
            target_ratio=0.20
        )

        # Target: $250,000 * 0.20 = $50,000
        assert savings.target_assessed_cents == 5000000
        assert savings.reduction_cents == 1250000  # $12,500

    def test_is_worthwhile_threshold(self, savings_estimator):
        """Test is_worthwhile threshold at $100/year."""
        # Exactly $100/year
        savings_100 = savings_estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=4846154,  # Calculated to give exactly $100 savings
            mill_rate=65.0
        )
        assert savings_100.annual_savings_cents >= 10000  # At least $100

        # Just under $100/year
        savings_99 = savings_estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=4984769,
            mill_rate=65.0
        )
        assert savings_99.is_worthwhile is False


# ============================================================================
# ASSESSMENT ANALYZER INTEGRATION TESTS
# ============================================================================

class TestAssessmentAnalyzer:
    """Test AssessmentAnalyzer orchestration."""

    def test_full_analysis_workflow(
        self, assessment_analyzer, sample_property, sample_comparables
    ):
        """Test complete analysis workflow with mocked services."""
        # Mock property data retrieval
        mock_conn = assessment_analyzer.db.connect.return_value.__enter__.return_value

        # Mock property lookup
        property_row = Mock(
            id=sample_property["id"],
            parcel_id=sample_property["parcel_id"],
            address=sample_property["address"],
            total_val_cents=sample_property["total_val_cents"],
            assess_val_cents=sample_property["assess_val_cents"],
            owner_name=sample_property["owner_name"]
        )

        # Mock comparables lookup
        comp_rows = [Mock(**comp) for comp in sample_comparables]
        comp_result = Mock()
        comp_result.fetchall.return_value = comp_rows

        mock_conn.execute.side_effect = [
            Mock(fetchone=Mock(return_value=property_row)),  # Property lookup
            comp_result  # Comparables lookup
        ]

        # Execute analysis
        analysis = assessment_analyzer.analyze_property(sample_property["parcel_id"])

        # Assert
        assert analysis is not None
        assert analysis.parcel_id == sample_property["parcel_id"]
        assert analysis.comparable_count == len(sample_comparables)
        assert analysis.fairness_score >= 0
        assert analysis.confidence >= 0
        assert analysis.recommended_action in ["APPEAL", "MONITOR", "NONE"]

    def test_recommendation_strong_appeal(
        self, assessment_analyzer, over_assessed_property, sample_comparables
    ):
        """Test strong appeal recommendation for severely over-assessed property."""
        # Mock property data with high assessment ratio
        mock_conn = assessment_analyzer.db.connect.return_value.__enter__.return_value

        property_row = Mock(
            id=over_assessed_property["id"],
            parcel_id=over_assessed_property["parcel_id"],
            address=over_assessed_property["address"],
            total_val_cents=over_assessed_property["total_val_cents"],
            assess_val_cents=over_assessed_property["assess_val_cents"],
            owner_name=over_assessed_property["owner_name"]
        )

        comp_rows = [Mock(**comp) for comp in sample_comparables]
        comp_result = Mock()
        comp_result.fetchall.return_value = comp_rows

        mock_conn.execute.side_effect = [
            Mock(fetchone=Mock(return_value=property_row)),
            comp_result
        ]

        analysis = assessment_analyzer.analyze_property(
            over_assessed_property["parcel_id"]
        )

        # Over-assessed property at 25% vs comparables at ~20%
        # Should trigger appeal recommendation
        if analysis.fairness_score >= 70:
            assert analysis.recommended_action == "APPEAL"
            assert analysis.appeal_strength in ["STRONG", "MODERATE"]

    def test_recommendation_moderate_appeal(self, assessment_analyzer):
        """Test moderate appeal recommendation."""
        # This is tested implicitly through the recommendation logic
        # A property with fairness_score 60-69 should get MODERATE appeal
        recommendation, strength = assessment_analyzer._determine_recommendation(
            fairness_score=65,
            confidence=70,
            savings_cents=30000  # $300/year
        )

        assert recommendation == "APPEAL"
        assert strength == "MODERATE"

    def test_recommendation_monitor(self, assessment_analyzer):
        """Test monitor recommendation."""
        recommendation, strength = assessment_analyzer._determine_recommendation(
            fairness_score=55,
            confidence=60,
            savings_cents=15000  # $150/year
        )

        assert recommendation == "MONITOR"
        assert strength == "WEAK"

    def test_recommendation_none(self, assessment_analyzer):
        """Test no action recommendation for fairly assessed property."""
        recommendation, strength = assessment_analyzer._determine_recommendation(
            fairness_score=30,
            confidence=80,
            savings_cents=5000  # $50/year
        )

        assert recommendation == "NONE"
        assert strength is None

    def test_batch_analysis(
        self, assessment_analyzer, sample_property, over_assessed_property
    ):
        """Test batch analysis of multiple properties."""
        property_ids = [
            sample_property["parcel_id"],
            over_assessed_property["parcel_id"]
        ]

        # Mock database responses
        mock_conn = assessment_analyzer.db.connect.return_value.__enter__.return_value

        # Create alternating responses for each property analysis
        property_responses = []
        for prop in [sample_property, over_assessed_property]:
            property_row = Mock(
                id=prop["id"],
                parcel_id=prop["parcel_id"],
                address=prop["address"],
                total_val_cents=prop["total_val_cents"],
                assess_val_cents=prop["assess_val_cents"],
                owner_name=prop["owner_name"]
            )
            property_responses.append(Mock(fetchone=Mock(return_value=property_row)))

            # Add mock comparables for each
            comp_result = Mock()
            comp_result.fetchall.return_value = []  # Empty for simplicity
            property_responses.append(comp_result)

        mock_conn.execute.side_effect = property_responses

        # Execute batch analysis
        analyses = assessment_analyzer.analyze_batch(property_ids)

        # Should return list (may be empty if no comparables)
        assert isinstance(analyses, list)

    def test_analysis_to_dict(
        self, assessment_analyzer, sample_property, sample_comparables
    ):
        """Test AssessmentAnalysis serialization to dict."""
        # Create a mock analysis
        analysis = AssessmentAnalysis(
            property_id=sample_property["id"],
            parcel_id=sample_property["parcel_id"],
            address=sample_property["address"],
            total_val_cents=sample_property["total_val_cents"],
            assess_val_cents=sample_property["assess_val_cents"],
            current_ratio=0.20,
            fairness_score=30,
            confidence=85,
            interpretation="FAIR",
            comparable_count=10,
            median_comparable_ratio=0.20,
            estimated_annual_savings_cents=0,
            estimated_five_year_savings_cents=0,
            recommended_action="NONE",
            appeal_strength=None,
            analysis_date=datetime.now(),
            model_version="1.0.0"
        )

        result_dict = analysis.to_dict()

        assert "property_id" in result_dict
        assert "fairness_score" in result_dict
        assert "recommended_action" in result_dict
        assert result_dict["fairness_score"] == 30
        assert result_dict["interpretation"] == "FAIR"

    def test_analysis_invalid_property(self, assessment_analyzer):
        """Test analysis with invalid property ID."""
        mock_conn = assessment_analyzer.db.connect.return_value.__enter__.return_value
        mock_conn.execute.return_value = Mock(fetchone=Mock(return_value=None))

        with pytest.raises(PropertyNotFoundError):
            assessment_analyzer.analyze_property("INVALID-ID")

    def test_analysis_property_zero_values(self, assessment_analyzer):
        """Test analysis with property having zero assessment values."""
        mock_conn = assessment_analyzer.db.connect.return_value.__enter__.return_value

        property_row = Mock(
            id="test-id",
            parcel_id="01-00000-000",
            address="Test Address",
            total_val_cents=0,
            assess_val_cents=0,
            owner_name="Test Owner"
        )

        mock_conn.execute.return_value = Mock(fetchone=Mock(return_value=property_row))

        result = assessment_analyzer.analyze_property("01-00000-000")

        # Should return None for invalid data
        assert result is None


# ============================================================================
# INTEGRATION TESTS (require real database)
# ============================================================================

@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests that connect to real database."""

    def test_real_comparable_lookup(self, db_engine):
        """Test finding comparables with real database connection."""
        service = ComparableService(db_engine)

        # Get a valid property ID from the database
        with db_engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("""
                SELECT parcel_id
                FROM properties
                WHERE assess_val_cents > 0
                    AND total_val_cents > 0
                    AND is_active = true
                LIMIT 1
            """))
            row = result.fetchone()

            if row:
                property_id = row.parcel_id

                # Find comparables
                comparables = service.find_comparables(property_id, limit=5)

                # Basic assertions
                assert isinstance(comparables, list)
                assert all(isinstance(c, ComparableProperty) for c in comparables)

                # If comparables found, verify structure
                if comparables:
                    comp = comparables[0]
                    assert comp.parcel_id is not None
                    assert comp.similarity_score >= 0
                    assert comp.assessment_ratio > 0

    def test_real_full_analysis(self, db_engine):
        """Test full analysis workflow with real database."""
        analyzer = AssessmentAnalyzer(db_engine, default_mill_rate=65.0)

        # Get a valid property ID
        with db_engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("""
                SELECT parcel_id
                FROM properties
                WHERE assess_val_cents > 0
                    AND total_val_cents > 0
                    AND is_active = true
                ORDER BY total_val_cents DESC
                LIMIT 1
            """))
            row = result.fetchone()

            if row:
                property_id = row.parcel_id

                # Run analysis
                analysis = analyzer.analyze_property(property_id)

                # Verify results
                if analysis:  # May be None if no comparables
                    assert analysis.property_id is not None
                    assert analysis.fairness_score >= 0
                    assert analysis.confidence >= 0
                    assert analysis.comparable_count >= 0
                    assert analysis.recommended_action in ["APPEAL", "MONITOR", "NONE"]


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_comparable_service_database_error(self, comparable_service):
        """Test handling of database errors."""
        from sqlalchemy.exc import SQLAlchemyError

        mock_conn = comparable_service.db.connect.return_value.__enter__.return_value
        mock_conn.execute.side_effect = SQLAlchemyError("Database connection failed")

        with pytest.raises(DatabaseError):
            comparable_service.find_comparables("01-12345-000")

    def test_fairness_scorer_single_comparable(self, fairness_scorer):
        """Test fairness scoring with only one comparable."""
        result = fairness_scorer.calculate_fairness_score(
            subject_ratio=0.25,
            comparable_ratios=[0.20]
        )

        assert result is not None
        # Should use default std dev
        assert result.comparable_count == 1
        assert result.confidence <= 50  # Low confidence

    def test_savings_estimator_fractional_cents(self, savings_estimator):
        """Test savings calculation with fractional cent precision."""
        savings = savings_estimator.estimate_savings(
            current_assessed_cents=5000033,  # $50,000.33
            target_assessed_cents=4500017,   # $45,000.17
            mill_rate=65.0
        )

        # Should handle cents precisely
        assert savings.reduction_cents == 500016
        assert savings.reduction_dollars == 5000.16

    def test_assessment_analyzer_no_comparables(self, assessment_analyzer):
        """Test analysis when no comparables are found."""
        mock_conn = assessment_analyzer.db.connect.return_value.__enter__.return_value

        property_row = Mock(
            id="test-id",
            parcel_id="01-ISOLATED-000",
            address="Isolated Property",
            total_val_cents=25000000,
            assess_val_cents=5000000,
            owner_name="Test Owner"
        )

        # Mock empty comparables result
        mock_conn.execute.side_effect = [
            Mock(fetchone=Mock(return_value=property_row)),
            Mock(fetchall=Mock(return_value=[]))  # No comparables
        ]

        result = assessment_analyzer.analyze_property("01-ISOLATED-000")

        # Should return None when no comparables
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
