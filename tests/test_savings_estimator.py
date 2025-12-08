"""
Unit tests for the SavingsEstimator service.

Tests cover:
- Standard savings calculations
- Fairness ratio calculations
- Edge cases (zero values, no savings, etc.)
- Error handling and validation
- Different mill rates
- Precision with cent-based calculations
"""

import pytest
from src.services.savings_estimator import SavingsEstimator, SavingsEstimate


class TestSavingsEstimatorInit:
    """Test SavingsEstimator initialization."""

    def test_default_mill_rate(self):
        """Test initialization with default mill rate."""
        estimator = SavingsEstimator()
        assert estimator.default_mill_rate == 65.0

    def test_custom_mill_rate(self):
        """Test initialization with custom mill rate."""
        estimator = SavingsEstimator(default_mill_rate=70.5)
        assert estimator.default_mill_rate == 70.5

    def test_negative_mill_rate_raises_error(self):
        """Test that negative mill rate raises ValueError."""
        with pytest.raises(ValueError, match="Mill rate must be positive"):
            SavingsEstimator(default_mill_rate=-10.0)

    def test_zero_mill_rate_raises_error(self):
        """Test that zero mill rate raises ValueError."""
        with pytest.raises(ValueError, match="Mill rate must be positive"):
            SavingsEstimator(default_mill_rate=0.0)


class TestEstimateSavings:
    """Test the estimate_savings method."""

    def test_standard_calculation(self):
        """Test basic savings calculation with clear reduction."""
        estimator = SavingsEstimator(default_mill_rate=65.0)
        savings = estimator.estimate_savings(
            current_assessed_cents=5000000,  # $50,000
            target_assessed_cents=4500000,   # $45,000
            mill_rate=65.0
        )

        assert savings.current_assessed_cents == 5000000
        assert savings.target_assessed_cents == 4500000
        assert savings.reduction_cents == 500000  # $5,000
        assert savings.reduction_percent == 10.0
        assert savings.annual_savings_cents == 32500  # $325
        assert savings.five_year_savings_cents == 162500  # $1,625
        assert savings.mill_rate_used == 65.0
        assert savings.is_worthwhile is True

    def test_uses_default_mill_rate_when_none(self):
        """Test that default mill rate is used when none is provided."""
        estimator = SavingsEstimator(default_mill_rate=70.0)
        savings = estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000
        )

        assert savings.mill_rate_used == 70.0

    def test_no_savings_when_target_equals_current(self):
        """Test that no savings are calculated when target equals current."""
        estimator = SavingsEstimator()
        savings = estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=5000000
        )

        assert savings.reduction_cents == 0
        assert savings.annual_savings_cents == 0
        assert savings.five_year_savings_cents == 0
        assert savings.is_worthwhile is False

    def test_no_savings_when_target_greater_than_current(self):
        """Test that no savings when target is greater than current."""
        estimator = SavingsEstimator()
        savings = estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=6000000
        )

        assert savings.reduction_cents == 0
        assert savings.annual_savings_cents == 0
        assert savings.five_year_savings_cents == 0
        assert savings.is_worthwhile is False

    def test_small_reduction_not_worthwhile(self):
        """Test that small reductions are flagged as not worthwhile."""
        estimator = SavingsEstimator(default_mill_rate=65.0)
        savings = estimator.estimate_savings(
            current_assessed_cents=5000000,  # $50,000
            target_assessed_cents=4980000,   # $49,800 (only $200 reduction)
        )

        # Annual savings: $200 * 0.065 = $13
        assert savings.annual_savings_cents == 1300
        assert savings.is_worthwhile is False  # Less than $100/year

    def test_large_reduction_worthwhile(self):
        """Test that large reductions are flagged as worthwhile."""
        estimator = SavingsEstimator(default_mill_rate=70.0)
        savings = estimator.estimate_savings(
            current_assessed_cents=10000000,  # $100,000
            target_assessed_cents=8000000,    # $80,000
        )

        # Annual savings: $20,000 * 0.070 = $1,400
        assert savings.annual_savings_cents == 140000
        assert savings.is_worthwhile is True

    def test_different_mill_rates(self):
        """Test that different mill rates produce different savings."""
        estimator = SavingsEstimator()

        savings_50 = estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            mill_rate=50.0
        )

        savings_80 = estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            mill_rate=80.0
        )

        # $5,000 reduction
        # At 50 mills: $5,000 * 0.050 = $250
        # At 80 mills: $5,000 * 0.080 = $400
        assert savings_50.annual_savings_cents == 25000
        assert savings_80.annual_savings_cents == 40000

    def test_zero_current_assessed(self):
        """Test behavior with zero current assessed value."""
        estimator = SavingsEstimator()
        savings = estimator.estimate_savings(
            current_assessed_cents=0,
            target_assessed_cents=0
        )

        assert savings.reduction_cents == 0
        assert savings.reduction_percent == 0.0
        assert savings.annual_savings_cents == 0

    def test_negative_assessed_raises_error(self):
        """Test that negative assessed values raise ValueError."""
        estimator = SavingsEstimator()

        with pytest.raises(ValueError, match="Assessed values must be non-negative"):
            estimator.estimate_savings(
                current_assessed_cents=-1000,
                target_assessed_cents=5000000
            )

        with pytest.raises(ValueError, match="Assessed values must be non-negative"):
            estimator.estimate_savings(
                current_assessed_cents=5000000,
                target_assessed_cents=-1000
            )

    def test_negative_mill_rate_raises_error(self):
        """Test that negative mill rate raises ValueError."""
        estimator = SavingsEstimator()

        with pytest.raises(ValueError, match="Mill rate must be positive"):
            estimator.estimate_savings(
                current_assessed_cents=5000000,
                target_assessed_cents=4500000,
                mill_rate=-10.0
            )

    def test_precision_with_cents(self):
        """Test that cent-based calculations maintain precision."""
        estimator = SavingsEstimator(default_mill_rate=65.0)

        # Test with odd cent values that could cause rounding issues
        savings = estimator.estimate_savings(
            current_assessed_cents=5000033,  # $50,000.33
            target_assessed_cents=4500017,   # $45,000.17
        )

        # Reduction: $50,000.33 - $45,000.17 = $50,000.16 = 50,001,600 cents
        assert savings.reduction_cents == 500016
        # Check that we can convert back to dollars cleanly
        assert savings.reduction_dollars == 5000.16


class TestEstimateFromFairness:
    """Test the estimate_from_fairness method."""

    def test_basic_fairness_calculation(self):
        """Test basic fairness ratio calculation."""
        estimator = SavingsEstimator(default_mill_rate=65.0)

        # Property assessed at 25% but should be 20%
        savings = estimator.estimate_from_fairness(
            current_assessed_cents=6250000,   # $62,500 (25%)
            current_total_cents=25000000,     # $250,000
            target_ratio=0.20                  # Should be 20%
        )

        # Target should be $250,000 * 0.20 = $50,000
        assert savings.target_assessed_cents == 5000000
        assert savings.current_assessed_cents == 6250000
        assert savings.reduction_cents == 1250000  # $12,500
        assert savings.reduction_percent == 20.0

    def test_fairness_with_statutory_ratio(self):
        """Test with Arkansas statutory ratio of 20%."""
        estimator = SavingsEstimator(default_mill_rate=65.0)

        savings = estimator.estimate_from_fairness(
            current_assessed_cents=7500000,   # $75,000 (30%)
            current_total_cents=25000000,     # $250,000
            target_ratio=0.20                  # Statutory 20%
        )

        # Target: $250,000 * 0.20 = $50,000
        assert savings.target_assessed_cents == 5000000
        assert savings.reduction_cents == 2500000  # $25,000

    def test_fairness_no_reduction_needed(self):
        """Test when property is already fairly assessed."""
        estimator = SavingsEstimator()

        # Already at 20%
        savings = estimator.estimate_from_fairness(
            current_assessed_cents=5000000,   # $50,000 (20%)
            current_total_cents=25000000,     # $250,000
            target_ratio=0.20
        )

        # No reduction needed
        assert savings.reduction_cents == 0
        assert savings.annual_savings_cents == 0

    def test_fairness_negative_values_raise_error(self):
        """Test that negative values raise ValueError."""
        estimator = SavingsEstimator()

        with pytest.raises(ValueError, match="Values must be non-negative"):
            estimator.estimate_from_fairness(
                current_assessed_cents=-5000000,
                current_total_cents=25000000,
                target_ratio=0.20
            )

    def test_fairness_invalid_ratio_raises_error(self):
        """Test that invalid ratios raise ValueError."""
        estimator = SavingsEstimator()

        with pytest.raises(ValueError, match="Target ratio must be between 0 and 1"):
            estimator.estimate_from_fairness(
                current_assessed_cents=5000000,
                current_total_cents=25000000,
                target_ratio=1.5
            )

        with pytest.raises(ValueError, match="Target ratio must be between 0 and 1"):
            estimator.estimate_from_fairness(
                current_assessed_cents=5000000,
                current_total_cents=25000000,
                target_ratio=-0.1
            )

    def test_fairness_zero_total_raises_error(self):
        """Test that zero total value raises ValueError."""
        estimator = SavingsEstimator()

        with pytest.raises(ValueError, match="Current total value cannot be zero"):
            estimator.estimate_from_fairness(
                current_assessed_cents=5000000,
                current_total_cents=0,
                target_ratio=0.20
            )


class TestGetMillRateForProperty:
    """Test the get_mill_rate_for_property stub method."""

    def test_returns_default_mill_rate(self):
        """Test that stub returns default mill rate."""
        estimator = SavingsEstimator(default_mill_rate=72.5)
        mill_rate = estimator.get_mill_rate_for_property("PROP-123")

        assert mill_rate == 72.5

    def test_accepts_any_property_id(self):
        """Test that method accepts any property ID string."""
        estimator = SavingsEstimator()

        assert estimator.get_mill_rate_for_property("ABC123") == 65.0
        assert estimator.get_mill_rate_for_property("XYZ999") == 65.0
        assert estimator.get_mill_rate_for_property("") == 65.0


class TestSavingsEstimateDataclass:
    """Test the SavingsEstimate dataclass properties and methods."""

    def test_dollar_properties(self):
        """Test that dollar conversion properties work correctly."""
        estimate = SavingsEstimate(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            reduction_cents=500000,
            reduction_percent=10.0,
            current_annual_tax_cents=32500,
            target_annual_tax_cents=29250,
            annual_savings_cents=3250,
            five_year_savings_cents=16250,
            mill_rate_used=65.0
        )

        assert estimate.annual_savings_dollars == 32.50
        assert estimate.five_year_savings_dollars == 162.50
        assert estimate.reduction_dollars == 5000.00
        assert estimate.current_assessed_dollars == 50000.00
        assert estimate.target_assessed_dollars == 45000.00

    def test_is_worthwhile_true(self):
        """Test is_worthwhile returns True for savings >= $100."""
        estimate = SavingsEstimate(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            reduction_cents=500000,
            reduction_percent=10.0,
            current_annual_tax_cents=32500,
            target_annual_tax_cents=29250,
            annual_savings_cents=10000,  # Exactly $100
            five_year_savings_cents=50000,
            mill_rate_used=65.0
        )

        assert estimate.is_worthwhile is True

    def test_is_worthwhile_false(self):
        """Test is_worthwhile returns False for savings < $100."""
        estimate = SavingsEstimate(
            current_assessed_cents=5000000,
            target_assessed_cents=4980000,
            reduction_cents=20000,
            reduction_percent=0.4,
            current_annual_tax_cents=32500,
            target_annual_tax_cents=32370,
            annual_savings_cents=9999,  # Just under $100
            five_year_savings_cents=49995,
            mill_rate_used=65.0
        )

        assert estimate.is_worthwhile is False

    def test_to_dict(self):
        """Test to_dict conversion."""
        estimate = SavingsEstimate(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            reduction_cents=500000,
            reduction_percent=10.0,
            current_annual_tax_cents=32500,
            target_annual_tax_cents=29250,
            annual_savings_cents=3250,
            five_year_savings_cents=16250,
            mill_rate_used=65.0
        )

        result = estimate.to_dict()

        assert result["current_assessed"] == 50000.0
        assert result["target_assessed"] == 45000.0
        assert result["reduction"] == 5000.0
        assert result["reduction_percent"] == 10.0
        assert result["current_annual_tax"] == 325.0
        assert result["target_annual_tax"] == 292.5
        assert result["annual_savings"] == 32.5
        assert result["five_year_savings"] == 162.5
        assert result["mill_rate"] == 65.0
        assert result["is_worthwhile"] is False  # $32.50 < $100

    def test_str_representation(self):
        """Test string representation is human-readable."""
        estimate = SavingsEstimate(
            current_assessed_cents=5000000,
            target_assessed_cents=4500000,
            reduction_cents=500000,
            reduction_percent=10.0,
            current_annual_tax_cents=32500,
            target_annual_tax_cents=29250,
            annual_savings_cents=32500,
            five_year_savings_cents=162500,
            mill_rate_used=65.0
        )

        str_repr = str(estimate)

        assert "Current Assessed: $50,000.00" in str_repr
        assert "Target Assessed: $45,000.00" in str_repr
        assert "Reduction: $5,000.00" in str_repr
        assert "10.0%" in str_repr
        assert "Annual Tax Savings: $325.00" in str_repr
        assert "5-Year Savings: $1,625.00" in str_repr
        assert "Mill Rate: 65.00" in str_repr


class TestTaxCalculationAccuracy:
    """Test that tax calculations match Arkansas formula."""

    def test_mill_rate_formula(self):
        """
        Test that tax calculation follows the correct formula.

        Formula: tax = assessed_value × (mill_rate / 1000)
        """
        estimator = SavingsEstimator()

        # $50,000 assessed at 65 mills
        # Tax = $50,000 × (65 / 1000) = $50,000 × 0.065 = $3,250
        savings = estimator.estimate_savings(
            current_assessed_cents=5000000,
            target_assessed_cents=5000000,  # Same, to check current tax only
            mill_rate=65.0
        )

        assert savings.current_annual_tax_cents == 325000  # $3,250

    def test_various_mill_rates(self):
        """Test tax calculation with various mill rates."""
        estimator = SavingsEstimator()
        assessed = 10000000  # $100,000

        test_cases = [
            (50.0, 500000),   # 50 mills → $5,000
            (65.0, 650000),   # 65 mills → $6,500
            (70.0, 700000),   # 70 mills → $7,000
            (80.0, 800000),   # 80 mills → $8,000
            (100.0, 1000000), # 100 mills → $10,000
        ]

        for mill_rate, expected_tax_cents in test_cases:
            savings = estimator.estimate_savings(
                current_assessed_cents=assessed,
                target_assessed_cents=assessed,
                mill_rate=mill_rate
            )
            assert savings.current_annual_tax_cents == expected_tax_cents

    def test_fractional_mill_rates(self):
        """Test that fractional mill rates work correctly."""
        estimator = SavingsEstimator()

        savings = estimator.estimate_savings(
            current_assessed_cents=5000000,  # $50,000
            target_assessed_cents=5000000,
            mill_rate=65.75  # Fractional mill rate
        )

        # $50,000 × 0.06575 = $3,287.50
        assert savings.current_annual_tax_cents == 328750


class TestRealWorldScenarios:
    """Test realistic property tax appeal scenarios."""

    def test_overassessed_property(self):
        """Test typical overassessment scenario."""
        estimator = SavingsEstimator(default_mill_rate=68.5)

        # Property market value: $350,000
        # Should be assessed at 20%: $70,000
        # Currently assessed at 23%: $80,500
        savings = estimator.estimate_from_fairness(
            current_assessed_cents=8050000,   # $80,500
            current_total_cents=35000000,     # $350,000
            target_ratio=0.20
        )

        # Target: $350,000 × 0.20 = $70,000
        assert savings.target_assessed_cents == 7000000
        # Reduction: $80,500 - $70,000 = $10,500
        assert savings.reduction_cents == 1050000
        # Annual tax savings: $10,500 × 0.0685 = $719.25
        assert savings.annual_savings_cents == 71925
        # 5-year savings: $719.25 × 5 = $3,596.25
        assert savings.five_year_savings_cents == 359625
        assert savings.is_worthwhile is True

    def test_borderline_appeal(self):
        """Test scenario where appeal is borderline worthwhile."""
        estimator = SavingsEstimator(default_mill_rate=65.0)

        # Small overassessment
        savings = estimator.estimate_savings(
            current_assessed_cents=5200000,  # $52,000
            target_assessed_cents=5000000,   # $50,000
        )

        # Reduction: $2,000
        # Annual savings: $2,000 × 0.065 = $130
        assert savings.annual_savings_cents == 13000
        assert savings.is_worthwhile is True  # Just over $100 threshold

    def test_minimal_overassessment(self):
        """Test scenario where appeal is not worthwhile."""
        estimator = SavingsEstimator(default_mill_rate=65.0)

        savings = estimator.estimate_savings(
            current_assessed_cents=5100000,  # $51,000
            target_assessed_cents=5000000,   # $50,000
        )

        # Reduction: $1,000
        # Annual savings: $1,000 × 0.065 = $65
        assert savings.annual_savings_cents == 6500
        assert savings.is_worthwhile is False  # Under $100 threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
